# These are unit tests

from cppsa import main as cpssa_main
from cppsa import parse_diag_spec_line
from btypes import PreprocessorDirective, tokenize
from directives import is_open_directive, is_close_directive

from simple import *
from multichecks import *

import unittest

class TestTokenizer(unittest.TestCase):
    def test_tokenize_empty(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("   "), [])
        self.assertEqual(tokenize("\n"), [])
        self.assertEqual(tokenize("  \n"), [])
        self.assertEqual(tokenize("  \t "), [])

    def test_tokenize_alnum(self):
        self.assertEqual(tokenize("word"), ["word"])
        self.assertEqual(tokenize("word another"), ["word", "another"])
        self.assertEqual(tokenize("#word another"), ["#word", "another"])
        self.assertEqual(tokenize("#word(another)"), ["#word", "(", "another", ")"])
        self.assertEqual(tokenize("#word(another)\n"), ["#word", "(", "another", ")"])
        self.assertEqual(tokenize("word(pa, pb)"), ["word", "(", "pa", ",", "pb", ")"])

    def test_token_pasting(self):
        self.assertEqual(tokenize("a##b"), ["a", "##", "b"])

    def test_tokenize_underscores_and_digits(self):
        self.assertEqual(tokenize("many_underscores_in_word"), ["many_underscores_in_word"])
        self.assertEqual(tokenize("u_n ds2 45c 3.14"), ["u_n", "ds2", "45c", "3.14"])

    def test_tokenize_backslash(self):
        self.assertEqual(tokenize("\\"), ["\\"])
        self.assertEqual(tokenize("word\\"), ["word", "\\"])
        self.assertEqual(tokenize("word\\\n"), ["word", "\\"])

    def test_tokenize_comments(self):
        self.assertEqual(tokenize("statement /* comment"), ["statement", "/*", "comment"])
        self.assertEqual(tokenize("statement /*comment"), ["statement", "/*", "comment"])
        self.assertEqual(tokenize("statement // comment"), ["statement", "//", "comment"])
        self.assertEqual(tokenize("statement //comment"), ["statement", "//", "comment"])
        self.assertEqual(tokenize("statement//comment"), ["statement", "//", "comment"])

    def test_tokenize_other(self):
        self.assertEqual(tokenize("#define LOST()lost"), ["#define", "LOST", "(", ")", "lost"])
        self.assertEqual(tokenize("#define FOUND( x) not_found"), ["#define", "FOUND", "(", "x", ")", "not_found"])

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

    def test_main_on_empty_diag_list(self):
        argv = ['cpssa', '-q', '-D-all', 'test/file-with-problems']
        res = cpssa_main(argv)
        self.assertTrue(res == 0)

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
        directive = PreprocessorDirective("#define MAX_INT 10000", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define A (a)", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define TIMESTAMP() do_nasty_global_stuff", 1)
        res = SuggestInlineDiagnostic.apply(directive)
        self.assertFalse(res)

    def test_if_0(self):
        directive = PreprocessorDirective("#if 0", 1)
        res = If0DeadCodeDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_if_always_true(self):
        directive = PreprocessorDirective("#if 1", 1)
        res = IfAlwaysTrueDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_suggest_void_function(self):
        directive = PreprocessorDirective("#define F() do", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define F do", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define F(a,b,c) do", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertTrue(res)
        directive = PreprocessorDirective("#define F (a, b, c) do", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertTrue(res)

        directive = PreprocessorDirective("#define F() dobado", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define do something", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#pragma random do something", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertFalse(res)

class TestMultiLineDirectives(unittest.TestCase):
    def test_shallow_ifdef_nesting(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif", 3)
        )
        res = IfdefNestingDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)

    def test_medium_ifdef_nesting(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#if B", 2),
            PreprocessorDirective("#endif", 3),
            PreprocessorDirective("#endif", 4),
        )
        res = IfdefNestingDiagnostic.apply_to_lines(dirs)
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

        res = IfdefNestingDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 1)

    def test_ifdef_nesting_with_header_guards(self):
        dirs = (
            PreprocessorDirective("#ifndef A_H", 1),
            PreprocessorDirective("#define A_H", 2),
            PreprocessorDirective("#if C == B", 3),
            PreprocessorDirective("#ifdef D", 4),

            PreprocessorDirective("#endif // D", 11),
            PreprocessorDirective("#endif // C == B", 12),
            PreprocessorDirective("#endif // A_H", 13),
        )
        res = IfdefNestingDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)

    def test_unbalanced_ifdef_nesting(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
        )
        res = UnbalancedIfDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 1)

    def test_unbalanced_endif_nesting(self):
        dirs = (
            PreprocessorDirective("#endif", 1),
        )
        res = UnbalancedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 1)

    def test_multiple_unbalanced_ifdefs(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#ifdef B", 2),
            PreprocessorDirective("#ifdef C", 3),
        )
        res = UnbalancedIfDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 3)

    def test_multiple_unbalanced_endifs(self):
        dirs = (
            PreprocessorDirective("#endif A", 1),
            PreprocessorDirective("#endif B", 2),
            PreprocessorDirective("#endif C", 3),
        )
        res = UnbalancedEndifDiagnostic.apply_to_lines(dirs)
        # Only the first unbalanced #endif is reported
        self.assertTrue(len(res) == 1)

    def test_unmarked_remote_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif", 1000),
        )
        res = UnmarkedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 1)

    def test_unmarked_close_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif", 2),
        )
        res = UnmarkedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)

        dirs = (
            PreprocessorDirective("#if A == B", 1),
            PreprocessorDirective("#endif", 2),
        )
        res = UnmarkedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)


    def test_annotated_remote_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif //A", 1000),
        )
        res = UnmarkedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)

        dirs = (
            PreprocessorDirective("#ifndef A", 1),
            # TODO the comment should (fuzzily) match #ifndef's condition,
            # but it is unimplemented
            PreprocessorDirective("#endif // some unrelated comment", 1000),
        )
        res = UnmarkedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)

    def test_incorrectly_annotated_remote_endif(self):
        dirs = (
            PreprocessorDirective("#ifdef A", 1),
            PreprocessorDirective("#endif incorrect but accepted", 1000),
        )
        res = UnmarkedEndifDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)


