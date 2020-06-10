# Threshold values for different diagnostics

from enum import IntEnum

class Threshold(IntEnum):
    IFDEF_NESTING = 2 # used by IfdefNestingDiagnostic
    TOKENS_THRESHOLD = 5 # used by ComplexIfConditionDiagnostic
    NON_ALPHANUM_THRESHOLD = 6 # used by ComplexIfConditionDiagnostic
    DEFINE_LINES_LIMIT = 5 # used by TooLongDefineDiagnostic
    MULTILINE_CONDITIONAL = 1 # used by MultilineConditionalDiagnostic
    MAX_IFDEF_ENDIF_DISTANCE = 7 # used by UnmarkedEndifDiagnostic
