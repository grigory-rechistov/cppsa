
diag_to_number = {
        "unknown": 1,
        "multiline": 2,
        "whitespace": 3,
        "deepnest" : 4,
        "complex_if_condition": 5,
        "space_after_leading": 6,
        "unbalanced_if": 7,
        "unmarked_endif": 8,
        "suggest_inline_function" : 9,
        "unbalanced_endif": 10,
        "if_0_dead_code": 11,
        "if_always_true": 12,
        "suggest_void_function": 13,
        "suggest_const": 14,
        # TODO using_numerical_as_def_undef # e.g #define A 1, #ifdef A
        # TODO "undef_is_bad for external symbols "
        # TODO mixed_percent_and_sharp_directives: %ifdef #if %endif #endif
    }

all_wcodes = frozenset(diag_to_number.values())

assert len(all_wcodes) == len(diag_to_number), "1:1 mapping is maintained"

def filter_diagnostics(all_diagnostics, enabled_wcodes):
    return set(diag for diag in all_diagnostics if diag.wcode in enabled_wcodes)
