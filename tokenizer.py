# Tokenizing directives and routines

import re
from keywords import IFNDEF, IF, IFDEF, std_predefined_macros, variadic_macros
from rolling import Context

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


def line_ends_with_continuation(txt):
    txt = txt.strip()
    # BUG: does not handle the case when the final backslash is escaped by
    #      itself by a preceding backslash
    return len(txt) > 0 and txt[-1] == "\\"

def extract_multiline_sequence(lines, start_lineno):
    lineno = start_lineno
    res = []
    while lineno < len(lines):
        this_line = lines[lineno]
        res.append(this_line)
        if not line_ends_with_continuation(this_line):
            break
        lineno += 1
    return res

class PreprocessorDirective:
    "Tokenized preprocessor line(s)"
    def __init__(self, line_or_lines, lineno, context = Context.OUTSIDE):
        assert line_or_lines
        if isinstance(line_or_lines, str):
            first_line = line_or_lines
            self.multi_lines = [line_or_lines]
        else:
            first_line = line_or_lines[0]
            self.multi_lines = line_or_lines

        self.first_line = first_line
        self.full_text = self.combine_all_lines()
        self.lineno = lineno
        self.context = context
        stripped_txt = self.full_text.strip()
        assert stripped_txt, "Line must have at least one symbol (# or similar)"
        tokens = tokenize(stripped_txt)
        if len(tokens[0]) == 1: # space between leading hash symbol and keyword
            # Merge them
            tokens = [tokens[0] + tokens[1]] + tokens[2:]

        self.tokens = tokens
        self.hashword = self.tokens[0]

    def combine_all_lines(self):
        res = ''
        for line in self.multi_lines:
            line = line.strip()
            if line_ends_with_continuation(line):
                line = line[:-1]
            if res and (not res[-1].isspace()):
                res += " "
            res += line
        return res

    def __repr__(self):
        if len(self.multi_lines) > 1:
            suffix = ' and %d more line(s)' % (len(self.multi_lines) - 1)
        else:
            suffix = ''
        return "<PreprocessorDirective at %d %s%s>" % (
            self.lineno, repr(self.first_line), suffix)
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

    def tokens_without_comment(self):
        # Disregard a trailing comment, i.e. anything after // or /*
        # Certain other diagnostics treat comments as important part of lines
        res = []
        for token in self.tokens:
            if token in ("//", "/*"):
                break
            res.append(token)
        return res

    def uses_macro_tricks(self):
        """Return True if the expression contains things that indeed can be best
        done by preprocessor"""
        all_tokens = self.tokens_without_comment()
        for token in all_tokens[1:]:
            if token == "##":
                # concatenation
                return True
            if token[0] == "#":
                # stringizing
                return True
            if token in std_predefined_macros:
                # __LINE__ etc.
                return True
            if token in variadic_macros:
                return True
        return False
