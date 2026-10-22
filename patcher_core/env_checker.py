"""Module kiểm tra phần mềm hệ thống và tự động cài đặt thư viện Python (pip) & gói LaTeX (MiKTeX)."""
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

from .ui import Colors, ctext, print_section


REQUIRED_PYTHON_PACKAGES: List[Tuple[str, str, str]] = [
    # (import_name, pip_package_name, description)
    ("pygments", "pygments", "Thư viện lõi tô màu cú pháp code (Pygments)"),
    ("PIL", "pillow", "Thư viện xử lý ảnh xuất PNG codeblock (Pillow)"),
    ("latexminted", "latexminted", "Trình thực thi Python mới cho gói LaTeX Minted v3+"),
]

REQUIRED_MIKTEX_PACKAGES: List[Tuple[str, str]] = [
    # (file_to_check_with_kpsewhich, miktex_package_id)
    ("minted.sty", "minted"),
    ("tcolorbox.sty", "tcolorbox"),
    ("fvextra.sty", "fvextra"),
    ("latex2pydata.sty", "latex2pydata"),
    ("pgfopts.sty", "pgfopts"),
    ("upquote.sty", "upquote"),
    ("lineno.sty", "lineno"),
    ("catchfile.sty", "catchfile"),
    ("etoolbox.sty", "etoolbox"),
    ("environ.sty", "environ"),
    ("trimspaces.sty", "trimspaces"),
    ("memoir.cls", "memoir"),
    ("fontspec.sty", "fontspec"),
    ("polyglossia.sty", "polyglossia"),
    ("mlmodern.sty", "mlmodern"),
    ("yhmath.sty", "yhmath"),
    ("xpatch.sty", "xpatch"),
    ("geometry.sty", "geometry"),
    ("framed.sty", "framed"),
    ("float.sty", "float"),
    ("graphicx.sty", "graphics"),
    ("xcolor.sty", "xcolor"),
    ("hyperref.sty", "hyperref"),
    ("amsmath.sty", "amsmath"),
    ("amsfonts.sty", "amsfonts"),
]

VSCODE_EXTENSIONS_INFO: List[Tuple[str, str, bool]] = [
    # (extension_id, display_name, is_core)
    ("james-yu.latex-workshop", "LaTeX Workshop (Biên dịch & xem PDF LaTeX)", True),
    ("formulahendry.code-runner", "Code Runner (Nút Run nhanh cho C++ / LaTeX)", True),
    ("ms-vscode.cpptools", "C/C++ Extension (IntelliSense & Debug C++)", False),
    ("divyanshuagrawal.competitive-programming-helper", "Competitive Programming Helper (CPH)", False),
]


