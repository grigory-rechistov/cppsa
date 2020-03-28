# Collection of simple diagnostics working on a single text line

from directives import all_directives, preprocessor_prefixes
from directives import directive_contains_condition, directive_is_definition
from diagcodes import diag_to_number

class BaseDiagnostic:
    def __init__(self, directive):
        self.lineno = directive.lineno
        self.text = directive.raw_text

        self.wcode = 0
        self.details = "unknown diagnostic"
    def __repr__(self):
        return "<%s W%d at %d: %s>" % (type(self).__name__,
                                      self.wcode, self.lineno, self.details)

class UnknownDirectiveDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["unknown"]
        self.details = "Unknown directive %s" % directive.hashword
    @staticmethod
    def apply(directive):
        lineno = directive.lineno
        hashword = directive.hashword
        if not hashword in all_directives:
            return UnknownDirectiveDiagnostic(directive)

class MultiLineDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["multiline"]
        self.details = "Multi-line define"
    @staticmethod
    def apply(directive):
        lineno = directive.lineno
        last_token = directive.tokens[-1]
        if last_token == "\\":
            return MultiLineDiagnostic(directive)


class LeadingWhitespaceDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["whitespace"]
        self.details = "Preprocessor directive starts with whitespace"
    @staticmethod
    def apply(directive):
        lineno = directive.lineno
        if not (directive.raw_text[0] in preprocessor_prefixes):
            return LeadingWhitespaceDiagnostic(directive)

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
    # TODO this function would not be needed if a separate pass handled single-
    #      and multiline comments in the source in advance.
    res = []
    for token in tokens:
        if token in ("//", "/*"):
            break
        res.append(token)
    return res

def has_any_operators(directive):
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

class ComplexIfConditionDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["complex_if_condition"]
        self.details = "Logical condition looks to be overly complex"

    @staticmethod
    def apply(directive):
        lineno = directive.lineno
        if not directive_contains_condition(directive.hashword):
            return
        # We want to allow only expressions using a single variable, e.g.
        #     #if SYMBOL, #if !SYMBOL, # if defined(SYMBOL) etc.
        # We want to notify about anything longer, like logic expressions:
        #     #if defined(EXPR1) && defined (EXPR2)
        # TODO A proper scanner/parser should be here. For now, just apply
        # a few heuristics.
        has_operators = has_any_operators(directive)

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
            return ComplexIfConditionDiagnostic(directive)

class SpaceAfterHashDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["space_after_leading"]
        self.details = "Space between leading symbol and keyword"

    @staticmethod
    def apply(directive):
        lineno = directive.lineno
        txt = directive.raw_text.strip()
        if len(txt) < 2:
            return
        if txt[1] in (" ", "\t"):
            return SpaceAfterHashDiagnostic(directive)

class SuggestInlineDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["suggest_inline_function"]
        self.details = "Suggest defining a static inline function instead"

    @staticmethod
    def apply(directive):
        lineno = directive.lineno
        # A macrodefine with non-empty parameter list
        # #define WORD ( something_not_bracket )

        if not directive_is_definition(directive.hashword):
            return
        # Is there enough tokens to contain bare minimum of function-like macro?
        if len(directive.tokens) < 5:
            return

        #first_token = directive.tokens[1]
        opening_bracket_candidate = directive.tokens[2]
        param_candidate = directive.tokens[3]
        if opening_bracket_candidate != "(":
            return
        # There must be no spaces between the opening bracket and the previous
        # letter for the line to be treated as a function-like macro. Tokenizer
        # has eaten all whitespaces, so look for it in raw_text
        brack_symbol_pos = directive.raw_text.find("(")
        assert brack_symbol_pos > 0
        prev_symbol = directive.raw_text[brack_symbol_pos - 1]
        if prev_symbol.isspace(): # first bracket did not open a parameter list
            return
        if param_candidate == ")": # no parameters between brackets
            return

        return SuggestInlineDiagnostic(directive)

class If0DeadCodeDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["if_0_dead_code"]
        self.details = "Code block is always discarded. Consider removing it"
    @staticmethod
    def apply(directive):
        if len(directive.tokens) < 2:
            return
        hashword = directive.hashword
        condition = directive.tokens[1]

        if directive_contains_condition(hashword) and condition == "0":
            return If0DeadCodeDiagnostic(directive)

class IfAlwaysTrueDiagnostic(BaseDiagnostic):
    def __init__(self, directive):
        super().__init__(directive)
        self.wcode = diag_to_number["if_always_true"]
        self.details = ("Code block is always included." +
                        " Remove surrounding directives")
    @staticmethod
    def apply(directive):
        if len(directive.tokens) < 2:
            return
        hashword = directive.hashword
        condition = directive.tokens[1]

        # TODO add detection of more trivially true expressions?
        if directive_contains_condition(hashword) and condition == "1":
            return If0DeadCodeDiagnostic(directive)

def run_simple_checks(pre_lines):
    all_single_line_diagnostics = (UnknownDirectiveDiagnostic,
                          MultiLineDiagnostic,
                          LeadingWhitespaceDiagnostic,
                          ComplexIfConditionDiagnostic,
                          SpaceAfterHashDiagnostic,
                          SuggestInlineDiagnostic,
                          If0DeadCodeDiagnostic,
                          IfAlwaysTrueDiagnostic,
    )

    res = list()
    for pre_line in pre_lines:
        for dia_class in all_single_line_diagnostics:
            w = dia_class.apply(pre_line)
            if w is not None:
                res.append(w)
    return res

