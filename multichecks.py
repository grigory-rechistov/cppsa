from btypes import PreprocessorDirective
from btypes import PreprocessorDiagnostic # TODO remove

from directives import is_open_directive, is_close_directive
from diagcodes import diag_to_number

class BaseMultilineDiagnostic:
    def __init__(self, directive, description):
        assert isinstance(description, str)
        assert isinstance(directive, PreprocessorDirective)
        self.lineno = directive.lineno
        self.text = directive.raw_text

        self.wcode = 0
        self.details = description
    def __repr__(self):
        return "<%s W%d at %d: %s>" % (type(self).__name__,
                                      self.wcode, self.lineno, self.details)

def make_deep_warning(opened_if_stack):
    description = "Nesting of if-endif is too deep."

    for prev_lineno in reversed(opened_if_stack):
        description += (" Earlier, an if-block"
                        " was opened at line %d." % prev_lineno)
    return description

class IfdefNestingDiagnostic(BaseMultilineDiagnostic):
    def __init__(self, directive, description):
        super().__init__(directive, description)
        self.wcode = diag_to_number["deepnest"]

    @staticmethod
    def apply_to_lines(pre_lines):
        # Complain after level has exceeded threshold until it has been reduced
        res = list()
        level = 0
        # TODO should be increased by one for headers if they have include guards
        # TODO should be increased by one if __cplusplus guards are used
        max_level = 2
        opened_if_stack = [] # To track encompassing if-endif blocks
        for directive in pre_lines:
            lineno = directive.lineno
            if is_open_directive(directive.hashword):
                level += 1
                if level > max_level:
                    description = make_deep_warning(opened_if_stack)
                    diagnostic = IfdefNestingDiagnostic(directive, description)
                    res.append(diagnostic)
                opened_if_stack.append(lineno)
            elif is_close_directive(directive.hashword):
                level += -1
                if len(opened_if_stack) == 0:
                    # Unbalanced #endif. Abort further processing.
                    break
                opened_if_stack.pop()
        return res

def unbalanced_if_endif(pre_lines):
    res = list()
    opened_if_stack = []
    for directive in pre_lines:
        lineno = directive.lineno
        if is_open_directive(directive.hashword):
            opened_if_stack.append(lineno)
        elif is_close_directive(directive.hashword):
            if len(opened_if_stack) == 0:
                unbalanced_dia = PreprocessorDiagnostic(
                                    diag_to_number["unbalanced_endif"],
                                    lineno,
                                    "Unbalanced closing directive found")
                res.append((lineno, unbalanced_dia.wcode,
                            unbalanced_dia.details))
                break
            opened_if_stack.pop()

    while len(opened_if_stack) > 0:
        lineno = opened_if_stack.pop()
        unbalanced_dia = PreprocessorDiagnostic(diag_to_number["unbalanced_if"],
                                    lineno,
                                    "Unbalanced opening directive found")
        res.append((lineno, unbalanced_dia.wcode,
                    unbalanced_dia.details))
    return res

def unmarked_remote_endif(pre_lines):
#    import pdb; pdb.set_trace()
    # Check that
        #if COND
        # has matching comment at:
        #endif // COND
    # or similar
    max_distance = 4
    res = list()
    opened_if_stack = []
    for directive in pre_lines:
        lineno = directive.lineno
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
                unmarked_w = PreprocessorDiagnostic(diag_to_number["unmarked_endif"],
                  lineno,
                  ("No trailing comment to match opening" +
                  " directive '%s' at line %d (%d lines apart)") %
                      (start_text, start_lineno, scope_distance))
                res.append((lineno, unmarked_w.wcode, unmarked_w.details))
    return res


def run_complex_checks(pre_lines):
    multi_line_checks = (IfdefNestingDiagnostic.apply_to_lines,
                         unmarked_remote_endif,
                         unbalanced_if_endif,
    )
    res = list()

    for check in multi_line_checks:
        res_list = check(pre_lines)
        res += res_list
    return res
