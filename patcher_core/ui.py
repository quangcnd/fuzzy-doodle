"""Module định dạng hiển thị Terminal (màu ANSI, tiêu đề) và quản lý các đường dẫn gốc."""
from __future__ import annotations

import os
import pathlib
import sys
from typing import Optional


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


def _detect_default_latex_project(root_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Tự động dò tìm thư mục Project LaTeX của người dùng (loại trừ tuyệt đối bản thân repo và thư mục cha)."""
    candidates = [
        pathlib.Path(r"d:\Project\Latex"),
        pathlib.Path(r"c:\Project\Latex"),
        pathlib.Path.home() / "Documents" / "Latex",
        pathlib.Path.cwd(),
    ]
    for cand in candidates:
        try:
            cand_res = cand.resolve()
            # Loại trừ nếu là repo này, thư mục cha của repo, hoặc có setup_latex_cpp.py / .git
            if cand_res == root_dir or root_dir in cand_res.parents or cand_res in root_dir.parents:
                continue
            if (cand_res / "setup_latex_cpp.py").is_file() or (cand_res / ".git").is_dir():
                continue
            if cand_res.is_dir() and (any(cand_res.glob("*.tex")) or (cand_res / "lib" / "codebox.tex").is_file()):
                return cand_res
        except OSError:
            continue
    return None


# Các đường dẫn tương đối dựa theo vị trí đặt thư mục bộ công cụ (hoạt động trên mọi máy)
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
PALENIGHT_SRC_DIR = ROOT_DIR / "palenight_source"
TEMPLATES_LIB_DIR = ROOT_DIR / "latex_templates" / "lib"
DEFAULT_LATEX_PROJECT: Optional[pathlib.Path] = _detect_default_latex_project(ROOT_DIR)
