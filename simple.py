from btypes import WarningDescription
from directives import all_directives, preprocessor_prefixes
from directives import directive_contains_condition
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

def complex_if_condition(directive):
    def has_logic_operator(t):
        return (t.find("&&") != -1 or t.find("||") != -1)
    def has_comparison_operator(t):
        return (t.find(">") != -1 or t.find("<") != -1)

    def count_non_alphanum(txt):
        txt = txt.replace(" ", "")
        ok_symbols = set("_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
        alphanum_count = sum(c in ok_symbols for c in txt)
        return len(txt) - alphanum_count

    if not directive_contains_condition(directive.hashword):
        return
    has_operators = False
    # Generally, we want to allow only expressions using a single variable, e.g.
    #     #if SYMBOL, #if !SYMBOL, # if defined(SYMBOL) etc.
    # We want to notify about logic expressions, such as
    #     #if defined(EXPR1) && defined (EXPR2)
    # TODO ideally, a proper scanner/parser should be here. For now, just apply
    # a few heuristics.
    tokens = directive.tokens[1:]
    for token in tokens:
        has_operators = (has_operators or has_logic_operator(token) or
                         has_comparison_operator(token))

    # In absense of proper tokenizer, consider all non-alphanumeric symbols as
    # potential token delimeters
    non_alphanum = count_non_alphanum(directive.raw_text)

    non_alphanum_threshold = 6
    tokens_threshold = 5 # an arbitrary value, really
    if (has_operators
        or len(tokens) > tokens_threshold
        or non_alphanum > non_alphanum_threshold):
        return WarningDescription(diag_to_number["complex_if_condition"],
                              "Logical condition looks to be overly complex")

def space_after_leading_symbol(directive):
    if len(directive.raw_text) < 2:
        return
    if directive.raw_text[1] in (" ", "\t"):
        return WarningDescription(diag_to_number["space_after_leading"],
                              "Space between leading symbol and keyword")

def run_simple_checks(pre_line_pairs):
    single_line_checks = (unknown_directive,
                          multi_line_define,
                          indented_directive,
                          complex_if_condition,
                          space_after_leading_symbol)

    res = list()
    for pre_pair in pre_line_pairs:
        for check in single_line_checks:
            w = check(pre_pair[1])
            if w:
                res.append((pre_pair[0], w.wcode, w.details))
    return res

