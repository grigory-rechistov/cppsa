from enum import Enum, auto

class Context(Enum):
    OUTSIDE = auto()
    COMMENT = auto()
    QUOTES = auto()
    BRACKETS = auto()


def update_language_context(line, old_state):
    return Context.OUTSIDE