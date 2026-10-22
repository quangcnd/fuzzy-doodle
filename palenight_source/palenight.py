"""Palenight Theme for Pygments (VS Code style).

File chính được giữ ngắn gọn và sạch sẽ. Toàn bộ các tính năng nâng cao
được tách thành các module độc lập trong thư mục `pygments/styles/palenight_ext/`:
- `config.py`         : `PalenightConfig` (bảng màu, cấu hình font, cờ bật/tắt `ENABLE_INDENT_RAINBOW`).
- `fonts.py`          : `FontRegistry` (quản lý alias font, quét thư mục font Windows & User).
- `indent_rainbow.py` : `IndentRainbowProcessor` (xử lý thụt lề 4 cấp & bật/tắt động).
- `cpp_analyzer.py`   : `CppSemanticAnalyzer` (phân tích ngữ nghĩa C++, `#define`, `template`, `struct`, Rainbow Brackets).
- `patchers.py`       : `FormatterPatcher` (kết nối vào `CppLexer`, `ImageFormatter`, `LatexFormatter`).

Cách bật / tắt `indent-rainbow`:
1. Trên dòng lệnh (CLI):
       python -m pygments -O style=palenight,indent_rainbow=false -o main.png main.cpp
       python -m pygments -O style=palenight,indent_rainbow=true  -o main.png main.cpp
2. Qua biến môi trường:
       $env:PALENIGHT_INDENT_RAINBOW="0"
3. Trong code Python hoặc sửa mặc định tại `palenight_ext/config.py`:
       from pygments.styles.palenight import set_indent_rainbow
       set_indent_rainbow(False)
"""
from pygments.style import Style
from pygments.token import (
    Keyword, Name, Comment, String, Error, Escape,
    Number, Operator, Generic, Whitespace, Text,
    Punctuation, Literal, Token
)

from pygments.styles.palenight_ext import (
    PalenightConfig,
    FontRegistry,
    IndentRainbowProcessor,
    CppSemanticAnalyzer,
    FormatterPatcher,
    BRACKET_1, BRACKET_2, BRACKET_3,
    INDENT_1, INDENT_2, INDENT_3, INDENT_4,
    NAME_PARAM,
)


def set_indent_rainbow(enabled: bool):
    """Hàm tiện ích bật / tắt tính năng indent-rainbow."""
    IndentRainbowProcessor.set_enabled(enabled)


def register_font(alias: str, *candidates: str):
    """Hàm tiện ích đăng ký thêm font mới."""
    FontRegistry.register_font(alias, *candidates)


def _patch_cpp_lexer():
    """Kích hoạt các bản vá cho CppLexer và Formatters."""
    FormatterPatcher.apply_all()


_patch_cpp_lexer()


