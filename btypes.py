
class PreprocessorDirective:
    def __init__(self, txt):
        self.raw_text = txt
        stripped_txt = txt.strip()
        assert len(stripped_txt) > 0, "Line must have at least one symbol (#)"
        tokens = list(token.strip() for token in stripped_txt.split(" "))
        final_token = tokens[-1]
        has_glued_slash = len(final_token) > 1 and final_token[-1] == "\\"
        if has_glued_slash:
            final_token_pair = [final_token[:-1], "\\"]
            tokens = tokens[:-1] + final_token_pair

        self.tokens = tokens
        self.hashword = self.tokens[0]
    def __repr__(self):
        return "<PreprocessorDirective %s>" % (repr(self.raw_text))

class WarningDescription:
    def __init__(self, wcode, details):
        self.wcode = wcode
        self.details = details
    def __repr__(self):
        return "<WarningDescription %d %s>" % (self.wcode, self.details)

