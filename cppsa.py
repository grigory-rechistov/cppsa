#!/usr/bin/env python3
# C preprocessor static analyzer

import sys

INCLUDE = "#include"
DEFINE = "#define"
UNDEF ="#undef"
IFDEF = "#ifdef"
IFNDEF = "#ifndef"
IF = "#if"
ELSE = "#else"
ELIF ="#elif"
ENDIF ="#endif"
ERROR = "#error"
PRAGMA = "#pragma"

include_meta_directives = True
P_IF = "\%if"
P_IFDEF = "\%ifdef"
P_IFNDEF = "\%ifndef"
P_ENDIF = "\%endif"


std_directives = (INCLUDE, DEFINE, UNDEF, IFDEF, IFNDEF, IF, ELSE, ELIF, ENDIF,
                  ERROR, PRAGMA)

if include_meta_directives:
    all_directives = std_directives + (P_IF, P_IFDEF, P_IFNDEF, P_ENDIF)
    preprocessor_prefixes = ("#", "\%")
else:
    all_directives = std_directives
    preprocessor_prefixes = ("#",)

def is_open_directive(d):
    return d in (IF, IFNDEF, IFDEF)

def is_close_directive(d):
    return d == ENDIF

class PreprocessorDirective:
    def __init__(self, txt):
        self.raw_text = txt
        stripped_txt = txt.strip()
        assert len(stripped_txt) > 0, "Line must have at least one symbol (#)"
        tokens = list(token.strip() for token in stripped_txt.split(" "))
        final_token = tokens[-1]
        has_glued_slash = len(final_token) > 1 and final_token[-1] == "\\"
        if has_glued_slash:
            final_token_pair = [final_token[:-1], "\\"]
            tokens = tokens[:-1] + final_token_pair

        self.tokens = tokens
        self.hashword = self.tokens[0]
    def __repr__(self):
        return "<PreprocessorDirective %s>" % (repr(self.raw_text))


def read_whitelist(input_file, global_whitelist):
    "Return a collection of suppressed warnings for input_file"
    res = list()
    with open(global_whitelist) as f:
        for line in f:
            (fname, line, wcode) = (tkn.strip() for tkn in line.split(","))
            if fname != input_file:
                continue
            line = int(line)
            res.append(line, wcode)
    return res

def line_is_preprocessor_directive(txt):
    txt = txt.strip()

    return (len(txt) > 0 and txt[0] in preprocessor_prefixes)

def extract_preprocessor_lines(input_file):
    # TODO maybe handle multi-line comments?
    res = list()
    with open(input_file) as f:
        lineno = 1
        for line in f:
            if line_is_preprocessor_directive(line):
                res.append((lineno, PreprocessorDirective(line)))
            lineno += 1
    return res


class WarningDescription:
    def __init__(self, wcode, details):
        self.wcode = wcode
        self.details = details
    def __repr__(self):
        return "<%d %s>" % (self.wcode, self.details)

# TODO invent a more flexible warning enumeration system. Don't use magic
# numbers. They should have priority level, from serious to mild.

def unknown_directive(directive):
#    import pdb; pdb.set_trace()
    hashword = directive.hashword
    if not hashword in all_directives:
        return WarningDescription(1, "Unknown directive %s" % hashword)

def multi_line_define(directive):
    last_token = directive.tokens[-1]
    if last_token == "\\":
        return WarningDescription(2, "Multi-line define")

def indented_directive(directive):
    if not (directive.raw_text[0] in preprocessor_prefixes):
        return WarningDescription(3,
                              "Preprocessor directive starts with whitespace")

def usage():
    print("Usage: %s <input> [whitelist]" % sys.argv[0])
    sys.exit(1)

def filter_diagnostics(diagnostics, whitelist):
    res = list()
    for diag in diagnostics:
        (lineno, wcode, _) = diag
        suppressed = False
        for (white_lineno, white_wcode) in whitelist:
            if lineno == white_lineno and wcode == white_wcode:
                suppressed = True
                break
        if not suppressed:
            res.append(diag)
    return res

def main(argv):
    # TODO introduce proper argparser
    # TODO have a separate whitelist of top level macrodefines: TARGET_HAS_ etc.
    if len(argv) < 2:
        usage()
    input_file = argv[1]
    if len(argv) == 3:
        whitelist = read_whitelist(argv[2])
    else:
        whitelist = list()

    pre_line_pairs = extract_preprocessor_lines(input_file)

    diagnostics = list()


    single_line_checks = (unknown_directive,
                          multi_line_define,
                          indented_directive)


    for pre_pair in pre_line_pairs:
        for check in single_line_checks:
            w = check(pre_pair[1])
            if w:
                diagnostics.append((pre_pair[0], w.wcode, w.details))

    # TODO add multi-line checks which operate over the complete file


    # Filter collected diagnostics against the whitelist
    displayed_diagnostics = filter_diagnostics(diagnostics, whitelist)
    for diag in displayed_diagnostics:
        (lineno, wcode, details) = diag
        print("%s:%d: W%d: %s" % (input_file, lineno, wcode, details) )

    return 0 if len(displayed_diagnostics) == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
