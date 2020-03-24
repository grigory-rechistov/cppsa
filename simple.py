from btypes import PreprocessorDiagnostic
from directives import all_directives, preprocessor_prefixes
from directives import directive_contains_condition, directive_is_definition
from diagcodes import diag_to_number

class UnknownDirectiveDiagnostic:
    # TODO make it child of PreprocessorDiagnostic
    def __init__(self, lineno, directive):
        assert isinstance(lineno, int)
        self.wcode = diag_to_number["unknown"]
        self.lineno = lineno
        self.text = directive.raw_text
        self.details = "Unknown directive %s" % directive.hashword
    def __repr__(self):
        return "<%s W%d at %d: %s>" % (type(self).__name__,
                                      self.wcode, self.lineno, self.details)

def unknown_directive(directive):
    lineno = directive.lineno

    hashword = directive.hashword
    if not hashword in all_directives:
        return UnknownDirectiveDiagnostic(lineno, directive)

def multi_line_define(directive):
    lineno = directive.lineno

    last_token = directive.tokens[-1]
    if last_token == "\\":
        return PreprocessorDiagnostic(diag_to_number["multiline"],
                                  lineno,
                                  "Multi-line define")

def indented_directive(directive):
    lineno = directive.lineno


    if not (directive.raw_text[0] in preprocessor_prefixes):
        return PreprocessorDiagnostic(diag_to_number["whitespace"],
                              lineno,
                              "Preprocessor directive starts with whitespace")

def complex_if_condition(directive):
    lineno = directive.lineno


    def has_logic_operator(t):
        return (t.find("&&") != -1 or t.find("||") != -1)
    def has_comparison_operator(t):
        return (t.find(">") != -1 or t.find("<") != -1)

    def count_non_alphanum(txt):
        txt = txt.replace(" ", "")
        ok_symbols = set("_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
        alphanum_count = sum(c in ok_symbols for c in txt)
        return len(txt) - alphanum_count

    def tokens_without_comment(tokens):
        # Disregard a trailing comment, i.e. anything after // or /*
        res = []
        for token in tokens:
            if token.find("//") != -1 or token.find("/*") != -1:
                # TODO ideally, split trailing comment in current token, but
                # preserve the head
                break
            res.append(token)
        return res

    def look_for_operators(directive):
        has_operators = False
        tokens = directive.tokens[1:]
        tokens = tokens_without_comment(tokens)
        for token in tokens:
            has_operators = (has_operators or has_logic_operator(token) or
                         has_comparison_operator(token))
        return has_operators

    def count_noncomment_tokens(directive):
        tokens = directive.tokens[1:]
        tokens = tokens_without_comment(tokens)
        return len(tokens)

    if not directive_contains_condition(directive.hashword):
        return
    # Generally, we want to allow only expressions using a single variable, e.g.
    #     #if SYMBOL, #if !SYMBOL, # if defined(SYMBOL) etc.
    # We want to notify about logic expressions, such as
    #     #if defined(EXPR1) && defined (EXPR2)
    # TODO A proper scanner/parser should be here. For now, just apply
    # a few heuristics.
    has_operators = look_for_operators(directive)

    # Consider wordiness a bad sign
    tokens_threshold = 5 # an arbitrary value, really
    too_many_tokens = count_noncomment_tokens(directive) > tokens_threshold

    # In absense of proper tokenizer, consider all non-alphanumeric symbols as
    # potential token delimeters
    non_alphanum = count_non_alphanum(directive.raw_text)

    non_alphanum_threshold = 6
    if (has_operators
        or too_many_tokens
        or non_alphanum > non_alphanum_threshold):
        return PreprocessorDiagnostic(diag_to_number["complex_if_condition"],
                              lineno,
                              "Logical condition looks to be overly complex")

def space_after_leading_symbol(directive):
    lineno = directive.lineno


    txt = directive.raw_text.strip()
    if len(txt) < 2:
        return
    if txt[1] in (" ", "\t"):
        return PreprocessorDiagnostic(diag_to_number["space_after_leading"],
                              lineno,
                              "Space between leading symbol and keyword")

def suggest_inline_function(directive):
    lineno = directive.lineno

    # A macrodefine with non-empty parameter list
    # TODO this function would certainly benefit from a proper lexer
    if not directive_is_definition(directive.hashword):
        return
    if len(directive.tokens) < 2:
        return
    
    first_token = directive.tokens[1]
    # The bracket must be glued to the symbol
    opening_bracket = first_token.find("(")
    if opening_bracket == -1: # it is a #define without parameters
        return
    closing_bracket = first_token.find(")")
    if closing_bracket != -1:
        if closing_bracket == opening_bracket + 1:
            # No parameters between brackets "()"
            return
        # else something is between brackets
    else:
        # Look for the bracket in the next token
        if len(directive.tokens) < 3:
            # Malformed directive, bail out
            return
        second_token = directive.tokens[2]
        if second_token[0] == ")":
            # No symbols between "(" in first_token and ")" in second_token
            return
        # otherwise, there is at least one symbol after "("
    
    return PreprocessorDiagnostic(diag_to_number["suggest_inline_function"],
                            lineno,
                            "Suggest defining a static inline function instead")


def run_simple_checks(pre_lines):
    single_line_checks = (unknown_directive,
                          multi_line_define,
                          indented_directive,
                          complex_if_condition,
                          space_after_leading_symbol,
                          suggest_inline_function)

    res = list()
    for pre_line in pre_lines:
        for check in single_line_checks:
            w = check(pre_line)
            if w:
                res.append((w.lineno, w.wcode, w.details))
    return res

