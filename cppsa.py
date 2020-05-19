#!/usr/bin/env python3
# C preprocessor static analyzer

import sys
import argparse
import re

from tokenizer import PreprocessorDirective
from tokenizer import extract_multiline_sequence
from keywords import line_is_preprocessor_directive
from diagcodes import all_wcodes

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
    res = list()
    with open(input_file) as f:
        lines = f.readlines()
    lineno = 0
    while lineno < len(lines):
        if line_is_preprocessor_directive(lines[lineno]):
            multi_lines = extract_multiline_sequence(lines, lineno)
            human_lineno = lineno + 1
            res.append(PreprocessorDirective(multi_lines, human_lineno))
            lineno += len(multi_lines)
        else:
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

def parse_args(argv):
    parser = argparse.ArgumentParser(description=
                                     "Analyze preprocessor directives")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Do not show diagnostics, only return error code")
    parser.add_argument("-v", "--verbose", action="store_true",
                help="Be extra verbose (cannot be used together with --quiet)")
    parser.add_argument("-W", "--whitelist", type=str, default=None,
                        help="Whitelist of ignored warnings")
    parser.add_argument("-D", "--diagnostics", type=str, default="",
                        help='List of diagnostics separated by commas.'
                            ' Use word "all" to mean all of them, or negative'
                            ' number to disable a specific diagnostic.')
    parser.add_argument("-a", "--analyze-true-preprocessor", action="store_true",
                        help="""Also look into directives that make use of
                                preprocessor-specific operations, such as
                                stringizing""")

    parser.add_argument('input_file', metavar='input_file', type=str,
                        help='File to be analyzed')

    opts = parser.parse_args(argv)
    if opts.verbose and opts.quiet:
        print("Flags --quiet and --verbose cannot be used together");
        parser.print_help()
        sys.exit(2)
    return opts

def parse_diag_spec_line(spec_string, all_wcodes):
    if spec_string == '':
        return (all_wcodes, None)
    result = set()
    tokens = spec_string.strip().split(",")
    for token in tokens:
        if token == "":
            continue
        if token == "all":
            result.update(all_wcodes)
        elif token == "-all":
            result = set()
        elif re.match(r"-?\d+", token):
            num = int(token)
            if num > 0:
                result.add(num)
            elif num < 0:
                try:
                    result.remove(-num)
                except KeyError:
                    pass # it's fine to attempt to remove non-present diag
            else:
                return (None, "invalid diagnostics code 0")
        else:
            return (None, "unrecognized token '%s'" % token)

    # Check that only known numbers are in the set
    extra_numbers = result.difference(all_wcodes)
    if extra_numbers:
        return (None, "unknown diagnostics codes %s" % extra_numbers)
    return (result, None)

def main(argv):
    # TODO have a separate whitelist of top level macrodefines: TARGET_HAS_ etc.

    opts = parse_args(argv[1:])

    input_file = opts.input_file
    verbose = opts.verbose
    quiet = opts.quiet
    whitelist_name = opts.whitelist

    (enabled_wcodes, diag_err) = parse_diag_spec_line(opts.diagnostics,
                                 all_wcodes)
    if diag_err is not None:
        print("Parsing -D failed: %s" % diag_err)
        return 2
    if verbose:
        print("Enabled diagnostics: %s" % sorted(enabled_wcodes))

    if verbose:
        print("Processing %s" % input_file)
    if whitelist_name is not None:
        whitelist = read_whitelist(input_file, whitelist_name)
    else:
        whitelist = list()

    pre_lines = extract_preprocessor_lines(input_file)

    if not opts.analyze_true_preprocessor:
        pre_lines = list(filter(lambda l: not l.uses_macro_tricks(), pre_lines))

    diagnostics = list()
    diagnostics += run_simple_checks(pre_lines, enabled_wcodes)
    diagnostics += run_complex_checks(pre_lines, enabled_wcodes)

    # Filter collected diagnostics against the whitelist
    displayed_diagnostics = filter_diagnostics(diagnostics, whitelist)
    if not quiet:
        for diag in displayed_diagnostics:
            (lineno, wcode, details) = (diag.lineno, diag.wcode, diag.details)
            print("%s:%d: W%d: %s" % (input_file, lineno, wcode, details) )
            assert diag.text is not None
            verbatim_text = diag.text.strip('\n')
            print("    %s" % verbatim_text)

    return 0 if len(displayed_diagnostics) == 0 else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
