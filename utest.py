# These are unit tests

from cppsa import main as cpssa_main
from btypes import PreprocessorDirective
from directives import is_open_directive, is_close_directive

from simple import *
from multichecks import *

import unittest

class TestInputFiles(unittest.TestCase):
    # Pass '-q' to main to suppress litter in stdout
    def test_main_on_basic(self):
        argv = ['cpssa', '-q', 'test/basic']
        res = cpssa_main(argv)
        self.assertTrue(res == 0)

    def test_main_on_unknown(self):
        argv = ['cpssa', '-q', 'test/unknown']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)

    def test_main_on_unknown_with_whitelist(self):
        argv = ['cpssa', '-q', '--whitelist', 'test/unknown-wl', 'test/unknown']
        res = cpssa_main(argv)
        self.assertFalse(res)

    def test_main_on_unmarked_endif(self):
        argv = ['cpssa', '-q', 'test/unmarked-endif']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)

    def test_main_on_suggest_inline_func(self):
        argv = ['cpssa', '-q', 'test/inline-func']
        res = cpssa_main(argv)
        self.assertTrue(res == 1)


class TestConstants(unittest.TestCase):
    def test_diag_to_number(self):
        # The mapping must be one-to-one
        keys = set(diag_to_number.keys())
        values = set(diag_to_number.values())
        self.assertEqual(len(keys), len(values))

class TestDirectiveTokens(unittest.TestCase):
    def test_space_between_hash_and_keyword(self):
        directive = PreprocessorDirective("# define A",1 )
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


class TestSimpleDirectives(unittest.TestCase):

    def test_indented_directive(self):
        directive = PreprocessorDirective("        #define SYMBOL", 1)
        res = LeadingWhitespaceDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_unknown_directive(self):
        directive = PreprocessorDirective("#unknown I am something unknown", 1)
        res = UnknownDirectiveDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_multi_line_define_separate(self):
        directive = PreprocessorDirective("#define TEXT \\", 1)
        res = MultiLineDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_multi_line_define_joined(self):
        directive = PreprocessorDirective("#define TEXT\\", 1)
        res = MultiLineDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_complex_if_condition_for_simple(self):
        directive = PreprocessorDirective("#if CONDITION", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#if OS == linux", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#if !TRUE", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertFalse(res)

    def test_complex_if_condition_for_complex(self):
        directive = PreprocessorDirective("#if LINUX || WINDOWS", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#if !LINUX && WINDOWS", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_complex_if_condition_for_many_tokens(self):
        # Keep spaces between words, they are important for the test
        directive = PreprocessorDirective("#if ( ! ROUNDING_CONTROL ( DEFAULT ) == 4 )", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_complex_if_condition_for_many_special_symbols(self):
        directive = PreprocessorDirective("#if (!ROUNDING_CONTROL(DEFAULT)==4)", 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_space_after_hash(self):
        directive = PreprocessorDirective("# define F", 1)
        res = SpaceAfterHashDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#\tdefine F", 1)
        res = SpaceAfterHashDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_more_spaces_around_leading_symbol(self):
        directive = PreprocessorDirective(" #   include <lib>", 1)
        res = SpaceAfterHashDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_suggest_inline_function_give_suggestion(self):
        directive = PreprocessorDirective("#define MAX(a,b) (a) > (b) ? (a):(b)", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define A( a ) /* nothing */", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define A( a) substitution", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define A(a , b) substitution", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_suggest_inline_function_reject_suggestion(self):
        directive = PreprocessorDirective("#define MAX_INT 10000",1 )
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define A (a)", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define TIMESTAMP() do_nasty_global_stuff", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertFalse(res)


class TestMultiLineDirectives(unittest.TestCase):
    def test_shallow_ifdef_nesting(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif", 3)
        )

        res = exsessive_ifdef_nesting(dirs)
        self.assertTrue(len(res) == 0)

    def test_deep_ifdef_nesting(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#ifdef B", 2),
            PreprocessorDirective("#ifdef C", 3),

            PreprocessorDirective("#endif", 11),
            PreprocessorDirective("#endif", 12),
            PreprocessorDirective("#endif", 13),
        )

        res = exsessive_ifdef_nesting(dirs)
        self.assertTrue(len(res) == 1)

    def test_unbalanced_ifdef_nesting(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
        )
        res = unbalanced_if_endif(dirs)
        self.assertTrue(len(res) == 1)
        dirs = (
            PreprocessorDirective("#endif", 1),
        )
        res = unbalanced_if_endif(dirs)
        self.assertTrue(len(res) == 1)

    def test_multiple_unbalanced_ifdefs(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#ifdef B", 2),
            PreprocessorDirective("#ifdef C", 3),
        )
        res = unbalanced_if_endif(dirs)
        self.assertTrue(len(res) == 3)

    def test_multiple_unbalanced_endifs(self):
        dirs = (
            PreprocessorDirective("#endif A", 1),
            PreprocessorDirective("#endif B", 2),
            PreprocessorDirective("#endif C", 3),
        )
        res = unbalanced_if_endif(dirs)
        # Only the first unbalanced #endif is reported
        self.assertTrue(len(res) == 1)

    def test_unmarked_remote_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif", 1000),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 1)

    def test_unmarked_close_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif", 2),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)

        dirs = (
            PreprocessorDirective("#if A == B", 1),
            PreprocessorDirective("#endif", 2),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)


    def test_annotated_remote_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif //A", 1000),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)

        dirs = (
            PreprocessorDirective("#ifndef A", 1),
            # TODO the comment should (fuzzily) match #ifndef's condition,
            # but it is unimplemented
            PreprocessorDirective("#endif // some unrelated comment", 1000),
        )
        res = unmarked_remote_endif(dirs)
        self.assertTrue(len(res) == 0)


if __name__ == '__main__':
    unittest.main()
