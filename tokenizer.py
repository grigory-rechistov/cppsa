# Tokenizing directives and routines

import re
from directives import IFNDEF, IF, IFDEF

def is_alnum_underscore(s):
    return re.match(r'^[A-Za-z0-9_]+$', s) is not None

def match_special(s):
    specials = ("(", ")", ",", "\\", "##",
                "!",
                "//", "/*",
    )
    matched_special = None
    for special in specials:
        if s.find(special) == 0:
            matched_special = special
            break
    return matched_special

def tokenize(txt):
    res = list()
    i = 0
    while i < len(txt):
        if txt[i].isspace():
            i += 1
            continue

        # Try to match a special
        matched_special = match_special(txt[i:])
        if matched_special is not None:
            i += len(matched_special)
            res.append(matched_special)
            continue

        # Otherwise consume everything until the next space/special
        k = i+1
        while (k < len(txt)
               and (match_special(txt[k:]) is None)
               and not txt[k].isspace()):
            k += 1
        misc_token = txt[i:k]
        i = k
        res.append(misc_token)
    return res


class PreprocessorDirective:
    "Tokenized preprocessor line"
    def __init__(self, line_or_lines, lineno):
        assert line_or_lines
        if isinstance(line_or_lines, str):
            txt = line_or_lines
            self.multi_lines = [line_or_lines]
        else:
            txt = line_or_lines[0]
            self.multi_lines = line_or_lines

        self.raw_text = txt
        self.lineno = lineno
        stripped_txt = txt.strip()
        assert len(stripped_txt) > 0, "Line must have at least one symbol (# or similar)"

        tokens = tokenize(stripped_txt)
        if len(tokens[0]) == 1: # space between leading symbol and keyword
            # Merge them
            tokens = [tokens[0] + tokens[1]] + tokens[2:]

        self.tokens = tokens
        self.hashword = self.tokens[0]
    def __repr__(self):
        if len(self.multi_lines) > 1:
            suffix = ' and %d more line(s)' % (len(self.multi_lines) - 1)
        else:
            suffix = ''
        return "<PreprocessorDirective at %d %s%s>" % (self.lineno,
                                                       repr(self.raw_text),
                                                       suffix)
    def is_ifndef(self):
        # Return True on either of
        # #ifndef
        # #if !defined(...)
        if self.hashword == IFNDEF:
            return True
        if self.hashword != IF:
            return False
        # Now look for (!, defined) among tokens
        if len(self.tokens) < 3: # #if ! defined
            return False
        if self.tokens[1] != "!":
            return False
        if self.tokens[2] != "defined":
            return False
        return True

    def is_ifdef(self):
        # Return True on either of
        # #ifdef
        # #if defined(...)
        if self.hashword == IFDEF:
            return True
        if self.hashword != IF:
            return False
        if len(self.tokens) < 2: # look for #if defined
            return False
        if self.tokens[1] != "defined":
            return False
        return True

    def first_symbol(self):
        # return first non-keyword alphanumeric token
        keywords = ("defined", )
        for token in self.tokens[1:]:
            if not is_alnum_underscore(token):
                continue
            if token in keywords:
                continue
            return token
        raise Exception("No alphanumeric symbols follow directive")
