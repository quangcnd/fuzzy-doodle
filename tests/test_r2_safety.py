"""Regression tests for Round 2 Safety of System Modifications defects (DEFECT-R2-01 through DEFECT-R2-10)."""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import zipfile
from unittest.mock import MagicMock, patch

import pytest

import palenight_source.palenight_ext as _ext
import palenight_source.palenight_ext.patchers as _ext_patchers
import palenight_source.palenight_ext.cpp_analyzer as _ext_cpp_analyzer
import palenight_source.palenight_ext.config as _ext_config
import palenight_source.palenight_ext.fonts as _ext_fonts
import palenight_source.palenight_ext.indent_rainbow as _ext_ir

# Route pygments.styles.palenight_ext to workspace implementation without touching system site-packages
sys.modules.setdefault("pygments.styles.palenight_ext", _ext)
sys.modules.setdefault("pygments.styles.palenight_ext.patchers", _ext_patchers)
sys.modules.setdefault("pygments.styles.palenight_ext.cpp_analyzer", _ext_cpp_analyzer)
sys.modules.setdefault("pygments.styles.palenight_ext.config", _ext_config)
sys.modules.setdefault("pygments.styles.palenight_ext.fonts", _ext_fonts)
sys.modules.setdefault("pygments.styles.palenight_ext.indent_rainbow", _ext_ir)

from patcher_core.env_checker import EnvironmentManager
from patcher_core.minted_patcher import MintedPygmentsPatcher
from patcher_core.vscode_patcher import VSCodePatcher, CODE_RUNNER_EXECUTORS
from patcher_core.ui import TEMPLATES_LIB_DIR, PALENIGHT_SRC_DIR


# ==============================================================================
# DEFECT-R2-01: Non-atomic write to settings.json
# ==============================================================================
def test_defect_r2_01_vscode_settings_atomic_write(tmp_path, monkeypatch):
    """DEFECT-R2-01: VSCode settings writing must be atomic via .tmp and os.replace."""
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"
    initial_content = '{\n    "editor.fontSize": 14\n}\n'
    settings_file.write_text(initial_content, encoding="utf-8")

    # Case A: Normal success - atomic replace succeeds, no .tmp file left behind
    res = VSCodePatcher._patch_settings_file(settings_file, patch_workshop=True, patch_coderunner=True)
    assert res is True
    assert settings_file.is_file()
    tmp_file = settings_dir / "settings.json.tmp"
    assert not tmp_file.exists(), ".tmp file must be cleaned up on success"
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "latex-workshop.latex.recipe.default" in data

    # Case B: Failure during replacement - original file MUST NOT be truncated to 0 bytes
    # and .tmp file must be removed in finally block
    def failing_replace(src, dst):
        raise OSError("Simulated atomic replace failure (e.g. disk full or lock)")

    monkeypatch.setattr(os, "replace", failing_replace)
    failing_settings = settings_dir / "fail_settings.json"
    failing_settings.write_text('{\n    "editor.tabSize": 2\n}\n', encoding="utf-8")

    res_fail = VSCodePatcher._patch_settings_file(failing_settings, patch_workshop=True, patch_coderunner=True)
    assert res_fail is False, "_patch_settings_file must return False on exception"
    # Verify original file content is intact, not 0 bytes or corrupted
    assert failing_settings.read_text(encoding="utf-8") == '{\n    "editor.tabSize": 2\n}\n'
    fail_tmp = settings_dir / "fail_settings.json.tmp"
    assert not fail_tmp.exists(), ".tmp file must be deleted in finally block upon failure"


