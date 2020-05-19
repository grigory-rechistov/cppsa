# Symbolic names for diagnostics

from enum import IntEnum, unique

@unique
class DiagCodes(IntEnum):
    unknown = 1
    multiline = 2
    whitespace = 3
    deepnest = 4
    complex_if_condition = 5
    space_after_leading = 6
    unbalanced_if = 7
    unmarked_endif = 8
    suggest_inline_function = 9
    unbalanced_endif = 10
    if_0_dead_code = 11
    if_always_true = 12
    suggest_void_function = 13
    suggest_const = 14
    too_long_define = 15
    multiline_conditional = 16

all_wcodes = frozenset(int(m) for m in DiagCodes.__members__.values())

def filter_diagnostics(all_diagnostics, enabled_wcodes):
    return set(diag for diag in all_diagnostics if diag.wcode in enabled_wcodes)