class TestIncludeGuards(unittest.TestCase):
    def test_include_guard_detection_ifndef(self):
        dirs = (
            PreprocessorDirective("#ifndef HEADER_GUARD", 1),
            PreprocessorDirective("#define HEADER_GUARD", 2),
            PreprocessorDirective("#endif", 3),
        )
        self.assertTrue(sense_for_include_guard(dirs))

    def test_include_guard_detection_if_not_defined(self):
        dirs = (
            PreprocessorDirective("#if !defined(HEADER_GUARD)", 1),
            PreprocessorDirective("#define HEADER_GUARD", 2),
            PreprocessorDirective("#endif", 3),
        )
#        import pdb; pdb.set_trace()
        self.assertTrue(sense_for_include_guard(dirs))

    def test_include_guard_detection_mismatch_symbol(self):
        dirs = (
            PreprocessorDirective("#ifndef HEADER_GUARD", 1),
            PreprocessorDirective("#define WRONG_SYMBOL", 2),
            PreprocessorDirective("#endif", 3),
        )
        self.assertFalse(sense_for_include_guard(dirs))
        dirs = (
            PreprocessorDirective("#if !defined(HEADER_GUARD)", 1),
            PreprocessorDirective("#define WRONG_SYMBOL", 2),
            PreprocessorDirective("#endif", 3),
        )
        self.assertFalse(sense_for_include_guard(dirs))

    def test_include_guard_detection_something_follows_endif(self):
        dirs = (
            PreprocessorDirective("#if !defined(HEADER_GUARD)", 1),
            PreprocessorDirective("#define HEADER_GUARD", 2),
            PreprocessorDirective("#endif", 3),
            PreprocessorDirective("#define EXTRA 2", 10),
        )
        self.assertFalse(sense_for_include_guard(dirs))
        dirs = (
            PreprocessorDirective("#ifndef HEADER_GUARD", 1),
            PreprocessorDirective("#define HEADER_GUARD", 2),
            PreprocessorDirective("#endif", 3),
            PreprocessorDirective("#define EXTRA 2", 10),
        )
        self.assertFalse(sense_for_include_guard(dirs))

    def test_include_guard_detection_missing_defined(self):
        dirs = (
            PreprocessorDirective("#if !defined(HEADER_GUARD)", 1),
            PreprocessorDirective("#include <header>", 2),
            PreprocessorDirective("#endif", 3),

        )
        self.assertFalse(sense_for_include_guard(dirs))
        dirs = (
            PreprocessorDirective("#if !defined(HEADER_GUARD)", 1),
            PreprocessorDirective("#endif", 3),

        )
        self.assertFalse(sense_for_include_guard(dirs))

class TestDiagSpecParsing(unittest.TestCase):
    def test_keyword_all(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("all", all)
        self.assertEqual(err, None)
        self.assertEqual(res, all)

    def test_default_empty(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("", all)
        self.assertEqual(err, None)
        self.assertEqual(res, all)

    def test_single_diag(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1", all)
        self.assertEqual(err, None)
        self.assertEqual(res, set((1,)))

    def test_comma_numbers(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1,99", all)
        self.assertEqual(err, None)
        self.assertEqual(res, set((1, 99)))

    def test_minus_all(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1,2,-all", all)
        self.assertEqual(err, None)
        self.assertEqual(res, set())

    def test_all_minus_number(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("all,-99", all)
        self.assertEqual(err, None)
        self.assertEqual(res, set((1, 2, 5)))

    def test_number_minus_number(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("2,5,-2", all)
        self.assertEqual(err, None)
        self.assertEqual(res, set((5,)))

    def test_minus_non_specified(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1,2,5,-99", all)
        self.assertEqual(err, None)
        self.assertEqual(res, set((1, 2, 5)))

    def test_minus_wrong_number(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("all,-100", all)
        self.assertEqual(err, None)
        self.assertEqual(res, all)

    def test_zero(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1,0", all)
        self.assertNotEqual(err, None)

    def test_wrong_number(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("100", all)
        self.assertNotEqual(err, None)

    def test_bad_token(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1,bad_token", all)
        self.assertNotEqual(err, None)

    def test_multiple_repeats(self):
        all = set((1, 2, 5, 99))
        (res, err)= parse_diag_spec_line("1,1,1,1,", all)
        self.assertNotEqual(err, set((1,)))

if __name__ == '__main__':
    unittest.main()