# ==============================================================================
# DEFECT-R2-02: Non-atomic writes to Pygments c_cpp.py and MiKTeX latexminted.py
# ==============================================================================
def test_defect_r2_02_minted_patcher_atomic_writes(tmp_path, monkeypatch):
    """DEFECT-R2-02: Writes to c_cpp.py and latexminted.py must be atomic with .tmp cleanup."""
    env = EnvironmentManager(auto_yes=True)
    patcher = MintedPygmentsPatcher(env, auto_yes=True)

    # Part 1: c_cpp.py atomic write
    fake_pyg = tmp_path / "pygments"
    lexers_dir = fake_pyg / "lexers"
    lexers_dir.mkdir(parents=True)
    cpp_file = lexers_dir / "c_cpp.py"
    cpp_content = "# initial c_cpp content\nclass CppLexer:\n    pass\n"
    cpp_file.write_text(cpp_content, encoding="utf-8")

    # Verify atomic write under failure:
    def failing_replace(src, dst):
        raise OSError("Simulated replace error")

    monkeypatch.setattr(os, "replace", failing_replace)
    fake_pygments_mod = MagicMock()
    fake_pygments_mod.__file__ = str(fake_pyg / "__init__.py")
    fake_pygments_mod.__version__ = "2.15.0"
    monkeypatch.setitem(sys.modules, "pygments", fake_pygments_mod)

    # run_patch should catch the exception and return False
    res = patcher.run_patch(skip_template_sync=True)
    assert res is False
    # Original file must NOT be truncated
    assert cpp_file.read_text(encoding="utf-8") == cpp_content
    # Temporary file must be removed
    assert not (lexers_dir / "c_cpp.py.tmp").exists()

    # Part 2: latexminted.py atomic write
    fake_miktex = tmp_path / "miktex"
    minted_scripts = fake_miktex / "scripts" / "minted"
    minted_scripts.mkdir(parents=True)
    lm_file = minted_scripts / "latexminted.py"
    old_lm = (
        "for wheel_path in wheel_paths:\n"
        "    sys.path.insert(0, wheel_path.as_posix())"
    )
    lm_file.write_text(old_lm, encoding="utf-8")
    monkeypatch.setattr(env, "find_all_miktex_roots", lambda: [fake_miktex])

    # Case A: Failure during latexminted.py atomic replace
    monkeypatch.setattr(os, "replace", failing_replace)
    patcher._patch_miktex_minted(fake_pyg, "2.15.0")
    # Original file must NOT be truncated
    assert lm_file.read_text(encoding="utf-8") == old_lm
    # Temporary file must be removed by finally
    assert not (minted_scripts / "latexminted.py.tmp").exists()

    # Case B: Success with normal os.replace
    monkeypatch.undo()
    monkeypatch.setattr(env, "find_all_miktex_roots", lambda: [fake_miktex])
    patcher._patch_miktex_minted(fake_pyg, "2.15.0")

    updated_lm = lm_file.read_text(encoding="utf-8")
    assert "wheel_path.name.startswith('pygments')" in updated_lm
    assert not (minted_scripts / "latexminted.py.tmp").exists()


# ==============================================================================
# DEFECT-R2-03: Unquoted $dir in Code Runner executor commands
# ==============================================================================
def test_defect_r2_03_code_runner_executors_quoted_dir(tmp_path):
    """DEFECT-R2-03: $dir must be quoted as \"$dir\" in CODE_RUNNER_EXECUTORS."""
    cpp_exec = CODE_RUNNER_EXECUTORS["cpp"]
    latex_exec = CODE_RUNNER_EXECUTORS["latex"]

    # Must start with cd "$dir" &&
    assert cpp_exec.startswith('cd "$dir" &&'), f"C++ executor map must quote $dir, got: {cpp_exec}"
    assert latex_exec.startswith('cd "$dir" &&'), f"LaTeX executor map must quote $dir, got: {latex_exec}"

    # Must not contain unquoted 'cd $dir &&'
    assert 'cd $dir &&' not in cpp_exec
    assert 'cd $dir &&' not in latex_exec

    # Test upgrading an existing configuration that has the old unquoted command
    settings_dir = tmp_path / "vscode"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"
    old_unquoted_cpp = 'cd $dir && g++ -std=c++17 -O2 -Wl,--stack=67108864 "$fileName" -o "$fileNameWithoutExt" && "$dir$fileNameWithoutExt"'
    settings_file.write_text(
        json.dumps({
            "code-runner.executorMap": {
                "cpp": old_unquoted_cpp,
            }
        }, indent=4),
        encoding="utf-8",
    )

    VSCodePatcher._patch_settings_file(settings_file, patch_workshop=False, patch_coderunner=True)
    updated_data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert updated_data["code-runner.executorMap"]["cpp"] == CODE_RUNNER_EXECUTORS["cpp"]
    assert updated_data["code-runner.executorMap"]["cpp"].startswith('cd "$dir" &&')


