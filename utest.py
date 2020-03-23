# These are unit tests

from cppsa import main as cpssa_main
from btypes import PreprocessorDirective
from directives import is_open_directive, is_close_directive

from simple import *
from multichecks import *

import unittest

class TestInputFiles(unittest.TestCase):
    # TODO Some of tests in this group write to stdout. Maybe stdout should be
    # intercepted to keep the test report clean. main() should accept -quiet

    def test_main_on_basic(self):
        argv = ['cpssa', 'test/basic']
        res = cpssa_main(argv)
        self.assertTrue(res == 0)

    def test_main_on_unknown(self):
        argv = ['cpssa', 'test/unknown']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)

    def test_main_on_unknown_with_whitelist(self):
        argv = ['cpssa', 'test/unknown', 'test/unknown-wl']
        res = cpssa_main(argv)
        self.assertFalse(res)

    def test_main_on_unmarked_endif(self):
        argv = ['cpssa', 'test/unmarked-endif']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)

    def test_main_on_suggest_inline_func(self):
        argv = ['cpssa', 'test/inline-func']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)


class TestConstants(unittest.TestCase):
    def test_diag_to_number(self):
        # The mapping must be one-to-one
        keys = set(diag_to_number.keys())
        values = set(diag_to_number.values())
        self.assertEqual(len(keys), len(values))

class TestSimpleDirectives(unittest.TestCase):
    def test_space_between_hash_and_keyword(self):
        directive = PreprocessorDirective("# define A")
        self.assertEqual(directive.hashword, "#define")

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

    def test_complex_if_condition_for_simple(self):
        directive = PreprocessorDirective("#if CONDITION")
        res = complex_if_condition(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#if OS == linux")
        res = complex_if_condition(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#if !TRUE")
        res = complex_if_condition(directive)
        self.assertFalse(res)

    def test_complex_if_condition_for_complex(self):
        directive = PreprocessorDirective("#if LINUX || WINDOWS")
        res = complex_if_condition(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#if !LINUX && WINDOWS")
        res = complex_if_condition(directive)
        self.assertTrue(res)

    def test_complex_if_condition_for_many_tokens(self):
        # Keep spaces between words, they are important for the test
        directive = PreprocessorDirective("#if ( ! ROUNDING_CONTROL ( DEFAULT ) == 4 )")
        res = complex_if_condition(directive)
        self.assertTrue(res)

    def test_complex_if_condition_for_many_special_symbols(self):
        directive = PreprocessorDirective("#if (!ROUNDING_CONTROL(DEFAULT)==4)")
        res = complex_if_condition(directive)
        self.assertTrue(res)

    def test_space_after_leading_symbol(self):
        directive = PreprocessorDirective("# define F")
        res = space_after_leading_symbol(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#\tdefine F")
        res = space_after_leading_symbol(directive)
        self.assertTrue(res)

    def test_more_spaces_around_leading_symbol(self):
        directive = PreprocessorDirective(" #   include <lib>")
        res = space_after_leading_symbol(directive)
        self.assertTrue(res)
        
    def test_suggest_inline_function_give_suggestion(self):
        directive = PreprocessorDirective("#define MAX(a,b) (a) > (b) ? (a):(b)")
        res = suggest_inline_function(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define A( a ) /* nothing */")
        res = suggest_inline_function(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define A( a) substitution")
        res = suggest_inline_function(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define A(a , b) substitution")
        res = suggest_inline_function(directive)
        self.assertTrue(res)
        
    def test_suggest_inline_function_reject_suggestion(self):
        directive = PreprocessorDirective("#define MAX_INT 10000")
        res = suggest_inline_function(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define A (a)")
        res = suggest_inline_function(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define TIMESTAMP() do_nasty_global_stuff")
        res = suggest_inline_function(directive)
        self.assertFalse(res)
        

class TestMultiLineDirectives(unittest.TestCase):
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
        self.assertTrue(len(res) == 1)

    def test_unbalanced_ifdef_nesting(self):
        dirs = (
            (1, PreprocessorDirective("#ifdef A")),
        )
        res = exsessive_ifdef_nesting(dirs)
        self.assertTrue(len(res) == 1)
        dirs = (
            (1, PreprocessorDirective("#endif")),
        )
        res = exsessive_ifdef_nesting(dirs)
        self.assertTrue(len(res) == 1)

    def test_unmarked_remote_endif(self):
        dirs = (
            (1, PreprocessorDirective("#ifdef A")),
            (1000, PreprocessorDirective("#endif")),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 1)

    def test_unmarked_close_endif(self):
        dirs = (
            (1, PreprocessorDirective("#ifdef A")),
            (2, PreprocessorDirective("#endif")),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)

        dirs = (
            (1, PreprocessorDirective("#if A == B")),
            (2, PreprocessorDirective("#endif")),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)


    def test_annotated_remote_endif(self):
        dirs = (
            (1, PreprocessorDirective("#ifdef A")),
            (1000, PreprocessorDirective("#endif //A")),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)

        # TODO the comment should match #ifndef's condition, but it is unimplemented
        dirs = (
            (1, PreprocessorDirective("#ifndef A")),
            (1000, PreprocessorDirective("#endif // some unrelated comment")),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)


if __name__ == '__main__':
    unittest.main()
