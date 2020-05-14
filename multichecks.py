from btypes import PreprocessorDirective

from directives import is_open_directive, is_close_directive
from directives import DEFINE
from diagcodes import diag_to_number, filter_diagnostics

class BaseMultilineDiagnostic:
    wcode = 0
    def __init__(self, directive, description):
        assert isinstance(description, str)
        assert isinstance(directive, PreprocessorDirective)
        self.lineno = directive.lineno
        self.text = directive.raw_text
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

def sense_for_include_guard(pre_lines):
    # Quite a fixed understanding what is considered to be include guards is
    # used
    if len(pre_lines) < 3:
        return False
    ifndef_candidate = pre_lines[0]
    define_candidate = pre_lines[1]
    endif_candidate = pre_lines[-1]
    # Check for all components of a proper guard:
    # #ifdef SYMBOL_H
    # define SYMBOL_H
    # endif
    if not ifndef_candidate.is_ifndef():
        return False
    header_symbol = ifndef_candidate.first_symbol()
    if not define_candidate.hashword == DEFINE:
        return False
    define_symbol = define_candidate.first_symbol()
    if header_symbol != define_symbol:
        return False
    if not is_close_directive(endif_candidate.hashword):
        return False

    return True

def sense_for_global_cplusplus_guard(pre_lines):
    # TODO write me
    return False

class IfdefNestingDiagnostic(BaseMultilineDiagnostic):
    wcode = diag_to_number["deepnest"]

    @staticmethod
    def apply_to_lines(pre_lines):
        # Complain after level has exceeded threshold until it has been reduced
        res = list()
        max_level = 2
        max_level += 1 if sense_for_include_guard(pre_lines) else 0
        max_level += 1 if sense_for_global_cplusplus_guard(pre_lines) else 0

        level = 0
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

class UnbalancedEndifDiagnostic(BaseMultilineDiagnostic):
    wcode = diag_to_number["unbalanced_endif"]

    @staticmethod
    def apply_to_lines(pre_lines):
        res = list()
        opened_if_stack = []
        for directive in pre_lines:
            lineno = directive.lineno
            if is_open_directive(directive.hashword):
                opened_if_stack.append(lineno)
            elif is_close_directive(directive.hashword):
                if len(opened_if_stack) == 0:
                    unbalanced_endif = UnbalancedEndifDiagnostic(directive,
                                        "Unbalanced closing directive found")
                    res.append(unbalanced_endif)
                    break
                opened_if_stack.pop()
        return res

class UnbalancedIfDiagnostic(BaseMultilineDiagnostic):
    wcode = diag_to_number["unbalanced_if"]

    @staticmethod
    def apply_to_lines(pre_lines):
        res = list()
        opened_if_stack = []
        for directive in pre_lines:
            lineno = directive.lineno
            if is_open_directive(directive.hashword):
                opened_if_stack.append(lineno)
            elif is_close_directive(directive.hashword):
                if len(opened_if_stack) == 0:
                    # endifs are unbalanced, bail out
                    break
                opened_if_stack.pop()

        while len(opened_if_stack) > 0:
            lineno = opened_if_stack.pop()
            unbalanced_if = UnbalancedIfDiagnostic(directive,
                                        "Unbalanced opening directive found")
            res.append(unbalanced_if)
        return res

class UnmarkedEndifDiagnostic(BaseMultilineDiagnostic):
    wcode = diag_to_number["unmarked_endif"]

    @staticmethod
    def apply_to_lines(pre_lines):
        # Check that
            #if COND
            # has matching comment at endif:
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
                # Ideally, we need to check if the text of the comment
                # matched the #if condition, but given it is a freeform text,
                # it can not be reliably done for complex cases.
                # Instead, require that some comment is present
                # TODO at least the first alphanumeric token should match, and
                #      it can be easily checked
                if len(endif_tokens) < 2: # #endif plus at least something
                    description = ("No trailing comment to match opening" +
                                    " directive '%s' at line %d (%d lines apart)" % (start_text, start_lineno, scope_distance))
                    unmarked_w = UnmarkedEndifDiagnostic(directive, description)
                    res.append(unmarked_w)
        return res


def run_complex_checks(pre_lines, enabled_wcodes):
    all_diagnostics = (
                        IfdefNestingDiagnostic,
                        UnbalancedEndifDiagnostic,
                        UnbalancedIfDiagnostic,
                        UnmarkedEndifDiagnostic,
    )

    enabled_diagnostics = filter_diagnostics(all_diagnostics, enabled_wcodes)

    res = list()
    for dia_class in enabled_diagnostics:
        res += dia_class.apply_to_lines(pre_lines)
    return res