# ==============================================================================
# DEFECT-R2-04: Abandoned .whl.tmp file in MiKTeX directory upon exception
# ==============================================================================
def test_defect_r2_04_abandoned_tmp_whl_cleaned_up_on_exception(tmp_path, monkeypatch):
    """DEFECT-R2-04: .whl.tmp file must be cleaned up in finally block upon any exception."""
    env = EnvironmentManager(auto_yes=True)
    patcher = MintedPygmentsPatcher(env, auto_yes=True)

    fake_miktex = tmp_path / "miktex"
    minted_scripts = fake_miktex / "scripts" / "minted"
    minted_scripts.mkdir(parents=True)
    whl_file = minted_scripts / "pygments-2.15.0-py3-none-any.whl"

    # Create a minimal valid wheel (zip)
    with zipfile.ZipFile(whl_file, "w") as zf:
        zf.writestr("pygments/lexers/c_cpp.py", "# dummy c_cpp\n")

    monkeypatch.setattr(env, "find_all_miktex_roots", lambda: [fake_miktex])

    # Intercept writestr on .whl.tmp to simulate write error
    original_writestr = zipfile.ZipFile.writestr

    def mock_writestr(self, zinfo_or_arcname, *args, **kwargs):
        if getattr(self, "filename", None) and str(self.filename).endswith(".whl.tmp"):
            raise RuntimeError("Simulated error writing to tmp_whl")
        return original_writestr(self, zinfo_or_arcname, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "writestr", mock_writestr)

    fake_pyg = tmp_path / "fake_pyg"
    fake_pyg.mkdir()
    (fake_pyg / "styles").mkdir()
    (fake_pyg / "styles" / "palenight.py").write_text("# style\n", encoding="utf-8")
    (fake_pyg / "styles" / "palenight_ext").mkdir()

    patcher._patch_miktex_minted(fake_pyg, "2.15.0")

    # Verify no .whl.tmp file is left behind in the directory
    tmp_whl = minted_scripts / "pygments-2.15.0-py3-none-any.whl.tmp"
    assert not tmp_whl.exists(), f"Temporary wheel file {tmp_whl} must be removed by finally block"
    # Original wheel must still exist
    assert whl_file.is_file(), "Original wheel must remain intact"


# ==============================================================================
# DEFECT-R2-05: Unhandled UnicodeDecodeError when reading existing codebox.tex
# ==============================================================================
def test_defect_r2_05_offer_latex_template_sync_non_utf8_binary_safe(tmp_path):
    """DEFECT-R2-05: _offer_latex_template_sync must handle non-UTF-8 existing codebox.tex without UnicodeDecodeError."""
    env = EnvironmentManager(auto_yes=True)
    patcher = MintedPygmentsPatcher(env, auto_yes=True)

    ws_dir = tmp_path / "my_project"
    lib_dir = ws_dir / "lib"
    lib_dir.mkdir(parents=True)
    dst_codebox = lib_dir / "codebox.tex"

    # Write invalid UTF-8 bytes to existing codebox.tex
    invalid_utf8_bytes = b"\\documentclass{article}\n% Non-utf8: \xe0\xe1\xe2 \xff\xfe\n"
    dst_codebox.write_bytes(invalid_utf8_bytes)

    # In pre-fix code, dst_codebox.read_text(encoding="utf-8") crashed with UnicodeDecodeError.
    # In post-fix code, dst_codebox.read_bytes() is used.
    patcher._offer_latex_template_sync(target_latex_dir=str(ws_dir))

    # Must complete cleanly without exception
    assert dst_codebox.is_file()
    # Backup must preserve the original non-UTF-8 bytes
    bak_codebox = dst_codebox.with_suffix(".tex.bak")
    assert bak_codebox.is_file()
    assert bak_codebox.read_bytes() == invalid_utf8_bytes


