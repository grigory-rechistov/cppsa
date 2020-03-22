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
    return d in (IF, IFNDEF, IFDEF,
                 P_IF, P_IFDEF, P_IFNDEF)

def is_close_directive(d):
    return d in (ENDIF, P_ENDIF)

diag_to_number = {
        "unknown": 1,
        "multiline": 2,
        "whitespace": 3,
        "deepnest" : 4,
    }

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
            tokens = list(tkn.strip() for tkn in line.split(":"))
            fname = tokens[0]
            line = int(tokens[1])
            # Strip leading "W"
            undecorated_wcode = (tokens[2][1:] if tokens[2][0] == 'W'
                                               else tokens[2])
            wcode = int(undecorated_wcode)
            if fname != input_file:
                continue
            res.append((line, wcode))
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

def unknown_directive(directive):
#    import pdb; pdb.set_trace()
    hashword = directive.hashword
    if not hashword in all_directives:
        return WarningDescription(diag_to_number["unknown"],
                                  "Unknown directive %s" % hashword)

def multi_line_define(directive):
    last_token = directive.tokens[-1]
    if last_token == "\\":
        return WarningDescription(diag_to_number["multiline"],
                                  "Multi-line define")

def indented_directive(directive):
    if not (directive.raw_text[0] in preprocessor_prefixes):
        return WarningDescription(diag_to_number["whitespace"],
                              "Preprocessor directive starts with whitespace")


def exsessive_ifdef_nesting(dirs):
    res = list()
    level = 0
    max_level = 2
    opened_if_stack = []
    for (lineno, directive) in dirs:
        if is_open_directive(directive.hashword):
            level += 1
            if level > max_level:
                description = "Nesting of if-endif is too deep."

                for prev_lineno in reversed(opened_if_stack):
                    description += (" Earlier, an if-block"
                                    " was opened at line %d." % prev_lineno)
                new_diag = WarningDescription(diag_to_number["deepnest"],
                                              description)
                res.append((lineno, new_diag))
            opened_if_stack.append(lineno)
        elif is_close_directive(directive.hashword):
            level += -1
            opened_if_stack.pop()
    # Note: this check does not check unmatched directives
    return res


def usage(argv):
    print("Usage: %s <input> [whitelist]" % argv[0])
    return 2

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

def run_simple_checks(pre_line_pairs):
    single_line_checks = (unknown_directive,
                          multi_line_define,
                          indented_directive)

    res = list()
    for pre_pair in pre_line_pairs:
        for check in single_line_checks:
            w = check(pre_pair[1])
            if w:
                res.append((pre_pair[0], w.wcode, w.details))
    return res

def run_complex_checks(pre_line_pairs):
    multi_line_checks = (exsessive_ifdef_nesting,
    )
    res = list()

    for check in multi_line_checks:
        res_list = check(pre_line_pairs)
        res += res_list
    return res

def main(argv):
    # TODO introduce proper argparser
    # TODO have a separate whitelist of top level macrodefines: TARGET_HAS_ etc.
    if len(argv) < 2:
        return usage(argv)
    input_file = argv[1]
    if len(argv) == 3:
        whitelist = read_whitelist(input_file, argv[2])
    else:
        whitelist = list()

    pre_line_pairs = extract_preprocessor_lines(input_file)

    diagnostics = list()
    diagnostics += run_simple_checks(pre_line_pairs)
    diagnostics += run_complex_checks(pre_line_pairs)

    # Filter collected diagnostics against the whitelist
    displayed_diagnostics = filter_diagnostics(diagnostics, whitelist)
    for diag in displayed_diagnostics:
        (lineno, wcode, details) = diag
        print("%s:%d: W%d: %s" % (input_file, lineno, wcode, details) )

    return 0 if len(displayed_diagnostics) == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))