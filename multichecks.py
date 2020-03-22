from btypes import WarningDescription
from directives import is_open_directive, is_close_directive
from diagcodes import diag_to_number

def exsessive_ifdef_nesting(dirs):
    # TODO: this check reports both exsessively deep and unbalanced nesting.
    # Probably these should be handled in two different functions
    def deep_warning(lineno, opened_if_stack):
        description = "Nesting of if-endif is too deep."

        for prev_lineno in reversed(opened_if_stack):
            description += (" Earlier, an if-block"
                            " was opened at line %d." % prev_lineno)
        new_diag = WarningDescription(diag_to_number["deepnest"],
                                          description)
        return (lineno, new_diag.wcode, new_diag.details)

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
                res.append(deep_warning(lineno, opened_if_stack))
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

def unmarked_remote_endif(dirs):
#    import pdb; pdb.set_trace()
    # Check that
        #if COND
        # has matching comment at:
        #endif // COND
    # or similar
    max_distance = 4
    res = list()
    opened_if_stack = []
    for (lineno, directive) in dirs:
        if is_open_directive(directive.hashword):
            opened_if_stack.append((lineno, directive))
        elif is_close_directive(directive.hashword):
            if len(opened_if_stack) == 0:
                # unbalanced #endif. Abort further processing.
                break
            (start_lineno, start_directive) = opened_if_stack.pop()
            start_text = start_directive.raw_text.strip()
            scope_distance = lineno - start_lineno
            assert scope_distance > 0
            if scope_distance <= max_distance:
                continue # Close lines are visible, no need to warn about
            endif_tokens = directive.tokens
            # TODO Ideally, we need to check if the text of the comment
            # matched the #if condition, but given it is a freeform text,
            # it can not be reliably done for complex cases.
            # Instead, require that some comment is present
            if len(endif_tokens) < 2: # #endif plus at least something
                unmarked_w = WarningDescription(diag_to_number["unmarked_endif"],
                  ("No trailing comment to match opening" +
                  " directive '%s' at line %d (%d lines apart)") %
                      (start_text, start_lineno, scope_distance))
                res.append((lineno, unmarked_w.wcode, unmarked_w.details))
    return res


def run_complex_checks(pre_line_pairs):
    multi_line_checks = (exsessive_ifdef_nesting,
                         unmarked_remote_endif,
    )
    res = list()

    for check in multi_line_checks:
        res_list = check(pre_line_pairs)
        res += res_list
    return res