# ==============================================================================
# DEFECT-R2-06: codebox.tex backup unconditionally overwriting previous .bak
# ==============================================================================
def test_defect_r2_06_codebox_backup_does_not_overwrite_pristine_bak(tmp_path):
    """DEFECT-R2-06: codebox.tex backup must not overwrite existing pristine .bak file."""
    env = EnvironmentManager(auto_yes=True)
    patcher = MintedPygmentsPatcher(env, auto_yes=True)

    ws_dir = tmp_path / "latex_proj"
    lib_dir = ws_dir / "lib"
    lib_dir.mkdir(parents=True)
    dst_codebox = lib_dir / "codebox.tex"

    # Initial pristine content v1
    v1_content = b"% Pristine Original v1\n\\newcommand{\\test}{1}\n"
    dst_codebox.write_bytes(v1_content)

    # Run 1: creates codebox.tex.bak with v1_content
    patcher._offer_latex_template_sync(target_latex_dir=str(ws_dir))
    bak_codebox = dst_codebox.with_suffix(".tex.bak")
    assert bak_codebox.is_file()
    assert bak_codebox.read_bytes() == v1_content

    # Simulate user modifying codebox.tex to v2
    v2_content = b"% User Modified v2\n\\newcommand{\\test}{2}\n"
    dst_codebox.write_bytes(v2_content)

    # Run 2: in pre-fix code, .bak was unconditionally overwritten with v2_content
    patcher._offer_latex_template_sync(target_latex_dir=str(ws_dir))

    # In post-fix code: .bak must STILL contain pristine v1_content
    assert bak_codebox.read_bytes() == v1_content, "codebox.tex.bak must preserve pristine original v1"


# ==============================================================================
# DEFECT-R2-07: Destructive shutil.rmtree on palenight_ext before copytree
# ==============================================================================
def test_defect_r2_07_palenight_ext_non_destructive_copytree(tmp_path, monkeypatch):
    """DEFECT-R2-07: copytree uses dirs_exist_ok=True and must not rmtree target_ext_dir beforehand."""
    env = EnvironmentManager(auto_yes=True)
    patcher = MintedPygmentsPatcher(env, auto_yes=True)

    fake_pyg = tmp_path / "pygments"
    styles_dir = fake_pyg / "styles"
    ext_dir = styles_dir / "palenight_ext"
    ext_dir.mkdir(parents=True)
    sentinel_file = ext_dir / "user_custom_marker.txt"
    sentinel_file.write_text("pre-existing data", encoding="utf-8")

    fake_pygments_mod = MagicMock()
    fake_pygments_mod.__file__ = str(fake_pyg / "__init__.py")
    fake_pygments_mod.__version__ = "2.15.0"
    monkeypatch.setitem(sys.modules, "pygments", fake_pygments_mod)

    # Simulate a copytree failure
    def failing_copytree(*args, **kwargs):
        raise OSError("Simulated copytree failure")

    monkeypatch.setattr(shutil, "copytree", failing_copytree)

    res = patcher.run_patch(skip_template_sync=True)
    assert res is False

    # In pre-fix code: shutil.rmtree(target_ext_dir) was called BEFORE copytree,
    # destroying target_ext_dir and sentinel_file.
    # In post-fix code: dirs_exist_ok=True is used without rmtree, preserving existing files.
    assert ext_dir.is_dir(), "target_ext_dir must not be deleted before copytree"
    assert sentinel_file.is_file(), "Existing files in target_ext_dir must survive if copytree fails"


# ==============================================================================
# DEFECT-R2-08: subprocess.run without explicit encoding="utf-8"
# ==============================================================================
def test_defect_r2_08_subprocess_run_utf8_encoding_and_error_handling(monkeypatch):
    """DEFECT-R2-08: subprocess.run calls in env_checker must include encoding='utf-8' and errors='replace'."""
    env = EnvironmentManager(auto_yes=True)

    recorded_kwargs = []
    def mock_subprocess_run(*args, **kwargs):
        recorded_kwargs.append(kwargs)
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Root1 : C:\\MiKTeX\\texmf\n"
        mock_res.stderr = ""
        return mock_res

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    monkeypatch.setattr(env, "get_miktex_tool", lambda name: pathlib.Path(f"C:/fake/{name}.exe"))

    # Trigger find_all_miktex_roots (runs kpsewhich and initexmf)
    env.find_all_miktex_roots()

    # Trigger ensure_miktex_packages (runs initexmf AutoInstall, kpsewhich, mpm/miktex)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda self: True)
    env.ensure_miktex_packages()

    assert len(recorded_kwargs) >= 2, "Expected subprocess.run calls to be captured"
    for kw in recorded_kwargs:
        if kw.get("text") is True:
            assert kw.get("encoding") == "utf-8", f"subprocess.run call missing encoding='utf-8': {kw}"
            assert kw.get("errors") == "replace", f"subprocess.run call missing errors='replace': {kw}"


