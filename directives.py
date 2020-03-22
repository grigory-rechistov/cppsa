include_meta_directives = True

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

P_IF = "\%if"
P_IFDEF = "\%ifdef"
P_IFNDEF = "\%ifndef"
P_ENDIF = "\%endif"

std_directives = (INCLUDE, DEFINE, UNDEF, IFDEF, IFNDEF, IF, ELSE, ELIF, ENDIF,
                  ERROR, PRAGMA)

if include_meta_directives:
    all_directives = std_directives + (P_IF, P_IFDEF, P_IFNDEF, P_ENDIF)
    preprocessor_prefixes = ("#", "\%")
else:
    all_directives = std_directives
    preprocessor_prefixes = ("#",)

def is_open_directive(d):
    return d in (IF, IFNDEF, IFDEF,
                 P_IF, P_IFDEF, P_IFNDEF)

def is_close_directive(d):
    return d in (ENDIF, P_ENDIF)

def line_is_preprocessor_directive(txt):
    txt = txt.strip()
    return (len(txt) > 0 and txt[0] in preprocessor_prefixes)

def directive_contains_condition(txt):
    return txt in (IF, P_IF)
