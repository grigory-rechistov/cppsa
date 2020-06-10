# These are unit tests

from cppsa import main as cppsa_main
from cppsa import parse_diag_spec_line
from cppsa import line_is_preprocessor_directive
from tokenizer import extract_multiline_sequence, line_ends_with_continuation
from tokenizer import PreprocessorDirective, tokenize
from keywords import is_open_directive, is_close_directive
from rolling import update_language_context, Context

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

class TestDirectiveFunctions(unittest.TestCase):
    def test_line_ends_with_continuation(self):
        self.assertTrue(line_ends_with_continuation("text text\\"))
        self.assertTrue(line_ends_with_continuation("text text\\  "))
        self.assertTrue(line_ends_with_continuation("text text\\\n"))
        self.assertTrue(line_ends_with_continuation("text text\\\n\r"))
        self.assertTrue(line_ends_with_continuation("text text\\\t"))
        self.assertTrue(line_ends_with_continuation("\\"))

        self.assertFalse(line_ends_with_continuation(""))
        self.assertFalse(line_ends_with_continuation("    \n"))
        self.assertFalse(line_ends_with_continuation("just a text"))
        self.assertFalse(line_ends_with_continuation("just a text\n"))

    def test_line_is_preprocessor_directive(self):
        self.assertTrue(line_is_preprocessor_directive("#directive"))
        self.assertTrue(line_is_preprocessor_directive("   #directive"))
        self.assertTrue(line_is_preprocessor_directive("#directive\n"))
        self.assertTrue(line_is_preprocessor_directive("#directive\n\t"))
        self.assertTrue(line_is_preprocessor_directive("#"))

        self.assertFalse(line_is_preprocessor_directive(""))
        self.assertFalse(line_is_preprocessor_directive("  \t\n"))
        self.assertFalse(line_is_preprocessor_directive("not_directive"))

    def test_extract_multiline_sequence(self):
        lines = ["line 1\\", "line2\\", "line3"]
        self.assertEqual(len(extract_multiline_sequence(lines, 0)), 3)

        lines = ["line 1\\", "line2\\", "line3\\"]
        self.assertEqual(len(extract_multiline_sequence(lines, 0)), 3)

        lines = ["line 1\n", "line2\\", "line3"]
        self.assertEqual(len(extract_multiline_sequence(lines, 0)), 1)

        lines = ["line 1\\"]
        self.assertEqual(len(extract_multiline_sequence(lines, 0)), 1)

        lines = ["line 1\\\n", "line2", "line3\\"]
        self.assertEqual(len(extract_multiline_sequence(lines, 0)), 2)

class TestInputFiles(unittest.TestCase):
    script = "cppsa"
    # Pass '-q' to main to suppress litter in stdout
    def test_main_on_basic(self):
        argv = [TestInputFiles.script, '-q', 'test/basic']
        res = cppsa_main(argv)
        self.assertEqual(res, 0)

    def test_main_on_unknown(self):
        argv = [TestInputFiles.script, '-q', 'test/unknown']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

    def test_main_on_unknown_with_whitelist(self):
        argv = [TestInputFiles.script, '-q', '--whitelist', 'test/unknown-wl',
                'test/unknown']
        res = cppsa_main(argv)
        self.assertFalse(res)

    def test_main_on_unmarked_endif(self):
        argv = [TestInputFiles.script, '-q', 'test/unmarked-endif']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

    def test_main_on_suggest_inline_func(self):
        argv = [TestInputFiles.script, '-q', 'test/inline-func']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

    def test_main_on_empty_diag_list(self):
        argv = [TestInputFiles.script, '-q', '-D-all','test/file-with-problems']
        res = cppsa_main(argv)
        self.assertEqual(res, 0)

    def test_main_on_multi_line_concat(self):
        # Suppress multi-line warning
        argv = [TestInputFiles.script, '-q', '-Dall,-2','test/two-lines-as-one']
        res = cppsa_main(argv)
        self.assertEqual(res, 0)

    def test_main_on_directive_inside_comment(self):
        argv = [TestInputFiles.script, '-q', '-Dall',
                'test/directive-inside-comment']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

    def test_main_on_directive_inside_slashes(self):
        argv = [TestInputFiles.script, '-q', '-Dall',
                'test/directive-inside-slashes']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

    def test_main_on_directive_inside_quotes(self):
        argv = [TestInputFiles.script, '-q', '-Dall,-2',
                'test/directive-inside-quotes']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

    def test_main_on_static_inline_vs_static_void(self):
        # Should not suggest do {} while to static inline returning non-void
        argv = [TestInputFiles.script, '-q', '-Dall,-2,-13',
                'test/double-diags']
        res = cppsa_main(argv)
        self.assertEqual(res, 0)

    def test_main_on_junk_inside_comments(self):
        # Should not suggest do {} while to static inline returning non-void
        argv = [TestInputFiles.script,'-q', 'test/not-directive-inside-comment']
        res = cppsa_main(argv)
        self.assertEqual(res, 0)

