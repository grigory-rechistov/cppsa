# Tracking of rolling context of C-based source file

from enum import Enum

BACKSLASH = "\\"
tokens = frozenset(("/*", "*/", "//", "\n", BACKSLASH, '"'))

class Context(Enum):
    OUTSIDE = "normal environment"
    COMMENT = "multi-line comment"
    SLASH_COMMENT = "single-line comment"
    QUOTES = "quoted string"

def find_next_token(line, tokens):
    # Look for the earliest match of any of tokens
    # Return tuple (token, position)
    # Return (None, _) if nothing matched
    min_pos = len(line) + 1
    min_token = None
    for token in tokens:
        pos = line.find(token)
        if pos == -1:
            continue
        if pos < min_pos:
            min_pos = pos
            min_token = token
    return (min_token, min_pos)

map_outside = {
        "/*": Context.COMMENT,
        "//": Context.SLASH_COMMENT,
        "*/": Context.OUTSIDE,
        "\n": Context.OUTSIDE,
        BACKSLASH: Context.OUTSIDE,
        '"': Context.QUOTES
}
map_comment = {
        "*/": Context.OUTSIDE,
        "\n": Context.COMMENT,
        "/*": Context.COMMENT,
        "//": Context.COMMENT,
        BACKSLASH: Context.COMMENT,
        '"': Context.COMMENT
}

map_slash_comment = {
        "\n": Context.OUTSIDE,
        "*/": Context.SLASH_COMMENT,
        "/*": Context.SLASH_COMMENT,
        "//": Context.SLASH_COMMENT,
        BACKSLASH: Context.SLASH_COMMENT,
        '"': Context.SLASH_COMMENT
}

map_quotes = {
        "\n": Context.QUOTES, # Or Context.OUTSIDE, it is syntax error anyway
        "*/": Context.QUOTES,
        "/*": Context.QUOTES,
        "//": Context.QUOTES,
        BACKSLASH: Context.QUOTES,
        '"': Context.OUTSIDE
}

transfer_table = {
        Context.OUTSIDE: map_outside,
        Context.COMMENT: map_comment,
        Context.SLASH_COMMENT: map_slash_comment,
        Context.QUOTES: map_quotes
}

# Make sure all input tokens are handled in all sub-tables
for item in transfer_table.values():
    assert(tokens == frozenset(item.keys())), "sub-table is complete"


def transfer(context, token):
    sub_table = transfer_table[context]
    return sub_table[token]

def update_language_context(lines, old_state):
    line = "".join(lines)
    context = old_state
    pos = 0
    while pos < len(line):
        (next_token, delta) = find_next_token(line[pos:], tokens)
        if next_token is None: # EOL
            return context
        if next_token == BACKSLASH:
            # Skip everything up to the backslash and one following symbol
            # XXX this does not sound too reliable
            pos += delta + len(next_token) + 1
            continue
        context = transfer(context, next_token)
        pos += delta + len(next_token)

    return context