# ==============================================================================
# DEFECT-R2-09: Quoted path strings passed to --workspace cause WinError 123
# ==============================================================================
def test_defect_r2_09_workspace_path_strips_quotes(tmp_path, monkeypatch):
    """DEFECT-R2-09: Quoted path strings passed to --workspace must strip quotes and not crash."""
    fake_appdata = tmp_path / "fake_appdata"
    fake_appdata.mkdir()
    monkeypatch.setenv("APPDATA", str(fake_appdata))

    env = EnvironmentManager(auto_yes=True)
    vscode_patcher = VSCodePatcher(env, auto_yes=True)
    minted_patcher = MintedPygmentsPatcher(env, auto_yes=True)

    ws_dir = tmp_path / "my workspace with spaces"
    ws_dir.mkdir()
    quoted_ws = f'"{ws_dir}"'

    # 1. VSCodePatcher with quoted workspace string
    success_vscode = vscode_patcher.run_patch(patch_workshop=True, patch_coderunner=True, target_workspace=quoted_ws)
    assert success_vscode is True, "VSCodePatcher must succeed on quoted workspace path"
    assert (ws_dir / ".vscode" / "settings.json").is_file(), "Workspace settings.json must be created"

    # 2. MintedPygmentsPatcher with quoted workspace string
    minted_patcher._offer_latex_template_sync(target_latex_dir=quoted_ws)
    assert (ws_dir / "lib" / "codebox.tex").is_file(), "lib/codebox.tex must be created"


# ==============================================================================
# DEFECT-R2-10: Cumulative timestamped backups and hardcoded settings.json name
# ==============================================================================
def test_defect_r2_10_vscode_patcher_conditional_backup_and_dynamic_name(tmp_path):
    """DEFECT-R2-10: VSCode settings backup must only be created if settings change, and use dynamic name."""
    settings_dir = tmp_path / "vscode_config"
    settings_dir.mkdir()
    custom_settings = settings_dir / "custom_user_settings.json"
    custom_settings.write_text('{\n    "editor.fontSize": 14\n}\n', encoding="utf-8")

    # Run 1: Settings file is modified -> exactly 1 timestamped backup created with dynamic name
    res1 = VSCodePatcher._patch_settings_file(custom_settings, patch_workshop=True, patch_coderunner=True)
    assert res1 is True

    # Check unversioned .json.bak
    bak_unversioned = custom_settings.with_suffix(".json.bak")
    assert bak_unversioned.is_file(), "Unversioned .json.bak must exist"

    # Check timestamped backups
    ts_backups = list(settings_dir.glob("custom_user_settings.json.bak.*"))
    assert len(ts_backups) == 1, f"Expected exactly 1 timestamped backup, found: {ts_backups}"
    # Verify backup is named after custom_user_settings.json, NOT hardcoded settings.json.bak.*
    assert not list(settings_dir.glob("settings.json.bak.*")), "Must not hardcode settings.json in backup filename"

    # Runs 2, 3, 4: File is already patched and unchanged -> NO new timestamped backups should be created
    for _ in range(3):
        res_repeat = VSCodePatcher._patch_settings_file(custom_settings, patch_workshop=True, patch_coderunner=True)
        assert res_repeat is True

    ts_backups_after = list(settings_dir.glob("custom_user_settings.json.bak.*"))
    assert len(ts_backups_after) == 1, (
        f"Repeated runs on unchanged settings must NOT create duplicate backups. Found: {len(ts_backups_after)}"
    )
