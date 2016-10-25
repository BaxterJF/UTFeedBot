from github3 import GitHub
import sqlite3
from bs4 import BeautifulSoup
import asyncio
import discord
import feedparser
import logging
import time
from time import mktime
from datetime import datetime
import auth
import style

bot = discord.Client()
logging.basicConfig(level=logging.INFO)

db = sqlite3.connect('data/db.sqlite')
cursor = db.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS entries(
        id INTEGER PRIMARY KEY,
        identifier TEXT, author TEXT, message TEXT,
        url TEXT, wilcox INTEGER, date TEXT
    )
""")

gh = GitHub(auth.GH_USERNAME, auth.GH_PASSWORD)
feed_url = str(gh.feeds()['current_user_url'])

wilcox_aliases = ['DigitalLeprechaun', 'Joe Wilcox']
wilcox_alert = 'WILCOX DETECTED'


@app.route("/")
def start():
    return "hello"


@bot.event
async def on_ready():
    logging.info('Logged in as {} {} at {}'.format(bot.user.name, bot.user.id, time.ctime()))
    while True:
        await shrink_db()
        await parse_feed()
        await asyncio.sleep(60)


@bot.event
async def send(message):
    if message:
        msg = style.paginate(message)
        for page in msg:
            await bot.send_message(discord.Object(id='213316494254276608'), page)
            logging.info('{}: dispatched commit summary'.format(time.ctime()))
    else:
        logging.info('{}: no new messages'.format(time.ctime()))
        pass


async def is_new(entry):
    cursor.execute("SELECT count(*) FROM entries WHERE identifier = ?", (entry['identifier'],))
    result = cursor.fetchone()[0]
    if result == 0:
        return True
    return False


async def shrink_db():
    c = cursor.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    logging.info('row count: {}'.format(c))
    if c > 30:
        cursor.execute("SELECT * FROM entries ORDER BY strftime('%s', date) DESC Limit 1 OFFSET 29")
        a = cursor.fetchone()
        if a is not None:
            cursor.execute("DELETE FROM entries WHERE strftime('%s', date) < strftime('%s', ?)", (a[6],))
            logging.info('purged {} entries'.format(cursor.rowcount))
            db.commit()


async def valid_feed(feed):
    if not feed:
        return False
    return True

async def valid_entry(entry, soup):
    # if not entry[3]['value'] == 'commit event':
    if not soup.svg['class'][1] == 'octicon-git-commit' or not entry.id:
        # logging.info('{}'.format(soup.svg['class'][1]))
        return False
    return True

async def parse_feed():
    d = feedparser.parse(feed_url)

    feed = d.entries
    if not await valid_feed(d):
        logging.warning("Empty feed; backing out..")
        return

    discord_message = ""
    for e in feed:
        sp = BeautifulSoup(e.summary, 'html.parser')
        if not await valid_entry(e, sp):
            logging.warning("Unwanted or malformed feed item; backing out..")
            continue

        identifier = e.id
        author = sp.span['title'].strip() if sp.span else '--'
        message = sp.blockquote.string.strip() if sp.blockquote.string else '--'
        url = 'https://github.com' + sp.code.a['href'] if sp.code and sp.code.a and sp.code.a['href'] else '--'
        wilcox = author in wilcox_aliases
        date = datetime.fromtimestamp(mktime(e.updated_parsed)) if e.updated_parsed else '--'

        entry = {
            'identifier': identifier,
            'author': author,
            'url': url,
            'wilcox': wilcox,
            'date': date
        }

        entry.update({'message': '\u200b\n{}\n{}\n{}\n\n'.format(
            style.bold(author + ':'), message,
            url)
        })

        # if wilcox:
        #     entry.update({'message': '\u200b\n{}\n{}\n{}\n{}\n{}\n\n'.format(
        #         wilcox_alert, style.bold(author + ':'),
        #         message, url, wilcox_alert)
        #     })
        # else:
        #     entry.update({'message': '\u200b\n{}\n{}\n{}\n\n'.format(
        #         style.bold(author + ':'), message,
        #         url)
        #     })

        if await is_new(entry):
            discord_message = ''.join([entry['message'], discord_message])
            cursor.execute("""
                INSERT INTO entries(
                    identifier, author, message,
                    url, wilcox, date
                )
                    VALUES(
                    :identifier, :author, :message,
                    :url, :wilcox, :date
                )
            """, entry)

            db.commit()

    await send(discord_message)

bot.run(auth.BOT_TOKEN)
