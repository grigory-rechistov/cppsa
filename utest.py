from cppsa import *
from cppsa import main as cpssa_main
import unittest

class TestInputFiles(unittest.TestCase):
    def test_main_on_empty_file(self):
        argv = ['cpssa', '/dev/null']
        res = cpssa_main(argv)
        self.assertTrue(res == 0)

    def test_main_on_basic(self):
        argv = ['cpssa', 'test/basic']
        res = cpssa_main(argv)
        self.assertTrue(res == 0)

    def test_main_on_unknown(self):
        argv = ['cpssa', 'test/unknown']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)

class TestConstants(unittest.TestCase):
    def test_diag_to_number(self):
        # The mapping must be one-to-one
        keys = set(diag_to_number.keys())
        values = set(diag_to_number.values())
        self.assertEqual(len(keys), len(values))

class TestRegularDirectives(unittest.TestCase):

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

    def test_is_open_directive(self):
        self.assertTrue(is_open_directive("#if"))
        self.assertTrue(is_open_directive("#ifdef"))
        self.assertTrue(is_open_directive("#ifndef"))
        self.assertFalse(is_open_directive("#define"))
        self.assertFalse(is_open_directive("#endif"))

    def test_is_close_directive(self):
        self.assertTrue(is_close_directive("#endif"))
        self.assertFalse(is_close_directive("#if"))
        self.assertFalse(is_close_directive("#else"))

    def test_shallow_ifdef_nesting(self):
        dirs = (
            (1, PreprocessorDirective("#ifdef A")),
            (3, PreprocessorDirective("#endif"))
        )

        res = exsessive_ifdef_nesting(dirs)
        self.assertTrue(len(res) == 0)

    def test_deep_ifdef_nesting(self):
        dirs = (
            (1, PreprocessorDirective("#ifdef A")),
            (2, PreprocessorDirective("#ifdef B")),
            (3, PreprocessorDirective("#ifdef C")),

            (11, PreprocessorDirective("#endif")),
            (12, PreprocessorDirective("#endif")),
            (13, PreprocessorDirective("#endif")),
        )

        res = exsessive_ifdef_nesting(dirs)
        print(res)
        self.assertTrue(len(res) == 1)


if __name__ == '__main__':
    unittest.main()
