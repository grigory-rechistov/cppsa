from btypes import WarningDescription
from directives import is_open_directive, is_close_directive
from diagcodes import diag_to_number

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
                res.append((lineno, new_diag.wcode, new_diag.details))
            opened_if_stack.append(lineno)
        elif is_close_directive(directive.hashword):
            level += -1
            opened_if_stack.pop()
    # Note: this check does not check unmatched directives
    return res

def run_complex_checks(pre_line_pairs):
    multi_line_checks = (exsessive_ifdef_nesting,
    )
    res = list()

    for check in multi_line_checks:
        res_list = check(pre_line_pairs)
        res += res_list
    return res
