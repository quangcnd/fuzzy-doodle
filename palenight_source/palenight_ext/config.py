"""Cấu hình trung tâm và các Token mở rộng cho VS Code Palenight."""
from pygments.token import Name, Punctuation, Whitespace


class PalenightConfig:
    """Chứa toàn bộ cấu hình màu sắc, font chữ và tuỳ chọn bật/tắt Indent-Rainbow."""

    # --- 1. Cấu hình Bật / Tắt Indent-Rainbow ---
    # Có thể bật/tắt mặc định tại đây, hoặc qua biến môi trường PALENIGHT_INDENT_RAINBOW=0/1,
    # hoặc truyền trực tiếp trên dòng lệnh: -O indent_rainbow=false
    ENABLE_INDENT_RAINBOW = True
    TAB_WIDTH             = 4
    INDENT_GUIDE_COLOR    = "#3E4460"
    INDENT_COLORS = (
        "#383C40",  # Cấp 1: rgba(255, 255, 64, 0.07)  trên #292D3E
        "#2F3C43",  # Cấp 2: rgba(127, 255, 127, 0.07) trên #292D3E
        "#38334B",  # Cấp 3: rgba(255, 127, 255, 0.07) trên #292D3E
        "#2C3A4A",  # Cấp 4: rgba(79, 236, 236, 0.07)  trên #292D3E
    )

    # --- 2. Cấu hình Font & Xuất ảnh mặc định ---
    DEFAULT_FONT_SIZE = 20
    DEFAULT_LINE_PAD  = 6
    DEFAULT_IMAGE_PAD = 14

    PREFERRED_FONTS = [
        "Consolas",
        "JetBrains Mono",
        "Cascadia Code",
        "Fira Code",
        "Source Code Pro",
        "Courier New",
    ]

    FONT_ALIASES = {
        "consolas":     ["Consolas", "consola.ttf"],
        "jetbrains":    ["JetBrains Mono", "JetBrainsMono NF", "JetBrainsMono Nerd Font", "JetBrainsMono-Regular.ttf"],
        "jb":           ["JetBrains Mono", "JetBrainsMono NF", "JetBrainsMono-Regular.ttf"],
        "cascadia":     ["Cascadia Code", "Cascadia Mono", "CascadiaCode NF", "CascadiaCode.ttf"],
        "fira":         ["Fira Code", "FiraCode NF", "FiraCode Nerd Font", "FiraCode-Regular.ttf"],
        "firacode":     ["Fira Code", "FiraCode NF", "FiraCode-Regular.ttf"],
        "sourcecode":   ["Source Code Pro", "SourceCodePro-Regular.ttf"],
        "ubuntu":       ["Ubuntu Mono", "UbuntuMono-Regular.ttf"],
        "dejavu":       ["DejaVu Sans Mono", "DejaVuSansMono.ttf"],
        "hack":         ["Hack", "Hack NF", "Hack-Regular.ttf"],
        "iosevka":      ["Iosevka", "Iosevka Term", "Iosevka-Regular.ttc"],
        "mononoki":     ["mononoki", "mononoki-Regular.ttf"],
        "inconsolata":  ["Inconsolata", "Inconsolata-Regular.ttf"],
        "courier":      ["Courier New", "cour.ttf"],
    }

    # --- 3. Bảng màu VS Code Palenight ---
    BG           = "#292D3E"
    FG           = "#BFC7D5"   # editor.foreground
    LINE_NUM_FG  = "#4E5579"   # editorLineNumber.foreground
    LINE_NUM_BG  = "#292D3E"   # editorLineNumber.background
    HIGHLIGHT_BG = "#3A3F58"   # editor.selectionBackground
    COMMENT      = "#697098"
    PURPLE       = "#C792EA"   # keyword, storage.type, rainbow bracket cấp 2
    BLUE         = "#82AAFF"   # function, macro name, custom type <ll>, rainbow bracket cấp 3
    PARAM        = "#82A0C2"   # variable.parameter (tham số hàm &x, &y)
    CYAN         = "#89DDFF"   # operator, punctuation
    YELLOW       = "#FFCB6B"   # variable, class, STL (vector, pair, cin, cout), rainbow bracket cấp 1
    GREEN        = "#C3E88D"   # string, char
    ORANGE       = "#F78C6C"   # number
    RED          = "#FF5572"   # tag, this/self, exception
    PINK         = "#FF5874"   # constant.language
    TEAL         = "#80CBC4"   # regex


# Các Token mở rộng dùng chung giữa các module
BRACKET_1 = Punctuation.Bracket.L1
BRACKET_2 = Punctuation.Bracket.L2
BRACKET_3 = Punctuation.Bracket.L3
BRACKET_LEVELS = (BRACKET_1, BRACKET_2, BRACKET_3)

INDENT_1 = Whitespace.Indent.L1
INDENT_2 = Whitespace.Indent.L2
INDENT_3 = Whitespace.Indent.L3
INDENT_4 = Whitespace.Indent.L4
INDENT_LEVELS = (INDENT_1, INDENT_2, INDENT_3, INDENT_4)
INDENT_BG_MAP = dict(zip(INDENT_LEVELS, PalenightConfig.INDENT_COLORS))

NAME_PARAM = Name.Variable.Parameter
