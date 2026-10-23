#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""================================================================================
SCRIPT ĐIỀU KHIỂN CHÍNH: KIỂM TRA MÔI TRƯỜNG & PATCH MINTED C++ / LATEX & VS CODE
================================================================================
Tự động kiểm tra và cài đặt các thư viện Python cần thiết ngay khi khởi chạy,
sau đó mở giao diện Textual TUI hoặc Menu CLI để thiết lập môi trường hoàn chỉnh.
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
    if any(arg in sys.argv for arg in ("-h", "--help")):
        return

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

    failed_pkgs: List[str] = []
    for pkg in missing:
        print(f"[Bootstrap] Đang tự động cài đặt `{pkg}`...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", pkg])
        if res.returncode != 0:
            # Thử lại với --break-system-packages phòng trường hợp Linux / PEP 668
            res = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--break-system-packages", pkg])
        if res.returncode == 0:
            print(f"[Bootstrap] ✔ Đã cài đặt xong `{pkg}`.")
        else:
            print(f"[Bootstrap] ✘ Không thể tự cài `{pkg}` (mã lỗi {res.returncode}).")
            failed_pkgs.append(pkg)

    importlib.invalidate_caches()

    if failed_pkgs:
        print(f"\n[Bootstrap] ✘ Lỗi nghiêm trọng: Không thể cài đặt các thư viện: {', '.join(failed_pkgs)}.")
        print("[Bootstrap] Vui lòng chạy lệnh sau bằng tay rồi khởi động lại chương trình:")
        print(f"    {sys.executable} -m pip install {' '.join(failed_pkgs)}")
        sys.exit(1)



