from btypes import WarningDescription
from directives import is_open_directive, is_close_directive
from diagcodes import diag_to_number

def exsessive_ifdef_nesting(dirs):
    # TODO: this check reports both exsessively deep and unbalanced nesting.
    # Probably these should be handled in two different functions
    res = list()
    level = 0
    # Complain after level has exceeded threshold until it has been reduced
    # TODO should be increased by one for headers if they have include guards
    # TODO should be increased by one if __cplusplus guards are used
    max_level = 2
    opened_if_stack = [] # To track encompassing if-endif blocks
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
            if len(opened_if_stack) == 0:
                # Either we missed an opening #if, or there is unbalanced #endif
                # in the input. Abort further processing.
                unbalanced_dia = WarningDescription(diag_to_number["unbalanced"],
                                      "Unbalanced closing directive found")
                res.append((lineno, unbalanced_dia.wcode,
                            unbalanced_dia.details))
                break
            opened_if_stack.pop()

    if level > 0:
        unbalanced_dia = WarningDescription(diag_to_number["unbalanced"],
                                      "Unbalanced opening directive found")
        res.append((lineno, unbalanced_dia.wcode,
                    unbalanced_dia.details))
    return res

def run_complex_checks(pre_line_pairs):
    multi_line_checks = (exsessive_ifdef_nesting,
    )
    res = list()

    for check in multi_line_checks:
        res_list = check(pre_line_pairs)
        res += res_list
    return res
