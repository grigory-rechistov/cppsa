from cppsa import *
import unittest

class TestStringMethods(unittest.TestCase):

    def test_indented_directive(self):
        directive = PreprocessorDirective("        #define SYMBOL")
        res = indented_directive(directive)
        self.assertTrue(res)

    def test_unknown_directive(self):
        directive = PreprocessorDirective("#unknown I am something unknown")
        res = unknown_directive(directive)
        self.assertTrue(res)

    def test_multi_line_define_separate(self):
        directive = PreprocessorDirective("#define TEXT \\")
        res = multi_line_define(directive)
        self.assertTrue(res)

    def test_multi_line_define_joined(self):
        directive = PreprocessorDirective("#define TEXT\\")
        res = multi_line_define(directive)
        self.assertTrue(res)


if __name__ == '__main__':
    unittest.main()
