"""Module chuyên xử lý Patch Minted / Pygments C++ / LaTeX (MiKTeX)."""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import zipfile
from typing import List, Optional, Tuple

from pygments.token import Token

from .env_checker import EnvironmentManager
from .ui import (
    Colors,
    ctext,
    print_section,
    PALENIGHT_SRC_DIR,
    TEMPLATES_LIB_DIR,
    DEFAULT_LATEX_PROJECT,
)


CPP_LEXER_HOOK = """

# Kích hoạt C++ Semantic Highlighting & Rainbow Brackets (VS Code Palenight)
try:
    from pygments.styles.palenight import _patch_cpp_lexer
    _patch_cpp_lexer()
except Exception as _palenight_err:
    import os as _os
    if _os.environ.get("PALENIGHT_DEBUG", "").lower() in ("1", "true", "yes"):
        import traceback as _tb, sys as _sys
        print(f"[PALENIGHT_DEBUG] Hook _patch_cpp_lexer failed: {_palenight_err}", file=_sys.stderr)
        _tb.print_exc()
"""


class MintedPygmentsPatcher:
    """Chịu trách nhiệm patch Pygments (C++ Semantic, Rainbow Brackets, Indent-Rainbow),
    đồng bộ an toàn với mọi gốc TEXMF của MiKTeX (`latexminted.py` & `pygments-*.whl`)
    và cập nhật mẫu `lib/codebox.tex`.
    """

    def __init__(self, env: EnvironmentManager, auto_yes: bool = False):
        self.env = env
        self.auto_yes = auto_yes

    def run_patch(self, target_latex_dir: Optional[str] = None, skip_template_sync: bool = False) -> bool:
        print_section("CHẾ ĐỘ PATCH 1: PATCH MINTED / PYGMENTS C++ / LATEX (MIKTEX)")

        if not PALENIGHT_SRC_DIR.is_dir():
            print(f"  {ctext('[✘]', Colors.RED)} Không tìm thấy thư mục nguồn `{PALENIGHT_SRC_DIR}`!")
            return False

        # 1. Tìm thư mục cài đặt pygments trong site-packages
        try:
            import pygments
            pygments_dir = pathlib.Path(pygments.__file__).resolve().parent
            pygments_ver = getattr(pygments, "__version__", "unknown")
        except ImportError:
            print(f"  {ctext('[✘]', Colors.RED)} Chưa thể nạp thư viện `pygments`. Vui lòng kiểm tra lại cài đặt Python.")
            return False

        print(f"  {ctext('[i]', Colors.CYAN)} Thư mục Pygments của Python ({pygments_ver}): {pygments_dir}")

        # 2. Copy palenight.py và palenight_ext/ vào pygments/styles/
        styles_dir = pygments_dir / "styles"
        target_palenight_py = styles_dir / "palenight.py"
        target_ext_dir = styles_dir / "palenight_ext"

        try:
            shutil.copy2(PALENIGHT_SRC_DIR / "palenight.py", target_palenight_py)
            shutil.copytree(
                PALENIGHT_SRC_DIR / "palenight_ext",
                target_ext_dir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            print(f"  {ctext('[✔]', Colors.GREEN)} Đã cài đặt `palenight.py` và bộ module `palenight_ext/` vào `{styles_dir}`.")
        except Exception as e:
            print(f"  {ctext('[✘]', Colors.RED)} Lỗi khi cài đặt palenight vào Pygments: {e}")
            return False

        # 3. Patch hook vào cuối file pygments/lexers/c_cpp.py
        cpp_lexer_file = pygments_dir / "lexers" / "c_cpp.py"
        if cpp_lexer_file.is_file():
            try:
                content = cpp_lexer_file.read_text(encoding="utf-8")
                if "_patch_cpp_lexer" not in content:
                    bak_file = cpp_lexer_file.with_suffix(".py.bak")
                    if not bak_file.exists():
                        shutil.copy2(cpp_lexer_file, bak_file)
                    tmp_cpp = cpp_lexer_file.with_name(f"{cpp_lexer_file.name}.tmp")
                    try:
                        tmp_cpp.write_text(content.rstrip() + "\n" + CPP_LEXER_HOOK, encoding="utf-8")
                        os.replace(tmp_cpp, cpp_lexer_file)
                    finally:
                        if tmp_cpp.exists():
                            try:
                                tmp_cpp.unlink()
                            except OSError:
                                pass
                    print(f"  {ctext('[✔]', Colors.GREEN)} Đã gắn hook C++ Semantic & Rainbow Brackets vào `{cpp_lexer_file}`.")
                else:
                    print(f"  {ctext('[✔]', Colors.GREEN)} File `{cpp_lexer_file.name}` đã có sẵn hook `_patch_cpp_lexer()`.")
            except Exception as e:
                print(f"  {ctext('[✘]', Colors.RED)} Lỗi khi patch `{cpp_lexer_file}`: {e}")
                return False
        else:
            print(f"  {ctext('[✘]', Colors.RED)} Không tìm thấy file `{cpp_lexer_file}`!")
            return False

        # 4. Patch MiKTeX trên tất cả các TEXMF root phát hiện được
        self._patch_miktex_minted(pygments_dir, pygments_ver)

        # 5. Hỏi cập nhật mẫu lib/codebox.tex và xóa cache _minted
        if not skip_template_sync:
            self._offer_latex_template_sync(target_latex_dir)

        return True

    def _patch_miktex_minted(self, pygments_dir: pathlib.Path, py_version: str) -> None:
        miktex_roots = self.env.find_all_miktex_roots()
        if not miktex_roots:
            print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy thư mục gốc MiKTeX, bỏ qua bước đồng bộ `.whl` nội bộ của MiKTeX.")
            return

        found_minted_dirs: List[pathlib.Path] = []
        for root in miktex_roots:
            mdir = root / "scripts" / "minted"
            if mdir.is_dir() and mdir not in found_minted_dirs:
                found_minted_dirs.append(mdir)

        if not found_minted_dirs:
            print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy thư mục `scripts/minted` trong bất kỳ gốc MiKTeX nào.")
            return

        for minted_scripts_dir in found_minted_dirs:
            print(f"  {ctext('[i]', Colors.CYAN)} Đang xử lý thư mục MiKTeX minted: {minted_scripts_dir}")

            # 4a. Patch latexminted.py để ưu tiên site-packages của Python trước file .whl
            latexminted_py = minted_scripts_dir / "latexminted.py"
            if latexminted_py.is_file():
                try:
                    lm_text = latexminted_py.read_text(encoding="utf-8")
                    old_block = (
                        "for wheel_path in wheel_paths:\n"
                        "    sys.path.insert(0, wheel_path.as_posix())"
                    )
                    new_block = (
                        "for wheel_path in wheel_paths:\n"
                        "    if wheel_path.name.startswith('pygments'):\n"
                        "        sys.path.append(wheel_path.as_posix())\n"
                        "    else:\n"
                        "        sys.path.insert(0, wheel_path.as_posix())"
                    )
                    if old_block in lm_text:
                        bak_lm = latexminted_py.with_suffix(".py.bak")
                        if not bak_lm.exists():
                            shutil.copy2(latexminted_py, bak_lm)
                        tmp_lm = latexminted_py.with_name(f"{latexminted_py.name}.tmp")
                        try:
                            tmp_lm.write_text(lm_text.replace(old_block, new_block), encoding="utf-8")
                            os.replace(tmp_lm, latexminted_py)
                        finally:
                            if tmp_lm.exists():
                                try:
                                    tmp_lm.unlink()
                                except OSError:
                                    pass
                        print(f"  {ctext('[✔]', Colors.GREEN)} Đã patch `{latexminted_py}` (ưu tiên nạp `pygments` từ `site-packages`).")
                    elif "wheel_path.name.startswith('pygments')" in lm_text:
                        print(f"  {ctext('[✔]', Colors.GREEN)} File `{latexminted_py.name}` đã có cấu hình ưu tiên `site-packages`.")
                    else:
                        print(f"  {ctext('[i]', Colors.CYAN)} Cấu trúc `{latexminted_py.name}` khác mặc định, tiếp tục đồng bộ an toàn vào `.whl`.")
                except Exception as e:
                    print(f"  {ctext('[!]', Colors.YELLOW)} Không thể chỉnh sửa `{latexminted_py}`: {e}")

            # 4b. Đồng bộ an toàn vào file pygments-*.whl nội bộ của MiKTeX:
            # GIỮ NGUYÊN file c_cpp.py nội bộ của chính whl đó, chỉ chèn hook để tuyệt đối không làm gãy lexer!
            whl_files = list(minted_scripts_dir.glob("pygments-*.whl"))
            for whl_path in whl_files:
                bak_whl = whl_path.with_suffix(".whl.bak")
                if not bak_whl.exists():
                    try:
                        shutil.copy2(whl_path, bak_whl)
                    except Exception as e:
                        print(f"  {ctext('[!]', Colors.YELLOW)} Lỗi khi sao lưu `{whl_path.name}`: {e}")
                        continue

                tmp_whl = whl_path.with_name(f"{whl_path.name}.tmp")
                try:
                    skip_entries = {"pygments/styles/palenight.py"}

                    whl_cpp_content: Optional[str] = None
                    whl_version = "unknown"
                    m_whl_ver = re.search(r"pygments-([0-9.]+)-", whl_path.name)
                    if m_whl_ver:
                        whl_version = m_whl_ver.group(1)

                    with zipfile.ZipFile(whl_path, "r") as zin:
                        if "pygments/lexers/c_cpp.py" in zin.namelist():
                            whl_cpp_content = zin.read("pygments/lexers/c_cpp.py").decode("utf-8", errors="replace")

                    with zipfile.ZipFile(whl_path, "r") as zin, zipfile.ZipFile(tmp_whl, "w", zipfile.ZIP_DEFLATED) as zout:
                        for item in zin.infolist():
                            if item.filename in skip_entries or item.filename.startswith("pygments/styles/palenight_ext/") or item.filename == "pygments/lexers/c_cpp.py":
                                continue
                            zout.writestr(item, zin.read(item.filename))

                        # Ghi palenight.py và palenight_ext
                        zout.write(pygments_dir / "styles" / "palenight.py", "pygments/styles/palenight.py")
                        ext_dir = pygments_dir / "styles" / "palenight_ext"
                        for py_file in ext_dir.glob("*.py"):
                            zout.write(py_file, f"pygments/styles/palenight_ext/{py_file.name}")

                        # Ghi lại c_cpp.py của chính wheel đó kèm hook
                        if whl_cpp_content is not None:
                            if "_patch_cpp_lexer" not in whl_cpp_content:
                                patched_whl_cpp = whl_cpp_content.rstrip() + "\n" + CPP_LEXER_HOOK
                            else:
                                patched_whl_cpp = whl_cpp_content
                            zout.writestr("pygments/lexers/c_cpp.py", patched_whl_cpp.encode("utf-8"))
                        else:
                            zout.write(pygments_dir / "lexers" / "c_cpp.py", "pygments/lexers/c_cpp.py")

                    os.replace(tmp_whl, whl_path)
                    ver_note = f" (whl v{whl_version} so với Python v{py_version})" if whl_version != py_version else ""
                    print(f"  {ctext('[✔]', Colors.GREEN)} Đã đồng bộ `palenight_ext` & hook an toàn vào gói MiKTeX: `{whl_path.name}`{ver_note}.")
                except PermissionError:
                    print(f"  {ctext('[!]', Colors.YELLOW)} Không đủ quyền ghi đè `{whl_path}` (Hãy chạy lại với quyền Administrator nếu cần).")
                except Exception as e:
                    print(f"  {ctext('[!]', Colors.YELLOW)} Lỗi khi cập nhật `{whl_path.name}`: {e}")
                finally:
                    if tmp_whl.exists():
                        try:
                            tmp_whl.unlink()
                        except OSError:
                            pass

    def _offer_latex_template_sync(self, target_latex_dir: Optional[str] = None) -> None:
        if not TEMPLATES_LIB_DIR.is_dir():
            return

        proj_path: Optional[pathlib.Path] = None

        if target_latex_dir:
            cleaned_dir = str(target_latex_dir).strip().strip('"')
            cand = pathlib.Path(cleaned_dir).resolve()
            if cand.is_dir():
                proj_path = cand
            else:
                print(f"  {ctext('[!]', Colors.YELLOW)} Thư mục chỉ định `--workspace` không tồn tại: {target_latex_dir}")
                return
        elif self.auto_yes:
            # Trong chế độ tự động (--yes), nếu không có target_latex_dir thì bỏ qua, tuyệt đối không tự đoán nhầm
            print(f"  {ctext('[i]', Colors.CYAN)} Chế độ --yes: không có tham số `--workspace`, bỏ qua cập nhật mẫu LaTeX vào project.")
            return
        else:
            print(f"\n  {ctext('📄 Đồng bộ mẫu LaTeX (`lib/codebox.tex`) & dọn cache `_minted`:', Colors.BOLD)}")
            ans = input("  Bạn có muốn cập nhật/xuất `lib/codebox.tex` vào thư mục Project LaTeX không? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                hint = f" (Enter = `{DEFAULT_LATEX_PROJECT}`)" if DEFAULT_LATEX_PROJECT else ""
                raw_dir = input(f"  Nhập đường dẫn thư mục Project LaTeX{hint} (hoặc Enter để bỏ qua): ").strip().strip('"')
                if raw_dir:
                    p = pathlib.Path(raw_dir).resolve()
                    if p.is_dir():
                        proj_path = p
                    else:
                        print(f"  {ctext('[!]', Colors.YELLOW)} Thư mục không tồn tại: `{p}`")
                elif DEFAULT_LATEX_PROJECT:
                    proj_path = DEFAULT_LATEX_PROJECT

        if proj_path:
            lib_dir = proj_path / "lib"
            lib_dir.mkdir(parents=True, exist_ok=True)

            src_codebox = TEMPLATES_LIB_DIR / "codebox.tex"
            dst_codebox = lib_dir / "codebox.tex"
            if dst_codebox.is_file():
                if dst_codebox.read_bytes() != src_codebox.read_bytes():
                    bak_codebox = dst_codebox.with_suffix(".tex.bak")
                    if not bak_codebox.exists():
                        shutil.copy2(dst_codebox, bak_codebox)
            shutil.copy2(src_codebox, dst_codebox)
            print(f"  {ctext('[✔]', Colors.GREEN)} Đã cập nhật `{dst_codebox}`.")

            for tpl_file in TEMPLATES_LIB_DIR.glob("*.tex"):
                if tpl_file.name == "codebox.tex":
                    continue
                dst_tpl = lib_dir / tpl_file.name
                if not dst_tpl.exists():
                    shutil.copy2(tpl_file, dst_tpl)
                    print(f"  {ctext('[✔]', Colors.GREEN)} Đã tạo mới file mẫu `{dst_tpl}`.")

            minted_cache = proj_path / "_minted"
            if minted_cache.is_dir():
                shutil.rmtree(minted_cache, ignore_errors=True)
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã dọn sạch thư mục cache cũ `{minted_cache}`.")

    def verify_patch(self) -> Tuple[bool, List[Tuple[bool, str]]]:
        """Kiểm tra toàn diện tính toàn vẹn của Pygments hook, module palenight_ext và MiKTeX."""
        results = []
        all_passed = True

        # 1. Kiểm tra import Pygments & style palenight
        try:
            import pygments
            from pygments.styles import get_style_by_name
            st = get_style_by_name("palenight")
            results.append((True, f"Pygments style 'palenight' nạp thành công ({len(st.styles)} style rules)."))
        except Exception as e:
            all_passed = False
            results.append((False, f"Không thể nạp Pygments style 'palenight': {e}"))

        # 2. Kiểm tra hook CppLexer & Semantic Highlighting
        try:
            from pygments.lexers.c_cpp import CppLexer
            is_patched = getattr(CppLexer, "_palenight_patched", False)
            if not is_patched:
                # Thử kích hoạt
                from pygments.styles.palenight import _patch_cpp_lexer
                _patch_cpp_lexer()
                is_patched = getattr(CppLexer, "_palenight_patched", False)

            if is_patched:
                # Test tokenize mẫu C++
                lexer = CppLexer()
                sample_cpp = "int solve(int a, int b) { return a + b; }"
                tokens = list(lexer.get_tokens(sample_cpp))
                # Phải có token param 'a'
                has_param = any(
                    (str(t[0]).startswith("Token.Name.Variable.Parameter") or t[0] is Token.Name.Variable.Parameter or str(t[0]).startswith("Token.Name.Variable.Magic"))
                    for t in tokens if t[1] == 'a'
                )
                if has_param:
                    results.append((True, "CppLexer hook đang hoạt động và nhận diện đúng Semantic Parameter."))
                else:
                    results.append((True, "CppLexer hook đã được kích hoạt."))
            else:
                all_passed = False
                results.append((False, "CppLexer chưa được kích hoạt hook `_palenight_patched`."))
        except Exception as e:
            all_passed = False
            results.append((False, f"Lỗi khi kiểm tra CppLexer hook: {e}"))

        # 3. Kiểm tra file pygments/lexers/c_cpp.py trên disk
        try:
            import pygments
            pygments_dir = pathlib.Path(pygments.__file__).resolve().parent
            c_cpp_path = pygments_dir / "lexers" / "c_cpp.py"
            if c_cpp_path.is_file() and "_patch_cpp_lexer" in c_cpp_path.read_text(encoding="utf-8"):
                results.append((True, f"File `{c_cpp_path}` chứa hook `_patch_cpp_lexer()`."))
            else:
                all_passed = False
                results.append((False, f"File `{c_cpp_path}` KHÔNG chứa hook `_patch_cpp_lexer()`!"))
        except Exception as e:
            all_passed = False
            results.append((False, f"Không thể đọc file lexer c_cpp.py: {e}"))

        # 4. Kiểm tra MiKTeX scripts/minted
        miktex_roots = self.env.find_all_miktex_roots()
        found_whl = False
        for r in miktex_roots:
            mdir = r / "scripts" / "minted"
            if mdir.is_dir():
                for whl in mdir.glob("pygments-*.whl"):
                    try:
                        with zipfile.ZipFile(whl, "r") as zf:
                            if "pygments/styles/palenight.py" in zf.namelist():
                                found_whl = True
                                results.append((True, f"Gói `{whl.name}` tại `{r}` đã được patch `palenight`."))
                    except Exception:
                        pass
        if not found_whl:
            all_passed = False
            results.append((False, "Chưa tìm thấy gói pygments-*.whl được patch trong MiKTeX (hoặc chưa cài MiKTeX)."))

        return all_passed, results
