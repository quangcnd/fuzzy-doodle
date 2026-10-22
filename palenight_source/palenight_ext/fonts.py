"""Bộ quản lý và cài đặt thêm Font chữ (FontRegistry) cho Pygments."""
import os
import re
from .config import PalenightConfig


class FontRegistry:
    """Tìm kiếm, đăng ký thêm font mới và nạp đầy đủ 4 kiểu (NORMAL, BOLD, ITALIC, BOLDITALIC)
    từ cả Windows Registry lẫn các thư mục Font (`C:\\Windows\\Fonts` và
    `%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts`), khắc phục lỗi `FontNotFound` của Pygments.
    """

    STYLE_SUFFIXES = {
        "NORMAL":     ["", "-Regular", "Regular", "-Retina", "-Medium", "Medium", "-Book"],
        "BOLD":       ["-Bold", "Bold", "b", "bd", "-SemiBold", "SemiBold"],
        "ITALIC":     ["-Italic", "Italic", "-Oblique", "Oblique", "i"],
        "BOLDITALIC": ["-BoldItalic", "BoldItalic", "-BoldOblique", "BoldOblique", "z", "bi"],
    }

    @classmethod
    def register_font(cls, alias, *candidates):
        """Đăng ký thêm một font mới bằng code:
            FontRegistry.register_font("myfont", "My Custom Font", r"D:\\Fonts\\MyFont-Regular.ttf")
        """
        PalenightConfig.FONT_ALIASES[alias.strip().lower()] = list(candidates)

    @classmethod
    def get_windows_font_dirs(cls):
        dirs = []
        win_dir = os.environ.get("WINDIR", r"C:\Windows")
        sys_fonts = os.path.join(win_dir, "Fonts")
        if os.path.isdir(sys_fonts):
            dirs.append(sys_fonts)
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            user_fonts = os.path.join(local_appdata, "Microsoft", "Windows", "Fonts")
            if os.path.isdir(user_fonts):
                dirs.append(user_fonts)
        return dirs

    @classmethod
    def find_font_file(cls, query, style="NORMAL"):
        """Tìm đường dẫn file `.ttf/.otf/.ttc` tương ứng với `query` và `style`."""
        if not query:
            return None

        if os.path.isfile(query):
            if style == "NORMAL":
                return query
            base_dir = os.path.dirname(query)
            base_stem = re.sub(r'(-Regular|Regular)$', '', os.path.splitext(os.path.basename(query))[0], flags=re.I)
            for ext in (".ttf", ".otf", ".ttc"):
                for suf in cls.STYLE_SUFFIXES.get(style, []):
                    cand_p = os.path.join(base_dir, f"{base_stem}{suf}{ext}")
                    if os.path.isfile(cand_p):
                        return cand_p
            return query

        norm_key = query.strip().lower()
        candidates = list(PalenightConfig.FONT_ALIASES.get(norm_key, [query]))
        if query not in candidates:
            candidates.append(query)

        font_dirs = cls.get_windows_font_dirs()

        for cand in candidates:
            if os.path.isfile(cand):
                return cls.find_font_file(cand, style)

            for fdir in font_dirs:
                direct = os.path.join(fdir, cand)
                if os.path.isfile(direct) and style == "NORMAL":
                    return direct

            clean_target = re.sub(r'[\s_-]+', '', os.path.splitext(cand)[0]).lower()
            for fdir in font_dirs:
                try:
                    files = os.listdir(fdir)
                except OSError:
                    continue
                for fname in files:
                    if not fname.lower().endswith(('.ttf', '.otf', '.ttc')):
                        continue
                    stem = re.sub(r'[\s_-]+', '', os.path.splitext(fname)[0]).lower()
                    for suf in cls.STYLE_SUFFIXES.get(style, [""]):
                        suf_clean = re.sub(r'[\s_-]+', '', suf).lower()
                        if stem == clean_target + suf_clean:
                            return os.path.join(fdir, fname)
                    if style == "NORMAL" and stem.startswith(clean_target) and (
                        "regular" in stem or stem == clean_target
                    ):
                        return os.path.join(fdir, fname)

        return None

    @classmethod
    def resolve_preferred_font(cls, requested_name):
        """Trả về tên font đã giải quyết alias hoặc chọn từ PREFERRED_FONTS nếu để trống."""
        if requested_name:
            norm = requested_name.strip().lower()
            if norm in PalenightConfig.FONT_ALIASES:
                return PalenightConfig.FONT_ALIASES[norm][0]
            return requested_name

        for pref in PalenightConfig.PREFERRED_FONTS:
            if cls.find_font_file(pref, "NORMAL"):
                return pref
        return PalenightConfig.PREFERRED_FONTS[0]
