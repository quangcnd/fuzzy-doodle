"""Module kết nối các bộ xử lý (Font, Indent-Rainbow, C++ Semantic) vào Pygments Formatters & Lexers."""
import os
from .config import PalenightConfig, INDENT_LEVELS, INDENT_BG_MAP
from .fonts import FontRegistry
from .indent_rainbow import IndentRainbowProcessor
from .cpp_analyzer import CppSemanticAnalyzer


class FormatterPatcher:
    """Module kết nối `FontRegistry`, `IndentRainbowProcessor` và `CppSemanticAnalyzer`
    vào Pygments (`CppLexer`, `FontManager`, `ImageFormatter`, `LatexFormatter`).
    Hỗ trợ tùy chọn `-O indent_rainbow=false` hoặc `-O indent_rainbow=true` ngay trên CLI.
    """

    @classmethod
    def apply_all(cls):
        cls.patch_cpp_lexer()
        cls.patch_image_formatter()
        cls.patch_latex_formatter()

    @classmethod
    def patch_cpp_lexer(cls):
        try:
            from pygments.lexers.c_cpp import CFamilyLexer, CppLexer
            if getattr(CppLexer, "_palenight_patched", False):
                return
            CppLexer._palenight_patched = True

            orig_cpp_init = CppLexer.__init__

            def _cpp_init(self, **options):
                if "indent_rainbow" in options:
                    self._indent_rainbow_opt = options.get("indent_rainbow")
                    IndentRainbowProcessor.set_enabled(
                        IndentRainbowProcessor.is_enabled(self._indent_rainbow_opt)
                    )
                else:
                    self._indent_rainbow_opt = None
                orig_cpp_init(self, **options)

            def get_tokens_unprocessed(self, text, stack=('root',)):
                yield from CppSemanticAnalyzer.analyze(self, CFamilyLexer, text, stack)

            CppLexer.__init__ = _cpp_init
            CppLexer.get_tokens_unprocessed = get_tokens_unprocessed
        except Exception:
            pass

    @classmethod
    def patch_image_formatter(cls):
        try:
            from pygments.formatters.img import ImageFormatter, FontManager, ImageDraw, ImageFont
            if getattr(ImageFormatter, "_palenight_indent_patched", False):
                return
            ImageFormatter._palenight_indent_patched = True

            # 1. Nâng cấp FontManager để hỗ trợ alias, thư mục font User và nạp đủ Bold/Italic
            orig_fm_init = FontManager.__init__

            def _smart_fm_init(self, font_name, font_size=14):
                resolved_name = FontRegistry.resolve_preferred_font(font_name)
                try:
                    orig_fm_init(self, resolved_name, font_size)
                except Exception:
                    normal_path = FontRegistry.find_font_file(resolved_name, "NORMAL")
                    if not normal_path:
                        normal_path = FontRegistry.find_font_file("Consolas", "NORMAL")
                    if not normal_path:
                        raise
                    self.font_name = resolved_name
                    self.font_size = font_size
                    self.fonts = {}
                    self.encoding = None
                    self.variable = False
                    self.fonts["NORMAL"] = ImageFont.truetype(normal_path, font_size)
                    for st in ("BOLD", "ITALIC", "BOLDITALIC"):
                        st_path = FontRegistry.find_font_file(resolved_name, st)
                        if st_path:
                            self.fonts[st] = ImageFont.truetype(st_path, font_size)
                        else:
                            self.fonts[st] = self.fonts.get("BOLD" if st == "BOLDITALIC" else "NORMAL", self.fonts["NORMAL"])
                    return

                if getattr(self, "variable", False):
                    for st in ("BOLD", "ITALIC", "BOLDITALIC"):
                        st_path = FontRegistry.find_font_file(resolved_name, st)
                        if st_path and os.path.isfile(st_path):
                            try:
                                self.fonts[st] = ImageFont.truetype(st_path, font_size)
                                self.variable = False
                            except Exception:
                                pass

            FontManager.__init__ = _smart_fm_init

            # 2. Nâng cấp ImageFormatter.__init__ để nhận tùy chọn `indent_rainbow` & thông số mặc định
            orig_img_init = ImageFormatter.__init__

            def _smart_img_init(self, **options):
                if "indent_rainbow" in options:
                    self._indent_rainbow_enabled = IndentRainbowProcessor.is_enabled(options.get("indent_rainbow"))
                    IndentRainbowProcessor.set_enabled(self._indent_rainbow_enabled)
                else:
                    self._indent_rainbow_enabled = None

                options.setdefault("font_size", PalenightConfig.DEFAULT_FONT_SIZE)
                options.setdefault("line_pad", PalenightConfig.DEFAULT_LINE_PAD)
                options.setdefault("image_pad", PalenightConfig.DEFAULT_IMAGE_PAD)
                options.setdefault("line_number_fg", PalenightConfig.LINE_NUM_FG)
                options.setdefault("line_number_bg", PalenightConfig.LINE_NUM_BG)
                options.setdefault("line_number_separator", False)
                options.setdefault("line_number_chars", 3)
                orig_img_init(self, **options)

            ImageFormatter.__init__ = _smart_img_init

            # 3. Nâng cấp vẽ Indent-Rainbow + vạch dẫn hướng trên ảnh (tự tắt nếu indent_rainbow=False)
            def _create_drawables(self, tokensource):
                lineno = charno = maxcharno = 0
                maxlinelength = linelength = 0
                self._indent_rects = []
                line_height = self._get_line_height()
                ir_active = IndentRainbowProcessor.is_enabled(getattr(self, "_indent_rainbow_enabled", None))

                for ttype, value in tokensource:
                    orig_ttype = ttype
                    while ttype not in self.styles:
                        ttype = ttype.parent
                    style = self.styles[ttype]
                    value = value.expandtabs(PalenightConfig.TAB_WIDTH)
                    lines = value.splitlines(True)

                    for line in lines:
                        temp = line.rstrip('\r\n')
                        if temp:
                            pos = self._get_text_pos(linelength, lineno)
                            temp_width, _ = self.fonts.get_text_size(temp)
                            if ir_active and orig_ttype in INDENT_LEVELS:
                                bg_col = self._get_text_bg_color(style)
                                if bg_col:
                                    self._indent_rects.append((
                                        pos[0],
                                        pos[1],
                                        pos[0] + temp_width,
                                        pos[1] + line_height,
                                        bg_col,
                                    ))
                            self._draw_text(
                                pos,
                                temp,
                                font=self._get_style_font(style),
                                text_fg=self._get_text_color(style),
                                text_bg=None if orig_ttype in INDENT_LEVELS else self._get_text_bg_color(style),
                            )
                            linelength += temp_width
                            maxlinelength = max(maxlinelength, linelength)
                            charno += len(temp)
                            maxcharno = max(maxcharno, charno)
                        if line.endswith('\n') or line.endswith('\r'):
                            linelength = 0
                            charno = 0
                            lineno += 1

                self.maxlinelength = maxlinelength
                self.maxcharno = maxcharno
                self.maxlineno = lineno

            def _format(self, tokensource, outfile):
                self._create_drawables(tokensource)
                self._draw_line_numbers()
                from PIL import Image
                im = Image.new(
                    'RGB',
                    self._get_image_size(self.maxlinelength, self.maxlineno),
                    self.background_color
                )
                self._paint_line_number_bg(im)
                draw = ImageDraw.Draw(im)

                for x0, y0, x1, y1, bg_col in getattr(self, '_indent_rects', ()):
                    draw.rectangle([x0, y0, x1, y1], fill=bg_col)
                    draw.line([(x0, y0), (x0, y1)], fill=PalenightConfig.INDENT_GUIDE_COLOR, width=1)

                if self.hl_lines:
                    x = self.image_pad + self.line_number_width - self.line_number_pad + 1
                    recth = self._get_line_height()
                    rectw = im.size[0] - x
                    for linenumber in self.hl_lines:
                        y = self._get_line_y(linenumber - 1)
                        draw.rectangle([(x, y), (x + rectw, y + recth)],
                                       fill=self.hl_color)
                for pos, value, font, text_fg, text_bg in self.drawables:
                    if text_bg:
                        if hasattr(draw, 'textsize'):
                            text_size = draw.textsize(text=value, font=font)
                        else:
                            text_size = font.getbbox(value)[2:]
                        draw.rectangle([pos[0], pos[1], pos[0] + text_size[0], pos[1] + text_size[1]], fill=text_bg)
                    draw.text(pos, value, font=font, fill=text_fg)
                im.save(outfile, self.image_format.upper())

            ImageFormatter._create_drawables = _create_drawables
            ImageFormatter.format = _format
        except Exception:
            pass

    @classmethod
    def patch_latex_formatter(cls):
        try:
            from pygments.formatters.latex import LatexFormatter, _get_ttype_name
            if getattr(LatexFormatter, "_palenight_indent_patched", False):
                return
            LatexFormatter._palenight_indent_patched = True
            orig_latex_init = LatexFormatter.__init__
            orig_create_stylesheet = LatexFormatter._create_stylesheet

            def _rgbcolor(col):
                return ','.join(['%.2f' % (int(col[i] + col[i + 1], 16) / 255.0) for i in (0, 2, 4)])

            guide_rgb = _rgbcolor(PalenightConfig.INDENT_GUIDE_COLOR.lstrip('#'))

            def _latex_init(self, **options):
                if "indent_rainbow" in options:
                    self._indent_rainbow_enabled = IndentRainbowProcessor.is_enabled(options.get("indent_rainbow"))
                    IndentRainbowProcessor.set_enabled(self._indent_rainbow_enabled)
                else:
                    self._indent_rainbow_enabled = None
                orig_latex_init(self, **options)

            def _latex_create_stylesheet(self):
                orig_create_stylesheet(self)
                ir_active = IndentRainbowProcessor.is_enabled(getattr(self, "_indent_rainbow_enabled", None))
                cp = self.commandprefix
                for ind_tok, hex_bg in INDENT_BG_MAP.items():
                    tname = _get_ttype_name(ind_tok)
                    if ir_active:
                        bg_rgb = _rgbcolor(hex_bg.lstrip('#'))
                        vrule_dim = r'height 0.74\baselineskip depth 0.31\baselineskip'
                        box_cmd = (
                            rf'\smash{{{{\setlength{{\fboxsep}}{{0pt}}'
                            rf'\rlap{{\textcolor[rgb]{{{guide_rgb}}}{{\vrule width 0.4pt {vrule_dim}}}}}'
                            rf'\colorbox[rgb]{{{bg_rgb}}}{{\vrule width 0pt {vrule_dim}##1}}}}}}'
                        )
                        cmndef = (
                            rf'\def\{cp}@bc##1{{'
                            rf'\ifcsname ifIndentRainbow\endcsname'
                            rf'\ifIndentRainbow{box_cmd}\else##1\fi'
                            rf'\else{box_cmd}\fi}}'
                        )
                        self.ttype2name[ind_tok] = tname
                        self.cmd2def[tname] = cmndef
                    else:
                        self.cmd2def.pop(tname, None)

            LatexFormatter.__init__ = _latex_init
            LatexFormatter._create_stylesheet = _latex_create_stylesheet
        except Exception:
            pass