class EnvironmentManager:
    """Quản lý việc dò tìm phần mềm hệ thống, tự cài thư viện Python & gói MiKTeX."""

    def __init__(self, auto_yes: bool = False):
        self.auto_yes = auto_yes
        self.miktex_bin_dir: Optional[pathlib.Path] = self._find_miktex_bin_dir()
        self.miktex_root_dir: Optional[pathlib.Path] = (
            self.miktex_bin_dir.parents[2] if self.miktex_bin_dir and len(self.miktex_bin_dir.parents) >= 3 else None
        )
        self.vscode_cmd: Optional[pathlib.Path] = self._find_vscode_cmd()
        self.perl_exe: Optional[pathlib.Path] = self._find_executable(
            "perl.exe",
            [
                pathlib.Path(r"D:\Apps\Strawberry\perl\bin\perl.exe"),
                pathlib.Path(r"C:\Strawberry\perl\bin\perl.exe"),
            ],
        )
        self.gpp_exe: Optional[pathlib.Path] = self._find_executable(
            "g++.exe",
            [
                pathlib.Path(r"C:\msys64\mingw64\bin\g++.exe"),
                pathlib.Path(r"C:\msys64\ucrt64\bin\g++.exe"),
                pathlib.Path(r"D:\Apps\msys64\mingw64\bin\g++.exe"),
                pathlib.Path(r"C:\MinGW\bin\g++.exe"),
            ],
        )

    @staticmethod
    def _find_executable(exe_name: str, extra_candidates: List[pathlib.Path]) -> Optional[pathlib.Path]:
        found = shutil.which(exe_name)
        if found:
            return pathlib.Path(found).resolve()
        for cand in extra_candidates:
            if cand.is_file():
                return cand.resolve()
        return None

    @classmethod
    def _find_miktex_bin_dir(cls) -> Optional[pathlib.Path]:
        for cmd in ("xelatex.exe", "pdflatex.exe", "miktex.exe", "initexmf.exe"):
            found = shutil.which(cmd)
            if found and "miktex" in found.lower():
                return pathlib.Path(found).resolve().parent

        local_app = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        candidates = [
            pathlib.Path(r"D:\Apps\MikTex\miktex\bin\x64"),
            pathlib.Path(r"C:\Apps\MikTex\miktex\bin\x64"),
            pathlib.Path(prog_files) / "MiKTeX" / "miktex" / "bin" / "x64",
            pathlib.Path(prog_x86) / "MiKTeX" / "miktex" / "bin" / "x64",
        ]
        if local_app:
            candidates.append(pathlib.Path(local_app) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64")

        for cand in candidates:
            if (cand / "xelatex.exe").is_file():
                return cand.resolve()
        return None

    @classmethod
    def _find_vscode_cmd(cls) -> Optional[pathlib.Path]:
        for name in ("code.cmd", "code"):
            found = shutil.which(name)
            if found:
                return pathlib.Path(found).resolve()

        local_app = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidates = [
            pathlib.Path(r"D:\Apps\Microsoft VS Code\bin\code.cmd"),
            pathlib.Path(prog_files) / "Microsoft VS Code" / "bin" / "code.cmd",
        ]
        if local_app:
            candidates.append(pathlib.Path(local_app) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd")

        for cand in candidates:
            if cand.is_file():
                return cand.resolve()
        return None

    def get_miktex_tool(self, tool_name: str) -> Optional[pathlib.Path]:
        exe_name = f"{tool_name}.exe" if (sys.platform == "win32" and not tool_name.endswith(".exe")) else tool_name
        if self.miktex_bin_dir and (self.miktex_bin_dir / exe_name).is_file():
            return self.miktex_bin_dir / exe_name
        found = shutil.which(exe_name)
        return pathlib.Path(found).resolve() if found else None

    def check_and_report_system_software(self) -> List[Tuple[str, str, str]]:
        """Kiểm tra các phần mềm hệ thống và trả về danh sách các phần mềm còn thiếu."""
        print_section("BƯỚC 1: KIỂM TRA PHẦN MỀM HỆ THỐNG CẦN THIẾT")
        missing_software: List[Tuple[str, str, str]] = []

        # 1. Python
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"  {ctext('[✔]', Colors.GREEN)} Python {py_ver:<10} : {sys.executable}")

        # 2. MiKTeX (xelatex, pdflatex, latexmk)
        if self.miktex_bin_dir:
            xelatex = self.get_miktex_tool("xelatex")
            latexmk = self.get_miktex_tool("latexmk")
            print(f"  {ctext('[✔]', Colors.GREEN)} MiKTeX (xelatex)  : {xelatex}")
            if latexmk:
                print(f"  {ctext('[✔]', Colors.GREEN)} MiKTeX (latexmk)  : {latexmk}")
            else:
                print(f"  {ctext('[!]', Colors.YELLOW)} MiKTeX (latexmk)  : Chưa có lệnh latexmk")
        else:
            print(f"  {ctext('[✘]', Colors.RED)} MiKTeX            : {ctext('CHƯA CÀI ĐẶT (Bắt buộc cho LaTeX)', Colors.RED)}")
            missing_software.append((
                "MiKTeX (Bộ biên dịch LaTeX)",
                "https://miktex.org/download",
                "Tải bản cài đặt 64-bit và chọn 'Install missing packages on-the-fly = Yes'",
            ))

        # 3. Strawberry Perl
        if self.perl_exe:
            print(f"  {ctext('[✔]', Colors.GREEN)} Strawberry Perl   : {self.perl_exe}")
        else:
            print(f"  {ctext('[✘]', Colors.YELLOW)} Strawberry Perl   : {ctext('CHƯA CÀI ĐẶT (Cần nếu chạy recipe latexmk)', Colors.YELLOW)}")
            missing_software.append((
                "Strawberry Perl (Hỗ trợ công cụ latexmk)",
                "https://strawberryperl.com/",
                "Cài đặt bản 64-bit để sử dụng công cụ tự động hóa latexmk",
            ))

        # 4. VS Code
        if self.vscode_cmd:
            print(f"  {ctext('[✔]', Colors.GREEN)} Visual Studio Code: {self.vscode_cmd}")
        else:
            print(f"  {ctext('[✘]', Colors.YELLOW)} Visual Studio Code: {ctext('CHƯA TÌM THẤY TRÊN MÁY', Colors.YELLOW)}")
            missing_software.append((
                "Visual Studio Code",
                "https://code.visualstudio.com/",
                "Khi cài nhớ tích chọn 'Add to PATH'",
            ))

        # 5. Trình biên dịch C++ (g++)
        if self.gpp_exe:
            print(f"  {ctext('[✔]', Colors.GREEN)} C++ Compiler (g++): {self.gpp_exe}")
        else:
            print(f"  {ctext('[✘]', Colors.YELLOW)} C++ Compiler (g++): {ctext('CHƯA TÌM THẤY TRONG PATH (Cần để biên dịch C++)', Colors.YELLOW)}")
            missing_software.append((
                "MinGW-w64 / MSYS2 G++ (Trình biên dịch C++)",
                "https://www.msys2.org/",
                "Cài MSYS2 rồi chạy `pacman -S mingw-w64-x86_64-gcc` và thêm `C:\\msys64\\mingw64\\bin` vào PATH",
            ))

        # 6. Kiểm tra Font chữ Code
        self._check_code_fonts()

        if missing_software:
            print(f"\n  {ctext('⚠ TỔNG HỢP PHẦN MỀM HỆ THỐNG CÒN THIẾU CẦN CÀI THÊM:', Colors.BOLD + Colors.YELLOW)}")
            for idx, (name, url, note) in enumerate(missing_software, 1):
                print(f"    {idx}. {ctext(name, Colors.BOLD)}")
                print(f"       - Link tải : {ctext(url, Colors.CYAN)}")
                print(f"       - Ghi chú  : {note}")
        else:
            print(f"\n  {ctext('✨ Tất cả các phần mềm nền tảng (Python, MiKTeX, Perl, VS Code, G++) đã đầy đủ!', Colors.GREEN)}")

        return missing_software

    def _check_code_fonts(self) -> None:
        font_dirs = []
        win_dir = os.environ.get("WINDIR", r"C:\Windows")
        if os.path.isdir(os.path.join(win_dir, "Fonts")):
            font_dirs.append(os.path.join(win_dir, "Fonts"))
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app and os.path.isdir(os.path.join(local_app, "Microsoft", "Windows", "Fonts")):
            font_dirs.append(os.path.join(local_app, "Microsoft", "Windows", "Fonts"))

        all_font_files = []
        for d in font_dirs:
            try:
                all_font_files.extend(f.lower() for f in os.listdir(d))
            except OSError:
                pass

        font_checks = [
            ("Consolas (Mặc định)", ["consola.ttf"]),
            ("JetBrains Mono", ["jetbrainsmono"]),
            ("Cascadia Code", ["cascadiacode", "cascadiamono"]),
            ("Fira Code / FiraMono", ["firacode", "firamono"]),
        ]
        found_fonts = []
        missing_fonts = []
        for label, patterns in font_checks:
            if any(any(pat in fname for pat in patterns) for fname in all_font_files):
                found_fonts.append(label)
            else:
                missing_fonts.append(label)

        print(f"  {ctext('[✔]', Colors.GREEN)} Font Code đã có   : {', '.join(found_fonts) if found_fonts else 'Không rõ'}")
        if missing_fonts:
            print(f"  {ctext('[i]', Colors.CYAN)} Font gợi ý cài thêm: {', '.join(missing_fonts)} (tùy chọn)")

    def ensure_python_libraries(self) -> bool:
        """Tự động kiểm tra và cài đặt các thư viện Python còn thiếu bằng pip."""
        print_section("BƯỚC 2: KIỂM TRA & TỰ ĐỘNG CÀI ĐẶT THƯ VIỆN PYTHON")
        all_ok = True
        for import_name, pip_name, desc in REQUIRED_PYTHON_PACKAGES:
            spec = importlib.util.find_spec(import_name)
            if spec is not None:
                print(f"  {ctext('[✔]', Colors.GREEN)} Thư viện `{pip_name:<12}` : Đã cài đặt ({desc})")
            else:
                print(f"  {ctext('[!]', Colors.YELLOW)} Phát hiện thiếu thư viện Python `{pip_name}` ({desc}) -> Đang tự động cài đặt...")
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", pip_name]
                res = subprocess.run(cmd)
                if res.returncode == 0:
                    print(f"  {ctext('[✔]', Colors.GREEN)} Đã tự động cài đặt thành công `{pip_name}`!")
                else:
                    print(f"  {ctext('[✘]', Colors.RED)} Lỗi khi cài đặt `{pip_name}` qua pip (mã lỗi {res.returncode}).")
                    all_ok = False
        return all_ok

    def ensure_miktex_packages(self) -> bool:
        """Tự động bật AutoInstall=1 và cài các gói LaTeX còn thiếu trên MiKTeX."""
        print_section("BƯỚC 3: KIỂM TRA & TỰ ĐỘNG CÀI ĐẶT GÓI LATEX (MIKTEX)")
        if not self.miktex_bin_dir:
            print(f"  {ctext('[!]', Colors.YELLOW)} Bỏ qua bước kiểm tra gói LaTeX vì chưa tìm thấy MiKTeX trên máy.")
            return False

        initexmf = self.get_miktex_tool("initexmf")
        kpsewhich = self.get_miktex_tool("kpsewhich")
        miktex_cli = self.get_miktex_tool("miktex")
        mpm_cli = self.get_miktex_tool("mpm")

        if initexmf:
            try:
                subprocess.run(
                    [str(initexmf), "--set-config-value=[MPM]AutoInstall=1"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã kích hoạt chế độ MiKTeX `AutoInstall=1` (Tự động tải gói thiếu khi compile).")
            except Exception as e:
                print(f"  {ctext('[!]', Colors.YELLOW)} Không thể đặt AutoInstall=1: {e}")

        if not kpsewhich:
            print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy công cụ `kpsewhich` để kiểm tra từng gói.")
            return True

        files_to_check = [item[0] for item in REQUIRED_MIKTEX_PACKAGES]
        try:
            proc = subprocess.run(
                [str(kpsewhich)] + files_to_check,
                capture_output=True,
                text=True,
                timeout=30,
            )
            found_lines = [line.strip().lower() for line in proc.stdout.splitlines() if line.strip()]
        except Exception:
            found_lines = []

        missing_pkgs: List[Tuple[str, str]] = []
        for sty_file, pkg_id in REQUIRED_MIKTEX_PACKAGES:
            is_found = any(line.endswith("/" + sty_file.lower()) or line.endswith("\\" + sty_file.lower()) for line in found_lines)
            if not is_found:
                missing_pkgs.append((sty_file, pkg_id))

        if not missing_pkgs:
            print(f"  {ctext('[✔]', Colors.GREEN)} Tất cả {len(REQUIRED_MIKTEX_PACKAGES)} gói LaTeX cần thiết (minted, tcolorbox, fvextra, memoir, fontspec...) đều đã có sẵn!")
            return True

        print(f"  {ctext('[!]', Colors.YELLOW)} Phát hiện thiếu {len(missing_pkgs)} gói LaTeX: {', '.join(p[1] for p in missing_pkgs)}")
        installed_any = False
        seen_pkg_ids = set()

        for sty_file, pkg_id in missing_pkgs:
            if pkg_id in seen_pkg_ids:
                continue
            seen_pkg_ids.add(pkg_id)
            print(f"  -> Đang tự động cài gói MiKTeX `{ctext(pkg_id, Colors.BOLD)}` (cho `{sty_file}`)...")

            install_cmd = None
            if miktex_cli:
                install_cmd = [str(miktex_cli), "packages", "install", pkg_id]
            elif mpm_cli:
                install_cmd = [str(mpm_cli), f"--install={pkg_id}"]

            if not install_cmd:
                print(f"     {ctext('[!]', Colors.YELLOW)} Không tìm thấy `miktex.exe` hoặc `mpm.exe`, gói `{pkg_id}` sẽ được MiKTeX tự tải ở lần compile đầu tiên.")
                continue

            res = subprocess.run(install_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"     {ctext('[✔]', Colors.GREEN)} Đã cài đặt thành công gói LaTeX `{pkg_id}`!")
                installed_any = True
            else:
                err_msg = (res.stderr or res.stdout or "").strip()
                if "already installed" in err_msg.lower():
                    print(f"     {ctext('[✔]', Colors.GREEN)} Gói `{pkg_id}` đã được cài đặt sẵn.")
                else:
                    print(f"     {ctext('[!]', Colors.YELLOW)} Chưa thể cài ngay `{pkg_id}` ({err_msg.splitlines()[0] if err_msg else 'lỗi mạng/quyền'}). MiKTeX sẽ tự tải khi compile.")

        if installed_any and initexmf:
            subprocess.run([str(initexmf), "--update-fndb"], capture_output=True)
            print(f"  {ctext('[✔]', Colors.GREEN)} Đã cập nhật cơ sở dữ liệu file MiKTeX (FNDB).")

        return True

    def check_and_offer_vscode_extensions(self, ask_install: bool = True) -> List[str]:
        """Kiểm tra các Extension VS Code đã cài đặt và hỏi người dùng có muốn tự cài nếu thiếu."""
        print_section("BƯỚC 4: KIỂM TRA VS CODE EXTENSIONS")
        ext_dir = pathlib.Path.home() / ".vscode" / "extensions"
        installed_folders: List[str] = []
        if ext_dir.is_dir():
            try:
                installed_folders = [d.name.lower() for d in ext_dir.iterdir() if d.is_dir()]
            except OSError:
                pass

        missing_exts: List[Tuple[str, str, bool]] = []
        for ext_id, desc, is_core in VSCODE_EXTENSIONS_INFO:
            prefix = ext_id.lower() + "-"
            is_installed = any(folder.startswith(prefix) or folder == ext_id.lower() for folder in installed_folders)
            if is_installed:
                print(f"  {ctext('[✔]', Colors.GREEN)} Extension `{ext_id:<50}` : Đã cài đặt")
            else:
                tag = "BẮT BUỘC" if is_core else "KHUYÊN DÙNG"
                color = Colors.YELLOW if is_core else Colors.CYAN
                print(f"  {ctext('[!]', color)} Extension `{ext_id:<50}` : {ctext(f'CHƯA CÀI ({tag}) - {desc}', color)}")
                missing_exts.append((ext_id, desc, is_core))

        if missing_exts and ask_install and self.vscode_cmd:
            print(f"\n  {ctext('💡 Phát hiện thiếu VS Code Extension:', Colors.YELLOW)} {', '.join(e[0] for e in missing_exts)}")
            do_install = self.auto_yes
            if not self.auto_yes:
                ans = input("  Bạn có muốn tự động cài đặt các Extension còn thiếu qua lệnh `code --install-extension` không? [Y/n]: ").strip().lower()
                do_install = ans in ("", "y", "yes")

            if do_install:
                for ext_id, _, _ in missing_exts:
                    print(f"  -> Đang cài đặt `{ext_id}`...")
                    res = subprocess.run([str(self.vscode_cmd), "--install-extension", ext_id])
                    if res.returncode == 0:
                        print(f"     {ctext('[✔]', Colors.GREEN)} Đã cài đặt `{ext_id}`!")
                    else:
                        print(f"     {ctext('[✘]', Colors.RED)} Không thể tự cài `{ext_id}`, vui lòng mở VS Code (Ctrl+Shift+X) và tìm `{ext_id}`.")

        return [e[0] for e in missing_exts]

    def run_all_checks(self, ask_ext_install: bool = True) -> None:
        """Chạy trọn bộ 4 bước kiểm tra & tự động cài đặt."""
        self.check_and_report_system_software()
        self.ensure_python_libraries()
        self.ensure_miktex_packages()
        self.check_and_offer_vscode_extensions(ask_install=ask_ext_install)