from patcher_core import (  # noqa: E402
    Colors,
    ctext,
    print_banner,
    print_section,
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
    parser.add_argument("--verify", action="store_true", help="Kiểm tra toàn diện tính toàn vẹn của Pygments hook, MiKTeX và VS Code")
    parser.add_argument("--all", action="store_true", help="Chạy thẳng: Kiểm tra + Patch cả Minted/Pygments/LaTeX lẫn VS Code")
    parser.add_argument("--minted", action="store_true", help="Chạy thẳng: Kiểm tra + Chỉ patch Minted/Pygments/LaTeX")
    parser.add_argument("--vscode", action="store_true", help="Chạy thẳng: Kiểm tra + Chỉ patch VS Code (LaTeX Workshop & Code Runner)")
    parser.add_argument("--workshop-only", action="store_true", help="Khi dùng với --vscode: chỉ patch LaTeX Workshop")
    parser.add_argument("--coderunner-only", action="store_true", help="Khi dùng với --vscode: chỉ patch Code Runner")
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm tra môi trường và tự cài đặt thư viện Python / MiKTeX còn thiếu")
    parser.add_argument("--workspace", type=str, default=None, help="Đường dẫn thư mục Project LaTeX cần đồng bộ cấu hình")
    parser.add_argument("-y", "--yes", action="store_true", help="Tự động đồng ý tất cả các câu hỏi (Non-interactive mode)")

    args = parser.parse_args()

    if args.workshop_only and args.coderunner_only:
        parser.error("Không thể sử dụng đồng thời cả hai cờ --workshop-only và --coderunner-only!")

    if (args.workshop_only or args.coderunner_only) and not args.vscode and not args.all:
        args.vscode = True

    return args


def main() -> int:
    bootstrap_self_dependencies()
    args = parse_args()

    # 1. Chế độ kiểm tra tính toàn vẹn (--verify)
    if args.verify:
        print_banner()
        env = EnvironmentManager(auto_yes=args.yes)
        minted_patcher = MintedPygmentsPatcher(env, auto_yes=args.yes)
        print_section("KIỂM TRA TÍNH TOÀN VẸN CỦA HỆ THỐNG (--verify)")
        ok, details = minted_patcher.verify_patch()
        for passed, msg in details:
            status = ctext("[✔]", Colors.GREEN) if passed else ctext("[✘]", Colors.RED)
            print(f"  {status} {msg}")
        if ok:
            print(f"\n{ctext('🎉 HỆ THỐNG ĐÃ ĐƯỢC PATCH ĐẦY ĐỦ VÀ SẴN SÀNG!', Colors.BOLD + Colors.GREEN)}")
            return 0
        else:
            print(f"\n{ctext('⚠ PHÁT HIỆN THIẾU HOẶC HỎNG PATCH TRONG HỆ THỐNG.', Colors.BOLD + Colors.RED)}")
            return 1

    # 2. Nếu có truyền cờ chạy thẳng (--check, --all, --minted, --vscode)
    if args.check or args.all or args.minted or args.vscode:
        print_banner()
        env = EnvironmentManager(auto_yes=args.yes)
        minted_patcher = MintedPygmentsPatcher(env, auto_yes=args.yes)
        vscode_patcher = VSCodePatcher(env, auto_yes=args.yes)

        checks_ok = env.run_all_checks(ask_ext_install=not args.check)

        success = True
        if args.check:
            success = checks_ok
        if args.all or args.minted:
            if not minted_patcher.run_patch(target_latex_dir=args.workspace):
                success = False

        if args.all or args.vscode:
            pw: Optional[bool] = None
            pc: Optional[bool] = None
            if args.workshop_only:
                pw, pc = True, False
            elif args.coderunner_only:
                pw, pc = False, True
            elif args.all or args.yes:
                pw, pc = True, True
            if not vscode_patcher.run_patch(patch_workshop=pw, patch_coderunner=pc, target_workspace=args.workspace):
                success = False

        if success:
            print(f"\n{ctext('🎉 HOÀN TẤT QUÁ TRÌNH KIỂM TRA & PATCH HỆ THỐNG!', Colors.BOLD + Colors.GREEN)}")
            return 0
        else:
            print(f"\n{ctext('✘ QUÁ TRÌNH PATCH GẶP LỖI! Vui lòng kiểm tra lại thông báo ở trên.', Colors.BOLD + Colors.RED)}")
            return 1

    # 3. Mặc định: Khởi chạy giao diện Textual TUI
    if not args.cli_menu or args.tui:
        try:
            from patcher_core.tui_app import run_textual_tui
            res = run_textual_tui()
            return res if isinstance(res, int) else 0
        except KeyboardInterrupt:
            print("\nĐã hủy giao diện TUI.")
            return 0
        except Exception as e:
            print(f"[!] Không thể khởi tạo giao diện Textual TUI ({e}), chuyển sang Menu chuẩn...")

    # 4. Dự phòng: Menu văn bản cổ điển nếu truyền --cli-menu hoặc TUI lỗi
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
        print(f"  {ctext('[5]', Colors.GREEN)} {ctext('Kiểm tra tính toàn vẹn hệ thống (--verify)', Colors.BOLD)}")
        print(f"  {ctext('[0]', Colors.RED)} Thoát chương trình")
        print(ctext("============================================================", Colors.CYAN))

        choice = input("\nNhập lựa chọn của bạn [1/2/3/4/5/0]: ").strip()

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
        elif choice == "5":
            ok, details = minted_patcher.verify_patch()
            for passed, msg in details:
                st_str = ctext("[✔]", Colors.GREEN) if passed else ctext("[✘]", Colors.RED)
                print(f"  {st_str} {msg}")
        else:
            print(ctext("Lựa chọn không hợp lệ, vui lòng nhập 1, 2, 3, 4, 5 hoặc 0.", Colors.YELLOW))
            continue

        print(f"\n{ctext('✔ Đã thực hiện xong tác vụ!', Colors.BOLD + Colors.GREEN)}")
        again = input("Bạn có muốn quay lại Menu chính để thực hiện tác vụ khác không? [y/N]: ").strip().lower()
        if again not in ("y", "yes"):
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
