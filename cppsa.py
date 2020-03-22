#!/usr/bin/env python3
# C preprocessor static analyzer

import sys

from btypes import WarningDescription, PreprocessorDirective
from directives import preprocessor_prefixes

from directives import is_open_directive, is_close_directive
from diagcodes import diag_to_number

from simple import run_simple_checks
from multichecks import run_complex_checks

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
