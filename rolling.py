from enum import Enum, auto

class Context(Enum):
    OUTSIDE = auto()
    COMMENT = auto()
    QUOTES = auto()
    BRACKETS = auto()

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

def transfer(context, token):
    map_outside = {
        "/*": Context.COMMENT,
        "*/": Context.OUTSIDE,
        "\n": Context.OUTSIDE,
    }
    map_comment = {
        "/*": Context.COMMENT,
        "*/": Context.OUTSIDE,
        "\n": Context.COMMENT,
    }

    table = {
        Context.OUTSIDE: map_outside,
        Context.COMMENT: map_comment,
    }

    sub_table = table[context]
    return sub_table[token]

def update_language_context(lines, old_state):
    line = "".join(lines)
    context = old_state
    tokens = ("/*", "*/", "\n") # TODO more tokens: // \\, ", ( ) {}
    pos = 0
    while pos < len(line):
        (next_token, delta) = find_next_token(line[pos:], tokens)
        if next_token is None: # EOL
            return context
        context = transfer(context, next_token)
        pos += delta + len(next_token)

    return context