class TestCommandLineOptions(unittest.TestCase):
    def test_analyze_true_preprocessor(self):
        argv = [TestInputFiles.script, 'test/true-preprocessor']
        res = cppsa_main(argv)
        self.assertEqual(res, 0)

        argv = [TestInputFiles.script, '-q', '--analyze-true-preprocessor',
                'test/true-preprocessor']
        res = cppsa_main(argv)
        self.assertEqual(res, 1)

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

class TestContinuedMultilineDirective(unittest.TestCase):
    def test_full_text_combining(self):
        directive = PreprocessorDirective(["aa\\", "bb"], 1)
        ft = directive.full_text
        self.assertEqual(ft, "aa bb")

        directive = PreprocessorDirective(["cc\\"], 2)
        ft = directive.full_text
        self.assertEqual(ft, "cc")

        directive = PreprocessorDirective(["dd\\\n", "ee"], 3)
        ft = directive.full_text
        self.assertEqual(ft, "dd ee")

        directive = PreprocessorDirective(["ff\t\\", "gg"], 4)
        ft = directive.full_text
        self.assertEqual(ft, "ff\tgg")

        directive = PreprocessorDirective(["hh", "jj"], 5)
        ft = directive.full_text
        self.assertEqual(ft, "hh jj")

class TestMacroTricks(unittest.TestCase):
    def test_line_and_file(self):
        directive = PreprocessorDirective(['#define A "file" __FILE__'], 1)
        self.assertTrue(directive.uses_macro_tricks())

        directive = PreprocessorDirective(['#define A "line" __LINE__'], 2)
        self.assertTrue(directive.uses_macro_tricks())

    def test_no_match(self):
        directive = PreprocessorDirective(["#ifdef __GNUC__"], 1)
        self.assertFalse(directive.uses_macro_tricks())

    def test_concat(self):
        directive = PreprocessorDirective(['#define A(x,y) A##B'], 1)
        self.assertTrue(directive.uses_macro_tricks())

    def test_stringify(self):
        directive = PreprocessorDirective(['#define A(x,y) A #x'], 1)
        self.assertTrue(directive.uses_macro_tricks())

    def test_variadic(self):
        directive = PreprocessorDirective(['#define PP(x,...) printf(x)'], 1)
        self.assertTrue(directive.uses_macro_tricks())

        # Mangle ellipsis ... so that it will not trigger the match
        directive = PreprocessorDirective(
            "#define eprintf(. . .) fprintf (stderr, __VA_ARGS__)", 1)
        self.assertTrue(directive.uses_macro_tricks())

    def test_inside_comment(self):
        # Should not treat the second hash as it is inside a comment
        directive = PreprocessorDirective(['#endif // #define A'], 1)
        self.assertFalse(directive.uses_macro_tricks())

        directive = PreprocessorDirective(['#endif /* #define B */'], 2)
        self.assertFalse(directive.uses_macro_tricks())

