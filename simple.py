from btypes import WarningDescription
from directives import all_directives, preprocessor_prefixes
from diagcodes import diag_to_number

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
