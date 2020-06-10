# Keywords of C/C++ preprocessor

INCLUDE = "#include"
DEFINE = "#define"
UNDEF ="#undef"
IFDEF = "#ifdef"
IFNDEF = "#ifndef"
IF = "#if"
ELSE = "#else"
ELIF ="#elif"
ENDIF ="#endif"
ERROR = "#error"
PRAGMA = "#pragma"

all_directives = (INCLUDE, DEFINE, UNDEF, IFDEF, IFNDEF, IF, ELSE, ELIF, ENDIF,
                  ERROR, PRAGMA)

CPLUSPLUS = "__cplusplus"
# Do not include __cplusplus as it is treated specially
std_predefined_macros = frozenset(("__FILE__", "__LINE__", "__DATE__", "__TIME__",
    "__func__", "__FUNCTION__"))

variadic_macros = frozenset(("...", "__VA_ARGS__", "__VA_OPT__"))

preprocessor_prefixes = ("#",)

def is_open_directive(d):
    return d in (IF, IFNDEF, IFDEF)

def is_close_directive(d):
    return d in (ENDIF, )

def line_is_preprocessor_directive(txt):
    txt = txt.strip()
    return (len(txt) > 0 and txt[0] in preprocessor_prefixes)

def directive_contains_condition(txt):
    return txt in (IF, )

def directive_is_definition(txt):
    return txt in (DEFINE, )

# C language keywords that cannot return value (cannot start an expression)
# TODO extend it with C++ keywords
non_expr_keywords = frozenset((
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if", "int",
    "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile",
    "while"))