class PalenightStyle(Style):
    """
    Palenight Theme (Olaolu Olawuyi) - VS Code Semantic Highlighting + Rainbow Brackets + Indent-Rainbow.
    """
    name = 'palenight'
    background_color = PalenightConfig.BG
    highlight_color  = PalenightConfig.HIGHLIGHT_BG
    line_number_color = PalenightConfig.LINE_NUM_FG
    line_number_background_color = PalenightConfig.LINE_NUM_BG

    C = PalenightConfig

    styles = {
        Token:                  C.FG,
        Text:                   C.FG,
        Whitespace:             C.FG,
        Escape:                 C.CYAN,

        # Indent-Rainbow (4 cấp độ màu nền thụt lề của VS Code)
        INDENT_1:               f"bg:{C.INDENT_COLORS[0]} {C.FG}",
        INDENT_2:               f"bg:{C.INDENT_COLORS[1]} {C.FG}",
        INDENT_3:               f"bg:{C.INDENT_COLORS[2]} {C.FG}",
        INDENT_4:               f"bg:{C.INDENT_COLORS[3]} {C.FG}",

        # Comment
        Comment:                "italic " + C.COMMENT,
        Comment.Hashbang:       "italic " + C.COMMENT,
        Comment.Multiline:      "italic " + C.COMMENT,
        Comment.Single:         "italic " + C.COMMENT,
        Comment.Special:        "italic " + C.COMMENT,
        Comment.Preproc:        "noitalic " + C.PURPLE,   # #include, #define
        Comment.PreprocFile:    "noitalic " + C.GREEN,    # <bits/stdc++.h>

        # Keyword
        Keyword:                C.PURPLE,                 # for, if, return, template, class, const...
        Keyword.Constant:       C.BLUE,                   # true, false, nullptr
        Keyword.Declaration:    C.PURPLE,
        Keyword.Namespace:      C.PURPLE,
        Keyword.Pseudo:         C.PURPLE,
        Keyword.Reserved:       C.PURPLE,
        Keyword.Type:           C.PURPLE,                 # int, long, double, unsigned, bool...

        # Operator & Punctuation + Rainbow Brackets
        Operator:               C.CYAN,                   # =, +, -, *, /, <<, >>, <=, &
        Operator.Word:          C.PURPLE,                 # and, or, not
        Punctuation:            C.CYAN,                   # ; , : .
        BRACKET_1:              C.YELLOW,                 # Ngoặc cấp 1: Vàng
        BRACKET_2:              C.PURPLE,                 # Ngoặc cấp 2: Tím
        BRACKET_3:              C.BLUE,                   # Ngoặc cấp 3: Xanh dương

        # Name
        Name:                   C.YELLOW,                 # Biến mặc định màu vàng như ảnh VS Code
        Name.Attribute:         C.YELLOW,
        Name.Builtin:           C.BLUE,                   # true, false, kiểu macro/typedef <ll>
        Name.Builtin.Pseudo:    "italic " + C.RED,        # this, self
        Name.Class:             C.YELLOW,                 # vector, pair, Trie, Node, cin, cout
        Name.Constant:          C.ORANGE,
        Name.Decorator:         C.BLUE,
        Name.Entity:            C.BLUE,
        Name.Exception:         C.YELLOW,
        Name.Function:          C.BLUE,                   # tên hàm & tên macro #define
        Name.Function.Magic:    C.BLUE,
        Name.Label:             C.PURPLE,
        Name.Namespace:         C.YELLOW,                 # std
        Name.Other:             C.YELLOW,
        Name.Property:          C.YELLOW,
        Name.Tag:               C.RED,
        Name.Variable:          C.YELLOW,                 # n, Q, P, m, nmax, mod
        Name.Variable.Class:    C.YELLOW,
        Name.Variable.Global:   C.YELLOW,
        Name.Variable.Instance: C.YELLOW,
        Name.Variable.Magic:    C.BLUE,
        NAME_PARAM:             C.PARAM,                  # Tham số hàm (&x, &y, name, idx, pos) màu #82A0C2

        # Literal / String
        Literal:                C.ORANGE,
        String:                 C.GREEN,
        String.Affix:           C.PURPLE,
        String.Char:            C.GREEN,
        String.Delimiter:       C.GREEN,
        String.Doc:             "italic " + C.COMMENT,
        String.Escape:          C.CYAN,                   # \n, \t trong cả string và char literal '\n'
        String.Interpol:        C.CYAN,
        String.Regex:           C.TEAL,
        String.Symbol:          C.GREEN,

        # Number
        Number:                 C.ORANGE,                 # 0, 1, 3e5, 998244353
        Number.Bin:             C.ORANGE,
        Number.Float:           C.ORANGE,
        Number.Hex:             C.ORANGE,
        Number.Integer:         C.ORANGE,
        Number.Integer.Long:    C.ORANGE,
        Number.Oct:             C.ORANGE,

        # Generic
        Generic.Deleted:        C.RED,
        Generic.Inserted:       C.GREEN,
        Generic.Error:          C.RED,
        Generic.Emph:           "italic " + C.PURPLE,
        Generic.Strong:         "bold " + C.YELLOW,
        Generic.Prompt:         C.COMMENT,
        Generic.Output:         C.FG,
        Generic.Traceback:      C.RED,
        Generic.Heading:        "bold " + C.BLUE,
        Generic.Subheading:     "bold " + C.BLUE,

        Error:                  C.FG,
    }
