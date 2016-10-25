def paginate(text, delims=['\n'], shorten_by=8):
    in_text = text
    while len(in_text) > 2000:
        closest_delim = max([in_text.rfind(d, 0, 2000 - shorten_by) for d in delims])
        closest_delim = closest_delim if closest_delim != -1 else 2000
        to_send = in_text[:closest_delim]
        yield to_send
        in_text = in_text[closest_delim:]

    yield in_text


def bold(text):
    return "**{}**".format(text)


def box(text, lang=""):
    ret = "```{}\n{}\n```".format(lang, text)
    return ret


def inline(text):
    return "`{}`".format(text)


def italics(text):
    return "*{}*".format(text)


def strikethrough(text):
    return "~~{}~~".format(text)


def underline(text):
    return "__{}__".format(text)
