"""Giao diện TUI (Terminal User Interface) sử dụng thư viện Textual.
Hỗ trợ danh sách tùy chọn dạng:
  [ ] ...
  [ ] ...
  [v] ...
Điều khiển mượt mà bằng cả Chuột (Click) và Bàn phím (↑/↓, Space để chọn, Enter để chạy).
"""
from __future__ import annotations

import io
import pathlib
import sys
import threading
from typing import Dict, List, Tuple

from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static

from .env_checker import EnvironmentManager
from .minted_patcher import MintedPygmentsPatcher
from .ui import DEFAULT_LATEX_PROJECT
from .vscode_patcher import VSCodePatcher


# Danh sách các mục lựa chọn trong TUI: (id, label, default_checked)
CHECKLIST_ITEMS: List[Tuple[str, str, bool]] = [
    (
        "env_check",
        "Kiểm tra phần mềm thiếu & Tự động cài thư viện Python (pip) + LaTeX (MiKTeX)",
        True,
    ),
    (
        "patch_minted",
        "Patch Minted / Pygments / LaTeX (C++ Semantic, Rainbow Brackets, Indent-Rainbow, MiKTeX)",
        True,
    ),
    (
        "sync_codebox",
        "Cập nhật mẫu lib/codebox.tex vào Project LaTeX & Xóa cache _minted cũ",
        True,
    ),
    (
        "patch_workshop",
        "Patch VS Code: LaTeX Workshop (Đặt xelatex -shell-escape làm mặc định)",
        True,
    ),
    (
        "patch_coderunner",
        "Patch VS Code: Code Runner (Tối ưu nút Run cho C++17 & LaTeX)",
        True,
    ),
    (
        "install_vsc_ext",
        "Tự động cài đặt VS Code Extensions còn thiếu (LaTeX Workshop, Code Runner)",
        False,
    ),
]


