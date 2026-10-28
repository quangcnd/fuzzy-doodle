# Changes Implemented by worker_r2 (Round 2 Fixes)

## 1. Overview
All 10 REAL DEFECTS identified by `reviewer_r2` in Round 2 (Safety of System Modifications) have been completely resolved with clean, minimal edits in adherence to Project Requirement R3. A comprehensive suite of 10 dedicated regression tests covering every safety fix was implemented in `tests/test_r2_safety.py`.

---

## 2. Summary of Changes by Defect

### DEFECT-R2-01: Non-atomic write to `settings.json`
- **File**: `patcher_core/vscode_patcher.py:269-289`
- **Change**: Replaced direct `settings_path.write_text(...)` with atomic write pattern:
  - Writes to temporary file: `tmp_path = settings_path.with_name(f"{settings_path.name}.tmp")`
  - Atomically swaps destination via `os.replace(tmp_path, settings_path)`
  - Wraps in `try...finally` to ensure `tmp_path` is unlinked if any error occurs.
- **Rationale**: Direct `write_text` immediately truncates destination files to 0 bytes upon opening in write mode (`"w"`). If interrupted or failed, settings files were left empty or corrupted. Atomic replacement guarantees all-or-nothing modification.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_01_vscode_settings_atomic_write`

### DEFECT-R2-02: Non-atomic writes to Pygments `c_cpp.py` and MiKTeX `latexminted.py`
- **File**: `patcher_core/minted_patcher.py:94-106` and `162-174`
- **Change**:
  - `c_cpp.py`: Writes to `tmp_cpp = cpp_lexer_file.with_name(f"{cpp_lexer_file.name}.tmp")`, performs `os.replace(tmp_cpp, cpp_lexer_file)`, and removes `tmp_cpp` in `finally`.
  - `latexminted.py`: Writes to `tmp_lm = latexminted_py.with_name(f"{latexminted_py.name}.tmp")`, performs `os.replace(tmp_lm, latexminted_py)`, and removes `tmp_lm` in `finally`.
- **Rationale**: Prevents accidental truncation to 0 bytes of critical Python site-packages and MiKTeX distribution scripts upon write interruption or disk quota exhaustion.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_02_minted_patcher_atomic_writes`

### DEFECT-R2-03: Unquoted `$dir` in Code Runner executor commands
- **File**: `patcher_core/vscode_patcher.py:72-74` and `260`
- **Change**:
  - Quoted `$dir` as `\"$dir\"` in both C++ and LaTeX command strings:
    - `"cpp": "cd \"$dir\" && g++ -std=c++17 -O2 -Wl,--stack=67108864 \"$fileName\" -o \"$fileNameWithoutExt\" && \"$dir$fileNameWithoutExt\""`
    - `"latex": "cd \"$dir\" && xelatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error \"$fileName\""`
  - Updated executor check in `_patch_settings_file` to recognize previous unquoted version and safely update it to quoted version.
