# Base classes

class PreprocessorDirective:
    "Partially parsed source file line"
    def __init__(self, txt, lineno):
        self.raw_text = txt
        self.lineno = lineno
        stripped_txt = txt.strip()
        assert len(stripped_txt) > 0, "Line must have at least one symbol (# or similar)"

        tokens = list(token.strip() for token in stripped_txt.split())
        if len(tokens[0]) == 1: # space between leading symbol and keyword,
            # Merge them
            tokens = [tokens[0] + tokens[1]] + tokens[2:]

        # Unglue hash if needed
        final_token = tokens[-1]
        has_glued_slash = len(final_token) > 1 and final_token[-1] == "\\"
        if has_glued_slash:
            final_token_pair = [final_token[:-1], "\\"]
            tokens = tokens[:-1] + final_token_pair

        self.tokens = tokens
        self.hashword = self.tokens[0]
    def __repr__(self):
        return "<PreprocessorDirective at %d %s>" % (self.lineno,
                                                     repr(self.raw_text))

class PreprocessorDiagnostic:
    "Base class for all diagnostics"
    def __init__(self, wcode, lineno, details = None):
        self.wcode = wcode
        assert isinstance(lineno, int)
        self.lineno = lineno
        self.details = details
        self.text = None # TODO To be provided in child classes
    def __repr__(self):
        return "<PreprocessorDiagnostic %d at %d: %s>" % (
                            self.wcode, self.lineno, self.details)

