#!/usr/bin/env python3
# C preprocessor static analyzer

import sys
import argparse

from btypes import PreprocessorDirective
from directives import preprocessor_prefixes

from directives import is_open_directive, is_close_directive
from directives import line_is_preprocessor_directive
from diagcodes import diag_to_number

from simple import run_simple_checks
from multichecks import run_complex_checks

def read_whitelist(input_file, global_whitelist):
    """global_whitelist contains lines for many files.
       Return a collection of suppressed warnings for input_file"""
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
                res.append(PreprocessorDirective(line, lineno))
            lineno += 1
    return res


def filter_diagnostics(diagnostics, whitelist):
    res = list()
    for diag in diagnostics:
        lineno = diag.lineno
        wcode = diag.wcode
        suppressed = False
        for (white_lineno, white_wcode) in whitelist:
            if lineno == white_lineno and wcode == white_wcode:
                suppressed = True
                break
        if not suppressed:
            res.append(diag)
    return res

def get_print_line(pre_lines, lineno):
    # TODO save reference to the original text line in the diagnostic, instead of
    # hunting for it once again. This is ineffective and stupid
    candidates = list(t.raw_text for t in pre_lines if t.lineno == lineno)
    assert len(candidates) == 1, "The line could not disappear from the file"
    res = candidates[0]
    if res[-1] == "\n":
        res = res[:-1]
    return res

def parse_args(argv):
    parser = argparse.ArgumentParser(description=
                                     "Analyze preprocessor directives")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Do not show diagnostics, only return error code")
    parser.add_argument("-v", "--verbose", action="store_true",
                help="Be extra verbose (cannot be used together with --quiet)")
    parser.add_argument("-W", "--whitelist", type=str, default=None,
                        help="Whitelist of ignored warnings")


    parser.add_argument('input_file', metavar='input_file', type=str,
                        help='File to be analyzed')

    opts = parser.parse_args(argv)
    if opts.verbose and opts.quiet:
        print("Flags --quiet and --verbose cannot be used together");
        parser.print_help()
        sys.exit(2)
    return opts

def main(argv):
    # TODO have a separate whitelist of top level macrodefines: TARGET_HAS_ etc.

    opts = parse_args(argv[1:])

    input_file = opts.input_file
    verbose = opts.verbose
    quiet = opts.quiet
    whitelist_name = opts.whitelist

    if verbose:
        print("Processing %s" % input_file)
    if whitelist_name is not None:
        whitelist = read_whitelist(input_file, whitelist_name)
    else:
        whitelist = list()

    pre_lines = extract_preprocessor_lines(input_file)

    diagnostics = list()
    diagnostics += run_simple_checks(pre_lines)
    diagnostics += run_complex_checks(pre_lines)

    # Filter collected diagnostics against the whitelist
    displayed_diagnostics = filter_diagnostics(diagnostics, whitelist)
    if not quiet:
        for diag in displayed_diagnostics:
            (lineno, wcode, details) = (diag.lineno, diag.wcode, diag.details)
            print("%s:%d: W%d: %s" % (input_file, lineno, wcode, details) )
            if diag.text is not None:
                verbatim_text = diag.text
            else:
                # TODO this line will be redundant once all diagnostics store
                # the text line inside themselves
                verbatim_text = get_print_line(pre_lines, lineno)
            print("    %s" % verbatim_text)

    return 0 if len(displayed_diagnostics) == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