class CheckItem(Static):
    """Một dòng tùy chọn hiển thị dạng `[ ]` hoặc `[v]`, hỗ trợ Click chuột và phím."""

    checked: reactive[bool] = reactive(False)
    selected: reactive[bool] = reactive(False)

    class Toggled(Message):
        def __init__(self, item_id: str, checked: bool) -> None:
            super().__init__()
            self.item_id = item_id
            self.checked = checked

    class Clicked(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    def __init__(self, item_id: str, title: str, index: int, checked: bool = False) -> None:
        super().__init__(id=f"chk_{item_id}")
        self.item_id = item_id
        self.title = title
        self.index = index
        self.checked = checked

    def render(self) -> Text:
        mark = "[v]" if self.checked else "[ ]"
        cursor = "❯ " if self.selected else "  "
        t = Text()
        t.append(cursor, style="bold cyan" if self.selected else "")
        t.append(mark, style="bold green" if self.checked else "dim white")
        t.append(f" {self.title}", style="bold yellow" if self.selected else ("white" if self.checked else "dim white"))
        return t

    def watch_checked(self, value: bool) -> None:
        self.refresh()

    def watch_selected(self, value: bool) -> None:
        if value:
            self.add_class("selected-row")
        else:
            self.remove_class("selected-row")
        self.refresh()

    def toggle(self) -> None:
        self.checked = not self.checked
        self.post_message(self.Toggled(self.item_id, self.checked))

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(self.Clicked(self.index))
        self.toggle()


class CheckListBox(Vertical):
    """Khung danh sách chứa các mục `[ ]` / `[v]`, điều hướng bằng ↑/↓/Chuột/Space/Enter."""

    can_focus = True

    BINDINGS = [
        Binding("up,k", "cursor_up", "Lên", show=False),
        Binding("down,j", "cursor_down", "Xuống", show=False),
        Binding("space", "toggle_current", "Chọn / Bỏ chọn [v]", show=True),
        Binding("enter", "submit_run", "Thực thi (Enter)", show=True),
        Binding("a", "toggle_all", "Chọn tất cả", show=True),
    ]

    class RunRequested(Message):
        pass

    def __init__(self) -> None:
        super().__init__(id="checklist-box")
        self.current_index = 0
        self.items: List[CheckItem] = []

    def compose(self) -> ComposeResult:
        for idx, (item_id, label, default_val) in enumerate(CHECKLIST_ITEMS):
            widget = CheckItem(item_id, label, idx, checked=default_val)
            self.items.append(widget)
            yield widget

    def on_mount(self) -> None:
        self._update_selection(0)

    def _update_selection(self, new_index: int) -> None:
        if not self.items:
            return
        self.current_index = max(0, min(new_index, len(self.items) - 1))
        for idx, item in enumerate(self.items):
            item.selected = (idx == self.current_index)

    def action_cursor_up(self) -> None:
        self._update_selection((self.current_index - 1) % len(self.items))

    def action_cursor_down(self) -> None:
        self._update_selection((self.current_index + 1) % len(self.items))

    def action_toggle_current(self) -> None:
        if 0 <= self.current_index < len(self.items):
            self.items[self.current_index].toggle()

    def action_toggle_all(self) -> None:
        any_unchecked = any(not item.checked for item in self.items)
        for item in self.items:
            item.checked = any_unchecked

    def action_submit_run(self) -> None:
        self.post_message(self.RunRequested())

    @on(CheckItem.Clicked)
    def _on_item_clicked(self, msg: CheckItem.Clicked) -> None:
        self._update_selection(msg.index)
        self.focus()

    def get_checked_map(self) -> Dict[str, bool]:
        return {item.item_id: item.checked for item in self.items}


class TuiLogWriter(io.TextIOBase):
    """Chuyển hướng `print()` có màu ANSI vào widget `RichLog` của Textual theo thời gian thực."""

    def __init__(self, app: "LatexCppPatcherApp") -> None:
        super().__init__()
        self.app = app
        self._buffer = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.app.write_ansi_line(line)
        return len(s)

    def flush(self) -> None:
        if self._buffer:
            self.app.write_ansi_line(self._buffer)
            self._buffer = ""


class LatexCppPatcherApp(App):
    """Ứng dụng TUI chính bằng Textual cho bộ công cụ Kiểm tra & Patch LaTeX / C++ / VS Code."""

    TITLE = "Bộ Công Cụ Tự Động Kiểm Tra & Patch Minted C++ / LaTeX (MiKTeX) & VS Code"
    SUB_TITLE = "↑/↓ hoặc Chuột: Di chuyển | Space/Click: Chọn [v] | Enter: Chạy | Q: Thoát"

    CSS = """
    Screen {
        background: #1e2230;
        color: #bfc7d5;
    }

    #top-panel {
        height: auto;
        margin: 1 2 0 2;
        padding: 1 2;
        border: round #82aaff;
        background: #292d3e;
    }

    #section-title {
        color: #ffcb6b;
        text-style: bold;
        margin-bottom: 1;
    }

    #checklist-box {
        height: auto;
        padding: 0 1;
        border: solid #3e4460;
        background: #242839;
    }

    #checklist-box:focus {
        border: double #82aaff;
    }

    CheckItem {
        height: 1;
        padding: 0 1;
    }

    CheckItem.selected-row {
        background: #3a3f58;
    }

    #path-row {
        height: 3;
        margin-top: 1;
        align: left middle;
    }

    #path-label {
        width: auto;
        padding-right: 1;
        padding-top: 1;
        color: #89ddff;
        text-style: bold;
    }

    #workspace-input {
        width: 1fr;
        background: #1e2230;
        border: tall #3e4460;
    }

    #button-row {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    Button {
        margin: 0 2;
        min-width: 24;
    }

    #log-panel {
        height: 1fr;
        margin: 1 2 1 2;
        padding: 0 1;
        border: round #c792ea;
        background: #191c28;
    }
    """

    BINDINGS = [
        Binding("q,escape", "quit", "Thoát (Q)", show=True),
        Binding("r", "run_selected", "Thực thi (Enter/R)", show=True),
        Binding("c", "clear_log", "Xóa Log (C)", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._is_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="top-panel"):
            yield Label(
                "CHỌN CÁC TÁC VỤ MUỐN THỰC HIỆN (Dùng phím ↑/↓ hoặc Chuột, Space để bật/tắt [v], Enter để chạy):",
                id="section-title",
            )
            yield CheckListBox()
            with Horizontal(id="path-row"):
                yield Label("Thư mục Project LaTeX:", id="path-label")
                yield Input(
                    value=str(DEFAULT_LATEX_PROJECT),
                    placeholder="Nhập đường dẫn thư mục Project LaTeX (VD: d:\\Project\\Latex)",
                    id="workspace-input",
                )
            with Horizontal(id="button-row"):
                yield Button("▶ Thực thi các mục [v] (Enter)", id="btn-run", variant="success")
                yield Button("Chọn / Bỏ chọn tất cả (A)", id="btn-all", variant="primary")
                yield Button("Xóa Log (C)", id="btn-clear", variant="default")
                yield Button("Thoát (Q)", id="btn-quit", variant="error")

        yield RichLog(id="log-panel", highlight=False, markup=False, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        checklist = self.query_one(CheckListBox)
        checklist.focus()
        log = self.query_one("#log-panel", RichLog)
        log.write(Text.from_ansi(
            "\033[96m💡 Sẵn sàng! Hãy dùng phím ↑/↓ (hoặc Click chuột) để chọn các mục [v], sau đó bấm Enter để bắt đầu.\033[0m"
        ))

    def write_ansi_line(self, line: str) -> None:
        """Ghi 1 dòng văn bản có mã màu ANSI vào RichLog từ bất kỳ luồng nào."""
        def _append() -> None:
            log = self.query_one("#log-panel", RichLog)
            log.write(Text.from_ansi(line))

        if getattr(self, "_thread_id", None) == threading.get_ident():
            _append()
        else:
            self.call_from_thread(_append)

    @on(CheckListBox.RunRequested)
    def _on_run_requested(self) -> None:
        self.action_run_selected()

    @on(Button.Pressed, "#btn-run")
    def _on_btn_run(self) -> None:
        self.action_run_selected()

    @on(Button.Pressed, "#btn-all")
    def _on_btn_all(self) -> None:
        self.query_one(CheckListBox).action_toggle_all()

    @on(Button.Pressed, "#btn-clear")
    def _on_btn_clear(self) -> None:
        self.action_clear_log()

    @on(Button.Pressed, "#btn-quit")
    def _on_btn_quit(self) -> None:
        self.exit()

    def action_clear_log(self) -> None:
        self.query_one("#log-panel", RichLog).clear()

    def action_run_selected(self) -> None:
        if self._is_running:
            return
        checked = self.query_one(CheckListBox).get_checked_map()
        ws_dir = self.query_one("#workspace-input", Input).value.strip().strip('"')
        self._execute_tasks(checked, ws_dir)

    @work(thread=True)
    def _execute_tasks(self, checked: Dict[str, bool], ws_dir: str) -> None:
        self._is_running = True
        btn_run = self.query_one("#btn-run", Button)
        self.call_from_thread(setattr, btn_run, "disabled", True)

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        writer = TuiLogWriter(self)
        sys.stdout = writer  # type: ignore[assignment]
        sys.stderr = writer  # type: ignore[assignment]

        try:
            if not any(checked.values()):
                print("\033[93m⚠ Bạn chưa đánh dấu [v] vào mục nào! Hãy bấm Space hoặc Click chuột để chọn ít nhất 1 mục.\033[0m")
                return

            env = EnvironmentManager(auto_yes=True)

            # Luôn báo cáo phần mềm thiếu & tự cài thư viện Python / MiKTeX mỗi lần patch
            env.check_and_report_system_software()
            env.ensure_python_libraries()
            env.ensure_miktex_packages()
            env.check_and_offer_vscode_extensions(ask_install=checked.get("install_vsc_ext", False))

            # 1. Patch Minted / Pygments / LaTeX
            if checked.get("patch_minted", False):
                minted_patcher = MintedPygmentsPatcher(env, auto_yes=True)
                target_dir = ws_dir if (checked.get("sync_codebox", False) and ws_dir) else "__SKIP_SYNC__"
                if target_dir == "__SKIP_SYNC__":
                    # Chạy patch Minted nhưng bỏ qua bước copy codebox.tex nếu người dùng bỏ chọn sync_codebox
                    minted_patcher.run_patch(target_latex_dir=None, skip_template_sync=True)
                else:
                    minted_patcher.run_patch(target_latex_dir=ws_dir)
            elif checked.get("sync_codebox", False) and ws_dir:
                minted_patcher = MintedPygmentsPatcher(env, auto_yes=True)
                minted_patcher._offer_latex_template_sync(target_latex_dir=ws_dir)

            # 2. Patch VS Code (LaTeX Workshop & Code Runner)
            pw = checked.get("patch_workshop", False)
            pc = checked.get("patch_coderunner", False)
            if pw or pc:
                vscode_patcher = VSCodePatcher(env, auto_yes=True)
                vscode_patcher.run_patch(
                    patch_workshop=pw,
                    patch_coderunner=pc,
                    target_workspace=ws_dir if ws_dir and pathlib.Path(ws_dir).is_dir() else None,
                )

            print("\n\033[1;92m🎉 ĐÃ THỰC HIỆN XONG TẤT CẢ CÁC MỤC ĐƯỢC CHỌN [v]!\033[0m")
        except Exception as e:
            print(f"\n\033[91m[✘] Có lỗi xảy ra: {e}\033[0m")
        finally:
            writer.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.call_from_thread(setattr, btn_run, "disabled", False)
            self._is_running = False


def run_textual_tui() -> int:
    app = LatexCppPatcherApp()
    app.run()
    return 0
