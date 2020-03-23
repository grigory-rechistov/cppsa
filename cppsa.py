#!/usr/bin/env python3
# C preprocessor static analyzer

import sys

from btypes import WarningDescription, PreprocessorDirective
from directives import preprocessor_prefixes

from directives import is_open_directive, is_close_directive
from directives import line_is_preprocessor_directive
from diagcodes import diag_to_number

from simple import run_simple_checks
from multichecks import run_complex_checks

# TODO turn these into knobs
verbose = False
print_line = True

def read_whitelist(input_file, global_whitelist):
    "Return a collection of suppressed warnings for input_file"
    res = list()
    with open(global_whitelist) as f:
        for line in f:
            # To make it compatible with cppsa's own output, ignore lines
            # prepended with space
            if len(line) == 0 or line[0] == " ":
                continue
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

def get_print_line(line_pairs, lineno):
    # TODO save reference to the original line in the diagnostic, instead of
    # hunting for it once again. This is ineffective and stupid
    candidates = list(t[1].raw_text for t in line_pairs if t[0] == lineno)
    assert len(candidates) == 1, "The line could not disappear from the file"
    res = candidates[0]
    if res[-1] == "\n":
        res = res[:-1]
    return res

def main(argv):
    # TODO introduce proper argparser
    # TODO have a separate whitelist of top level macrodefines: TARGET_HAS_ etc.
    if len(argv) < 2:
        return usage(argv)
    input_file = argv[1]

    if verbose:
        print("Processing %s" % input_file)
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
        if print_line:
            verbatim_text = get_print_line(pre_line_pairs, lineno)
            print("    %s" % verbatim_text)

    return 0 if len(displayed_diagnostics) == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
