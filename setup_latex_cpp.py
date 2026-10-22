#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT ĐIỀU KHIỂN CHÍNH: KIỂM TRA MÔI TRƯỜNG & PATCH MINTED C++ / LATEX & VS CODE
================================================================================
Tự động kiểm tra và cài đặt các thư viện Python cần thiết ngay khi khởi chạy
(bao gồm cả `textual` cho giao diện TUI), sau đó mở giao diện chọn dạng:
  [ ]
  [ ]
  [v]
di chuyển bằng chuột hoặc phím ↑/↓, chọn bằng Space/Click và chạy bằng Enter.
================================================================================
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from typing import List, Optional, Tuple


# Danh sách thư viện Python cần thiết cho bản thân bộ công cụ (TUI + Patcher)
SELF_REQUIRED_PACKAGES: List[Tuple[str, str]] = [
    # (import_name, pip_package_name)
    ("textual", "textual"),
    ("pygments", "pygments"),
    ("PIL", "pillow"),
    ("latexminted", "latexminted"),
]


def bootstrap_self_dependencies() -> None:
    """Tự động kiểm tra `pip` và cài đặt ngay các thư viện cần thiết cho bản thân
    script (`textual`, `pygments`, `pillow`, `latexminted`) nếu máy mới chưa có.
    """
    missing: List[str] = []
    for mod_name, pip_name in SELF_REQUIRED_PACKAGES:
        if importlib.util.find_spec(mod_name) is None:
            missing.append(pip_name)

    if not missing:
        return

    print(f"[Bootstrap] Phát hiện thiếu thư viện cần thiết cho chương trình: {', '.join(missing)}")
    if importlib.util.find_spec("pip") is None:
        print("[Bootstrap] Đang kích hoạt `pip` qua `ensurepip`...")
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=False)

    for pkg in missing:
        print(f"[Bootstrap] Đang tự động cài đặt `{pkg}`...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", pkg])
        if res.returncode == 0:
            print(f"[Bootstrap] ✔ Đã cài đặt xong `{pkg}`.")
        else:
            print(f"[Bootstrap] ✘ Không thể tự cài `{pkg}` (mã lỗi {res.returncode}).")


# Tự động cài đặt thư viện cần thiết cho bản thân chương trình ngay khi khởi chạy
bootstrap_self_dependencies()

