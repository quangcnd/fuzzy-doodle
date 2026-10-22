"""Module định dạng hiển thị Terminal (màu ANSI, tiêu đề) và quản lý các đường dẫn gốc."""
from __future__ import annotations

import os
import pathlib
import sys


# Bật hiển thị màu ANSI và UTF-8 trên Windows Terminal / CMD
if sys.platform == "win32":
    os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"


def ctext(text: str, color: str) -> str:
    """Tô màu chuỗi văn bản trên Terminal."""
    return f"{color}{text}{Colors.RESET}"


def print_banner() -> None:
    """In tiêu đề chính của chương trình."""
    print(ctext("=" * 78, Colors.CYAN))
    print(ctext("  CÔNG CỤ TỰ ĐỘNG KIỂM TRA & PATCH MINTED / PYGMENTS C++ / LATEX & VS CODE", Colors.BOLD + Colors.CYAN))
    print(ctext("=" * 78, Colors.CYAN))


def print_section(title: str) -> None:
    """In tiêu đề phân mục."""
    print(f"\n{ctext('▶ ' + title, Colors.BOLD + Colors.BLUE)}")
    print(ctext("-" * 78, Colors.BLUE))


def _detect_default_latex_project(root_dir: pathlib.Path) -> pathlib.Path:
    """Tự động dò tìm thư mục Project LaTeX mặc định trên máy hiện tại (không phụ thuộc cứng vào 1 ổ đĩa)."""
    candidates = [
        pathlib.Path.cwd(),
        root_dir.parent,
        pathlib.Path(r"d:\Project\Latex"),
        pathlib.Path(r"c:\Project\Latex"),
        pathlib.Path.home() / "Documents" / "Latex",
    ]
    for cand in candidates:
        try:
            if cand.is_dir() and (any(cand.glob("*.tex")) or (cand / "lib" / "codebox.tex").is_file()):
                return cand.resolve()
        except OSError:
            continue
    return pathlib.Path(r"d:\Project\Latex")


# Các đường dẫn tương đối dựa theo vị trí đặt thư mục bộ công cụ (hoạt động trên mọi máy)
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
PALENIGHT_SRC_DIR = ROOT_DIR / "palenight_source"
TEMPLATES_LIB_DIR = ROOT_DIR / "latex_templates" / "lib"
DEFAULT_LATEX_PROJECT = _detect_default_latex_project(ROOT_DIR)