- **Rationale**: Paths with spaces (e.g. `C:\Users\John Doe\Latex Projects\`) broke terminal `cd` commands in both PowerShell and cmd.exe when `$dir` was unquoted.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_03_code_runner_executors_quoted_dir`

### DEFECT-R2-04: Abandoned `.whl.tmp` in MiKTeX directory upon exception
- **File**: `patcher_core/minted_patcher.py:180-222`
- **Change**:
  - Replaced `shutil.move` with atomic `os.replace(tmp_whl, whl_path)`.
  - Wrapped wheel construction and replacement in `try...finally` to guarantee `tmp_whl.unlink()` executes if `tmp_whl.exists()`.
  - Added `errors="replace"` when decoding internal `c_cpp.py` from wheel.
- **Rationale**: Previously, any exception during zip creation or file replacement left orphaned `pygments-*.whl.tmp` files permanently littered in MiKTeX `scripts/minted`.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_04_abandoned_tmp_whl_cleaned_up_on_exception`

### DEFECT-R2-05: Unhandled `UnicodeDecodeError` when reading existing `codebox.tex`
- **File**: `patcher_core/minted_patcher.py:280`
- **Change**: Changed `dst_codebox.read_text(encoding="utf-8") != src_codebox.read_text(encoding="utf-8")` to `dst_codebox.read_bytes() != src_codebox.read_bytes()`.
- **Rationale**: Existing LaTeX projects containing `lib/codebox.tex` saved with Windows-1258, Windows-1252, or invalid bytes crashed the patcher with unhandled `UnicodeDecodeError`. Raw binary comparison avoids all decoding issues.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_05_offer_latex_template_sync_non_utf8_binary_safe`

### DEFECT-R2-06: `codebox.tex` backup unconditionally overwrites `.bak`
- **File**: `patcher_core/minted_patcher.py:281-283`
- **Change**: Added guard:
  ```python
  bak_codebox = dst_codebox.with_suffix(".tex.bak")
  if not bak_codebox.exists():
      shutil.copy2(dst_codebox, bak_codebox)
  ```
- **Rationale**: Aligns `codebox.tex` backup behavior with all other patchers. Prevents subsequent runs from overwriting and destroying the original pre-patch backup.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_06_codebox_backup_does_not_overwrite_pristine_bak`

### DEFECT-R2-07: Destructive `shutil.rmtree` on `palenight_ext` before `copytree`
- **File**: `patcher_core/minted_patcher.py:73-80`
- **Change**: Removed `if target_ext_dir.exists(): shutil.rmtree(target_ext_dir)`. Added `dirs_exist_ok=True` to `shutil.copytree(...)`.
- **Rationale**: If `copytree` failed (due to permissions, antivirus lock, or I/O error), `rmtree` had already wiped the existing directory, leaving Pygments with missing modules and causing `ModuleNotFoundError`. `dirs_exist_ok=True` overlays files non-destructively.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_07_palenight_ext_non_destructive_copytree`

### DEFECT-R2-08: `subprocess.run(..., text=True)` without explicit UTF-8 encoding
- **File**: `patcher_core/env_checker.py:165, 183, 370, 386, 423`
- **Change**: Added `encoding="utf-8", errors="replace"` to all `subprocess.run(..., capture_output=True, text=True)` calls.
- **Rationale**: On Windows systems running default OEM code pages (e.g. CP1252, CP437, CP936), non-ASCII paths or console output triggered `UnicodeDecodeError`.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_08_subprocess_run_utf8_encoding_and_error_handling`

### DEFECT-R2-09: Quoted path strings passed to `--workspace` cause `WinError 123`
- **File**: `patcher_core/minted_patcher.py:249-250` and `patcher_core/vscode_patcher.py:342-343`
- **Change**: Stripped quotes and whitespace prior to calling `pathlib.Path.resolve()`:
  - `minted_patcher.py`: `cleaned_dir = str(target_latex_dir).strip().strip('"')`, then `cand = pathlib.Path(cleaned_dir).resolve()`
  - `vscode_patcher.py`: `cleaned_ws = str(target_workspace).strip().strip('"')`, then `cand = pathlib.Path(cleaned_ws).resolve()`
- **Rationale**: When paths with enclosing quotes (e.g. `"\"C:\\My Latex\""`) were passed from scripts or wrappers, `resolve()` threw `OSError: [WinError 123]`.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_09_workspace_path_strips_quotes`

### DEFECT-R2-10: Cumulative timestamped backups and hardcoded `settings.json` name
- **File**: `patcher_core/vscode_patcher.py:238, 267-275`
- **Change**:
  - Saved `original_data = copy.deepcopy(data)` before modification.
  - Added check: if `settings_path.is_file() and data == original_data: return True`, avoiding creating redundant backups or touching disk when settings already match.
  - Used dynamic filename `f"{settings_path.name}.bak.{ts}"` instead of hardcoded `settings.json.bak.{ts}`.
- **Rationale**: Running the patcher repeatedly created unbound timestamped `.bak.<ts>` files containing already-patched settings and cluttered user directories. Dynamic naming ensures profile/custom settings files are backed up to their respective filenames.
- **Regression Test**: `tests/test_r2_safety.py::test_defect_r2_10_vscode_patcher_conditional_backup_and_dynamic_name`

---

## 3. Regression Test Suite
- **New Test File**: `tests/test_r2_safety.py` (10 tests, 1 per defect)
- **Environment Isolation**: All tests utilize `tmp_path` and `monkeypatch` (including overriding `APPDATA` to isolate from real VS Code settings and mocking Pygments / MiKTeX paths). Real system state is 100% untouched.
- **Release Zip**: `setup_latex_cpp_release.zip` untouched.
- **Git State**: Zero git commits or pushes.