class TestSimpleDirectives(unittest.TestCase):

    def test_indented_directive(self):
        directive = PreprocessorDirective("        #define SYMBOL", 1)
        res = LeadingWhitespaceDiagnostic.apply(directive)
        self.assertTrue(res)

    def test_unknown_directive(self):
        directive = PreprocessorDirective("#unknown I am something unknown", 1)
        res = UnknownDirectiveDiagnostic.apply(directive)
        self.assertIsInstance(res, UnknownDirectiveDiagnostic)

        directive = PreprocessorDirective(
            "### I am decoration inside comment ###",
            1,
            Context.COMMENT)
        res = UnknownDirectiveDiagnostic.apply(directive)
        self.assertIsNone(res)

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

    def test_complex_if_condition_for_multiline(self):
        directive = PreprocessorDirective(["#if LINUX ||\\\n", "WINDOWS"], 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertIsInstance(res, ComplexIfConditionDiagnostic)

        directive = PreprocessorDirective(
            ["#if LINUX_IS_SO_COOL_IT_NEEDS_A_LONG_DEFINE \\\n",
             "/* This is harmless comment*/"], 1)
        res = ComplexIfConditionDiagnostic.apply(directive)
        self.assertFalse(res)

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

    def test_suggest_void_function_accept(self):
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

    def test_suggest_void_function_reject(self):
        directive = PreprocessorDirective("#define F() dobado", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#define do something", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertFalse(res)
        directive = PreprocessorDirective("#pragma random do something", 1)
        res = SuggestVoidDiagnostic.apply(directive)
        self.assertFalse(res)

    def test_suggest_better_constant_accept(self):
        directive = PreprocessorDirective("#define A 1", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

        directive = PreprocessorDirective("#define B 0xabcd", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

        directive = PreprocessorDirective('#define C "string"', 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

        directive = PreprocessorDirective('#define D -5', 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

    def test_suggest_better_constant_accept_special(self):
        directive = PreprocessorDirective("#define A UINT64_C(1)", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

        directive = PreprocessorDirective("#define B BIT(999)", 2)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

        directive = PreprocessorDirective("#define C UINT32_C(~0x1ff)", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertIsInstance(res, SuggestConstantDiagnostic)

    def test_suggest_better_constant_reject(self):
        directive = PreprocessorDirective("#define A", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#define B() 1", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#define C(x) 1", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#ifdef D", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#define E 1 + f(x)", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective('#define F 2 - 3', 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective('#define G //comment', 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective('#define H \\', 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

    def test_suggest_better_constant_reject_too_complex(self):
        # Too complex to figure out the constant means the diagnostic will not
        # be reported for the following cases. Ideally, these cases should be
        # to start being recognized

        directive = PreprocessorDirective("#define A (400)", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#define B (uint64_t)400", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#define C (1 << 30)", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective("#define D ~UINT32_C(0x1ff)", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertFalse(res)

    def test_suggest_better_constant_symbol_is_mentioned_in_details(self):
        directive = PreprocessorDirective("#define THIS_IS_SYMBOL 0", 1)
        res = SuggestConstantDiagnostic.apply(directive)
        self.assertTrue(res)
        found_symbol = res.details.find("THIS_IS_SYMBOL") != -1
        self.assertTrue(found_symbol)

    def test_too_long_define(self):
        directive = PreprocessorDirective(["#define SYMBOL \\",
                                           "one more line\\",
                                           "and one more\\",
                                           "it goes on and on\\",
                                           "I am getting tired\\",
                                           "now that is too long"], 1)
        res = TooLongDefineDiagnostic.apply(directive)
        self.assertIsInstance(res, TooLongDefineDiagnostic)

        directive = PreprocessorDirective(["#define SYMBOL \\",
                                           "one more line\\",
                                           "just not too long"], 2)
        res = TooLongDefineDiagnostic.apply(directive)
        self.assertFalse(res)

        directive = PreprocessorDirective(["#ifdef SYMBOL \\",
                                           "this is not a define\\",
                                           "why so many lines"], 3)
        res = TooLongDefineDiagnostic.apply(directive)
        self.assertFalse(res) # not a #define

    def test_multiline_condition(self):
        directive = PreprocessorDirective(["#if expr1 \\",
                                           "&& second part expression"], 1)
        res = MultilineConditionalDiagnostic.apply(directive)
        self.assertIsInstance(res, MultilineConditionalDiagnostic)

        directive = PreprocessorDirective(["#ifdef \\",
                                           "WHY_IS_IT_ON_NEXT_LINE"], 2)
        res = MultilineConditionalDiagnostic.apply(directive)
        self.assertFalse(res)


class TestScopeDirectives(unittest.TestCase):
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

    def test_ifdef_nesting_with_single_global_cplusplus(self):
        dirs = (
            PreprocessorDirective("#ifdef __cplusplus", 1),
            PreprocessorDirective("#if C == B", 3),
            PreprocessorDirective("#ifdef D", 4),

            PreprocessorDirective("#endif // D", 11),
            PreprocessorDirective("#endif // C == B", 12),
            PreprocessorDirective("#endif // __cplusplus", 13),
        )
        res = IfdefNestingDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 0)

    def test_ifdef_nesting_with_several_cplusplus(self):
        dirs = (
            PreprocessorDirective("#ifdef __cplusplus", 1),
            PreprocessorDirective("#if C == B", 3),
            PreprocessorDirective("#ifdef D", 4),

            PreprocessorDirective("#endif // D", 11),
            PreprocessorDirective("#endif // C == B", 12),
            PreprocessorDirective("#endif // __cplusplus", 13),

            PreprocessorDirective("#ifdef __cplusplus", 20),
            PreprocessorDirective("#endif // second __cplusplus", 24),
        )
        res = IfdefNestingDiagnostic.apply_to_lines(dirs)
        self.assertTrue(len(res) == 1)

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

class TestLanguageContext(unittest.TestCase):
    def test_into_comment(self):
        lines = ["aaaa /*   \n", "bbbb \n"]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.COMMENT)

    def test_after_comment_closed(self):
        lines = ["aaaa /*   \n", "bbbb \n", "ccc */ dddd\n"]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.OUTSIDE)

    def test_inside_comment(self):
        lines = ["/*aaaa /*   \n"]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.COMMENT)

        lines = ["/* bbbb \n", "// cccc" ]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.COMMENT)

    def test_slash_comment(self):
        lines = ["aaaa //   \n"]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.OUTSIDE)

        lines = ["bbbb // /*  \n"]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.OUTSIDE)

        lines = ["\ncccc // dddd"]
        new_context = update_language_context(lines, Context.OUTSIDE)
        self.assertEqual(new_context, Context.SLASH_COMMENT)

class TestDirectivesInContext(unittest.TestCase):
    def test_directive_insize_wrong_context(self):
        directive = PreprocessorDirective("#define A", 1, Context.COMMENT)
        res = WrongContextDiagnostic.apply(directive)
        self.assertIsInstance(res, WrongContextDiagnostic)


if __name__ == '__main__':
    unittest.main()