from patcher_core import (  # noqa: E402
    Colors,
    ctext,
    print_banner,
    EnvironmentManager,
    MintedPygmentsPatcher,
    VSCodePatcher,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Công cụ tự động kiểm tra phần mềm thiếu, cài thư viện Python/MiKTeX và patch Minted/Pygments C++ & VS Code.",
    )
    parser.add_argument("--tui", action="store_true", help="Mở giao diện TUI Textual (Mặc định khi chạy không tham số)")
    parser.add_argument("--cli-menu", action="store_true", help="Chạy bằng Menu văn bản cổ điển trên Terminal")
    parser.add_argument("--all", action="store_true", help="Chạy thẳng: Kiểm tra + Patch cả Minted/Pygments/LaTeX lẫn VS Code")
    parser.add_argument("--minted", action="store_true", help="Chạy thẳng: Kiểm tra + Chỉ patch Minted/Pygments/LaTeX")
    parser.add_argument("--vscode", action="store_true", help="Chạy thẳng: Kiểm tra + Chỉ patch VS Code (LaTeX Workshop & Code Runner)")
    parser.add_argument("--workshop-only", action="store_true", help="Khi dùng với --vscode: chỉ patch LaTeX Workshop")
    parser.add_argument("--coderunner-only", action="store_true", help="Khi dùng với --vscode: chỉ patch Code Runner")
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm tra môi trường và tự cài đặt thư viện Python / MiKTeX còn thiếu")
    parser.add_argument("--workspace", type=str, default=None, help="Đường dẫn thư mục Project LaTeX cần đồng bộ cấu hình")
    parser.add_argument("-y", "--yes", action="store_true", help="Tự động đồng ý tất cả các câu hỏi (Non-interactive mode)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # 1. Nếu có truyền cờ chạy thẳng (--check, --all, --minted, --vscode)
    if args.check or args.all or args.minted or args.vscode:
        print_banner()
        env = EnvironmentManager(auto_yes=args.yes)
        minted_patcher = MintedPygmentsPatcher(env, auto_yes=args.yes)
        vscode_patcher = VSCodePatcher(env, auto_yes=args.yes)

        env.run_all_checks(ask_ext_install=not args.check)

        if args.all or args.minted:
            minted_patcher.run_patch(target_latex_dir=args.workspace)

        if args.all or args.vscode:
            pw: Optional[bool] = None
            pc: Optional[bool] = None
            if args.workshop_only:
                pw, pc = True, False
            elif args.coderunner_only:
                pw, pc = False, True
            elif args.all or args.yes:
                pw, pc = True, True
            vscode_patcher.run_patch(patch_workshop=pw, patch_coderunner=pc, target_workspace=args.workspace)

        print(f"\n{ctext('🎉 HOÀN TẤT QUÁ TRÌNH KIỂM TRA & PATCH HỆ THỐNG!', Colors.BOLD + Colors.GREEN)}")
        return 0

    # 2. Mặc định: Khởi chạy giao diện Textual TUI dạng [ ] / [v]
    if not args.cli_menu:
        try:
            from patcher_core.tui_app import run_textual_tui
            return run_textual_tui()
        except Exception as e:
            print(f"[!] Không thể khởi tạo giao diện Textual TUI ({e}), chuyển sang Menu chuẩn...")

    # 3. Dự phòng: Menu văn bản cổ điển nếu truyền --cli-menu
    print_banner()
    env = EnvironmentManager(auto_yes=args.yes)
    minted_patcher = MintedPygmentsPatcher(env, auto_yes=args.yes)
    vscode_patcher = VSCodePatcher(env, auto_yes=args.yes)

    while True:
        print(f"\n{ctext('================ MENU LỰA CHỌN CHẾ ĐỘ PATCH ================', Colors.BOLD + Colors.CYAN)}")
        print(f"  {ctext('[1]', Colors.GREEN)} Patch {ctext('Minted / Pygments / LaTeX', Colors.BOLD)} (Xử lý C++ Semantic, Rainbow Brackets, Indent-Rainbow, MiKTeX)")
        print(f"  {ctext('[2]', Colors.GREEN)} Patch {ctext('VS Code', Colors.BOLD)} (Tuỳ chọn LaTeX Workshop và/hoặc Code Runner C++/LaTeX)")
        print(f"  {ctext('[3]', Colors.GREEN)} Patch {ctext('TẤT CẢ', Colors.BOLD)} (Cả Minted/Pygments/LaTeX lẫn VS Code Workshop/CodeRunner)")
        print(f"  {ctext('[4]', Colors.GREEN)} Chỉ {ctext('Kiểm tra phần mềm thiếu & Tự cài thư viện', Colors.BOLD)} (Python pip & gói MiKTeX)")
        print(f"  {ctext('[0]', Colors.RED)} Thoát chương trình")
        print(ctext("============================================================", Colors.CYAN))

        choice = input("\nNhập lựa chọn của bạn [1/2/3/4/0]: ").strip()

        if choice == "0":
            print(ctext("Đã thoát chương trình.", Colors.CYAN))
            break
        elif choice == "1":
            env.run_all_checks()
            minted_patcher.run_patch()
        elif choice == "2":
            env.run_all_checks()
            vscode_patcher.run_patch()
        elif choice == "3":
            env.run_all_checks()
            minted_patcher.run_patch()
            vscode_patcher.run_patch()
        elif choice == "4":
            env.run_all_checks()
        else:
            print(ctext("Lựa chọn không hợp lệ, vui lòng nhập 1, 2, 3, 4 hoặc 0.", Colors.YELLOW))
            continue

        print(f"\n{ctext('✔ Đã thực hiện xong tác vụ!', Colors.BOLD + Colors.GREEN)}")
        again = input("Bạn có muốn quay lại Menu chính để thực hiện tác vụ khác không? [y/N]: ").strip().lower()
        if again not in ("y", "yes"):
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
