# Collection of simple diagnostics working on a single text line

from keywords import all_directives, preprocessor_prefixes
from keywords import directive_contains_condition, directive_is_definition
from diagcodes import DiagCodes, filter_diag_codes
from rolling import Context

class BaseDiagnostic:
    wcode = 0
    def __init__(self, directive):
        self.lineno = directive.lineno
        self.first_line = directive.first_line
        self.details = "unknown diagnostic"
    def __repr__(self):
        return "<%s W%d at %d: %s>" % (type(self).__name__,
                                      self.wcode, self.lineno, self.details)

class UnknownDirectiveDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.unknown
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Unknown directive %s" % directive.hashword
    @staticmethod
    def apply(directive):
        hashword = directive.hashword
        if hashword in all_directives:
            return
        if directive.context != Context.OUTSIDE:
            # Inside e.g. comments hashes may be used for decoration, should not
            # trigger a warning
            return

        return UnknownDirectiveDiagnostic(directive)

class MultiLineDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.multiline
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Multi-line preprocessor directive"
    @staticmethod
    def apply(directive):
        first_line = directive.first_line.strip()
        last_token = first_line[-1]
        if last_token == "\\":
            return MultiLineDiagnostic(directive)

class LeadingWhitespaceDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.whitespace
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Preprocessor directive starts with whitespace"
    @staticmethod
    def apply(directive):
        if not (directive.first_line[0] in preprocessor_prefixes):
            return LeadingWhitespaceDiagnostic(directive)

def has_logic_operator(t):
    return (t.find("&&") != -1 or t.find("||") != -1)
def has_comparison_operator(t):
    return (t.find(">") != -1 or t.find("<") != -1)

def count_non_alphanum(txt):
    txt = txt.replace(" ", "")
    ok_symbols = frozenset("_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz0123456789")
    alphanum_count = sum(c in ok_symbols for c in txt)
    return len(txt) - alphanum_count

def has_any_operators(directive):
    has_operators = False
    tokens = directive.tokens_without_comment()
    for token in tokens:
        has_operators = (has_operators or has_logic_operator(token) or
                     has_comparison_operator(token))
    return has_operators

def count_noncomment_tokens(directive):
    return len(directive.tokens_without_comment())

class ComplexIfConditionDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.complex_if_condition
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Logical condition looks to be overly complex"

    @staticmethod
    def apply(directive):
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
        non_alphanum = count_non_alphanum(directive.full_text)

        non_alphanum_threshold = 6
        if (has_operators
            or too_many_tokens
            or non_alphanum > non_alphanum_threshold):
            return ComplexIfConditionDiagnostic(directive)

class SpaceAfterHashDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.space_after_leading
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Space between leading symbol and keyword"

    @staticmethod
    def apply(directive):
        txt = directive.full_text.strip()
        if len(txt) < 2:
            return
        if txt[1] in (" ", "\t"):
            return SpaceAfterHashDiagnostic(directive)

class SuggestInlineDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.suggest_inline_function
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Suggest defining a static inline function instead"

    @staticmethod
    def apply(directive):
        # A macrodefine with non-empty parameter list
        # #define WORD ( something_not_bracket )

        if not directive_is_definition(directive.hashword):
            return
        # Is there enough tokens to contain bare minimum of function-like macro?
        if len(directive.tokens) < 5:
            return

        opening_bracket_candidate = directive.tokens[2]
        param_candidate = directive.tokens[3]
        if opening_bracket_candidate != "(":
            return
        # There must be no spaces between the opening bracket and the previous
        # letter for the line to be treated as a function-like macro. Tokenizer
        # has eaten all whitespaces, so look for it in the unsplit string
        unsplit_text = directive.full_text
        brack_symbol_pos = unsplit_text.find("(")
        assert brack_symbol_pos > 0
        prev_symbol = unsplit_text[brack_symbol_pos - 1]
        if prev_symbol.isspace(): # first bracket did not open a parameter list
            return
        if param_candidate == ")": # no parameters between brackets
            return

        return SuggestInlineDiagnostic(directive)

class If0DeadCodeDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.if_0_dead_code
    def __init__(self, directive):
        super().__init__(directive)
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
    wcode = DiagCodes.if_always_true
    def __init__(self, directive):
        super().__init__(directive)
        self.details = ("Code block is always included." +
                        " Remove surrounding directives")
    @staticmethod
    def apply(directive):
        if len(directive.tokens) < 2:
            return
        hashword = directive.hashword
        condition = directive.tokens[1]

        if directive_contains_condition(hashword) and condition == "1":
            return IfAlwaysTrueDiagnostic(directive)

class SuggestVoidDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.suggest_void_function
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Suggest defining a void function instead of do {} while"

    @staticmethod
    def apply(directive):
        # A function-like macrodefine with "do", hinting at do {} while
        # #define WORD ... do ...

        if not directive_is_definition(directive.hashword):
            return
        # Is there enough tokens?
        if len(directive.tokens) < 3:
            return

        has_do = "do" in directive.tokens[2:]
        if has_do:
            return SuggestVoidDiagnostic(directive)

class SuggestConstantDiagnostic(BaseDiagnostic):
    # standard function-like macros that return compile-time constants
    # and a few commonly used function-like macros
    recognized_keywords = frozenset(("UINT64_C", "UINT32_C", "UINT16_C",
        "UINTMAX_C", "INTMAX_C", "INT64_C", "INT32_C", "INT16_C",
        "BIT",
    ))

    wcode = DiagCodes.suggest_const
    def __init__(self, directive, symbol):
        super().__init__(directive)
        self.details = (
            "Suggest using an enum, constant or typedef for %s" % symbol)

    @staticmethod
    def apply(directive):
        # symbol is defined as a literal constant:
        # #define SYMBOL 1234
        # #define SYMBOL 0xabcd
        # #define SYMBOL "string here"

        if not directive_is_definition(directive.hashword):
            return
        # Is there enough tokens?
        if len(directive.tokens) < 3:
            return

        symbol = directive.tokens[1]
        diag = SuggestConstantDiagnostic(directive, symbol)

        literal_candidate = directive.tokens[2]
        if literal_candidate == "(": # It is a function-like define
            return

        if literal_candidate == "\\": # No idea what follows at the next line
            return

        if literal_candidate in SuggestConstantDiagnostic.recognized_keywords:
            return diag

        if len(directive.tokens) == 3:
            # Not much deviation from #define SYMBOL LITERAL
            return diag

class TooLongDefineDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.too_long_define
    line_limit = 3
    def __init__(self, directive):
        super().__init__(directive)
        self.details = ("Multi-line definition is longer than %d lines" %
                        self.line_limit)

    @staticmethod
    def apply(directive):
        if not directive_is_definition(directive.hashword):
            return
        number_of_lines = len(directive.multi_lines)

        if number_of_lines > TooLongDefineDiagnostic.line_limit:
            return TooLongDefineDiagnostic(directive)

class WrongContextDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.multiline_conditional
    def __init__(self, directive):
        super().__init__(directive)
        str_context = directive.context.value
        self.details = "Preprocessor directive inside %s" % str_context

    @staticmethod
    def apply(directive):
        if directive.context == Context.OUTSIDE:
            return
        return WrongContextDiagnostic(directive)

class MultilineConditionalDiagnostic(BaseDiagnostic):
    wcode = DiagCodes.multiline_conditional
    def __init__(self, directive):
        super().__init__(directive)
        self.details = "Multi-line conditional statement"

    @staticmethod
    def apply(directive):
        if not directive_contains_condition(directive.hashword):
            return
        number_of_lines = len(directive.multi_lines)

        if number_of_lines > 1:
            return MultilineConditionalDiagnostic(directive)


def run_simple_checks(pre_lines, enabled_wcodes):
    all_diagnostics    = (UnknownDirectiveDiagnostic,
                          MultiLineDiagnostic,
                          LeadingWhitespaceDiagnostic,
                          ComplexIfConditionDiagnostic,
                          SpaceAfterHashDiagnostic,
                          SuggestInlineDiagnostic,
                          If0DeadCodeDiagnostic,
                          IfAlwaysTrueDiagnostic,
                          SuggestVoidDiagnostic,
                          SuggestConstantDiagnostic,
                          TooLongDefineDiagnostic,
                          MultilineConditionalDiagnostic,
                          WrongContextDiagnostic,
    )

    enabled_diagnostics = filter_diag_codes(all_diagnostics, enabled_wcodes)
    res = list()
    for pre_line in pre_lines:
        for dia_class in enabled_diagnostics:
            w = dia_class.apply(pre_line)
            if w is not None:
                res.append(w)
    return res
