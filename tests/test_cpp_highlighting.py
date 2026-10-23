"""Bộ ca kiểm thử tự động cho CppSemanticAnalyzer & Palenight Syntax Highlighting."""
from __future__ import annotations

import unittest
from pygments.lexers.c_cpp import CFamilyLexer, CppLexer
from pygments.token import Keyword, Name, Punctuation, Token

from palenight_source.palenight_ext.cpp_analyzer import CppSemanticAnalyzer
from palenight_source.palenight_ext.config import NAME_PARAM, BRACKET_LEVELS


class TestCppSemanticAnalyzer(unittest.TestCase):
    def setUp(self):
        self.lexer = CppLexer()

    def tokenize(self, code: str):
        return list(CppSemanticAnalyzer.analyze(self.lexer, CFamilyLexer, code))

    def get_token_types_for(self, code: str, target_val: str):
        tokens = self.tokenize(code)
        return [tok for _, tok, val in tokens if val == target_val]

    def test_multiline_macro_continuation(self):
        code = (
            "#define FOO(a, b) \\\n"
            "    int x = (a) + (b); \\\n"
            "    int y = x * 2;\n"
            "int main() { return 0; }"
        )
        tokens = self.tokenize(code)
        # Kiểm tra tham số macro 'a' và 'b' được tô màu
        tok_a = [tok for _, tok, val in tokens if val == 'a']
        self.assertTrue(len(tok_a) >= 1)
        self.assertEqual(tok_a[0], NAME_PARAM)

        # Thân macro không bị biến thành toàn bộ Comment.Preproc mà được phân tích cú pháp C++
        has_kw_int = any(tok is Keyword.Type for _, tok, val in tokens if val == 'int')
        self.assertTrue(has_kw_int, "Từ khóa 'int' trong thân macro phải được phân tích đúng kiểu Keyword.Type")

    def test_lambda_parameters(self):
        code = "auto func = [&](int x, int y) { return x + y; };"
        tokens = self.tokenize(code)
        tok_x = [tok for _, tok, val in tokens if val == 'x']
        tok_y = [tok for _, tok, val in tokens if val == 'y']
        self.assertTrue(len(tok_x) >= 1)
        self.assertTrue(len(tok_y) >= 1)
        self.assertEqual(tok_x[0], NAME_PARAM, "Tham số x trong lambda phải là NAME_PARAM")
        self.assertEqual(tok_y[0], NAME_PARAM, "Tham số y trong lambda phải là NAME_PARAM")

    def test_unbalanced_brace_in_macro_isolation(self):
        code = (
            "#define BEGIN {\n"
            "int main() {\n"
            "    return 0;\n"
            "}"
        )
        tokens = self.tokenize(code)
        # Dấu { trong main() phải bắt đầu từ Level 0 (BRACKET_LEVELS[0]), không bị lệch do #define BEGIN {
        main_braces = [tok for _, tok, val in tokens if val == '{' and tok in BRACKET_LEVELS]
        self.assertTrue(len(main_braces) >= 2)
        # Dấu { thứ hai (của main) phải là BRACKET_LEVELS[0]
        self.assertEqual(main_braces[1], BRACKET_LEVELS[0], "Dấu ngoặc của main() không được bị lệch độ sâu rainbow bởi macro")

    def test_template_vs_comparison_ambiguity(self):
        # Biểu thức f(a < b, c > d) không phải template
        code1 = "void solve() { f(a < b, c > d); }"
        tokens1 = self.tokenize(code1)
        b_toks = [tok for _, tok, val in tokens1 if val == 'b']
        self.assertTrue(all(tok is not Name.Builtin for tok in b_toks))

        # Khai báo template vector<int>
        code2 = "vector<int> v;"
        tokens2 = self.tokenize(code2)
        int_toks = [tok for _, tok, val in tokens2 if val == 'int']
        self.assertTrue(len(int_toks) >= 1)

    def test_constructor_init_list_with_braces(self):
        code = (
            "struct Point {\n"
            "    int x, y;\n"
            "    Point(int a, int b) : x{a}, y{b} {\n"
            "        int z = 10;\n"
            "    }\n"
            "};"
        )
        tokens = self.tokenize(code)
        x_toks = [tok for _, tok, val in tokens if val == 'x']
        # Member x trong : x{a} phải là Name.Variable chứ không bị nhầm thành Name.Function
        self.assertIn(Name.Variable, x_toks)
        # Tham số a, b phải là NAME_PARAM
        a_toks = [tok for _, tok, val in tokens if val == 'a']
        self.assertIn(NAME_PARAM, a_toks)

    def test_function_prototype_parameters(self):
        code = "int compute(int val_a, double val_b);"
        tokens = self.tokenize(code)
        tok_a = [tok for _, tok, val in tokens if val == 'val_a']
        tok_b = [tok for _, tok, val in tokens if val == 'val_b']
        self.assertTrue(len(tok_a) >= 1)
        self.assertTrue(len(tok_b) >= 1)
        self.assertEqual(tok_a[0], NAME_PARAM, "Tham số trong prototype phải là NAME_PARAM")
        self.assertEqual(tok_b[0], NAME_PARAM, "Tham số trong prototype phải là NAME_PARAM")

    def test_type_aliases_using_and_typedef(self):
        code = (
            "using ll = long long;\n"
            "typedef unsigned long long ull;\n"
            "ll a = 10;\n"
            "ull b = 20;\n"
        )
        tokens = self.tokenize(code)
        ll_types = [tok for _, tok, val in tokens if val == 'll']
        ull_types = [tok for _, tok, val in tokens if val == 'ull']
        self.assertIn(Name.Builtin, ll_types)
        self.assertIn(Name.Builtin, ull_types)

    def test_builtins_true_false_nullptr(self):
        code = "bool ok = true; bool no = false; void* p = nullptr;"
        tokens = self.tokenize(code)
        true_tok = [tok for _, tok, val in tokens if val == 'true'][0]
        false_tok = [tok for _, tok, val in tokens if val == 'false'][0]
        null_tok = [tok for _, tok, val in tokens if val == 'nullptr'][0]
        # Không được bị ép sang Name.Variable
        self.assertNotEqual(true_tok, Name.Variable)
        self.assertNotEqual(false_tok, Name.Variable)
        self.assertNotEqual(null_tok, Name.Variable)


if __name__ == "__main__":
    unittest.main()
