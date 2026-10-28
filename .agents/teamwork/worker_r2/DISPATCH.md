# DISPATCH — Round 2 Fix Worker

## Identity
- **Name**: `worker_r2`
- **Role**: `teamwork_preview_worker`
- **Working Directory**: `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\worker_r2\`

## Input Context Files
1. `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\reviewer_r2\review_r2.md`
3. `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\reviewer_r2\handoff.md`
4. `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\worker_r1\changes.md`

## Mission
Resolve all **10 REAL DEFECTS** identified in Round 2 (Safety of System Modifications) and write comprehensive pytest regression tests in `tests/test_r2_safety.py`.

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Real Defects to Fix:
1. **DEFECT-R2-01**: `patcher_core/vscode_patcher.py:268-271` — Non-atomic write to `settings.json` (`write_text`). Fix: write to a `.tmp` file in the same directory and use `os.replace` for atomic swap, with `finally` cleanup.
2. **DEFECT-R2-02**: `patcher_core/minted_patcher.py:95` & `154` — Non-atomic writes to Pygments `c_cpp.py` and MiKTeX `latexminted.py`. Fix: write to `.tmp` and atomically replace with `os.replace`, with `finally` cleanup.
3. **DEFECT-R2-03**: `patcher_core/vscode_patcher.py:71-73` — Unquoted `$dir` in `CODE_RUNNER_EXECUTORS` (`cd $dir`). Fix: Quote `$dir` as `\"$dir\"` in both C++ and LaTeX command strings.
4. **DEFECT-R2-04**: `patcher_core/minted_patcher.py:172-214` — Abandoned `.whl.tmp` in MiKTeX directory on exception. Fix: Add `try...finally` block ensuring `tmp_whl` is deleted if it exists.
5. **DEFECT-R2-05**: `patcher_core/minted_patcher.py:254` — Unhandled `UnicodeDecodeError` when reading existing `codebox.tex`. Fix: Use `read_bytes()` for binary comparison instead of `read_text(encoding="utf-8")`.
6. **DEFECT-R2-06**: `patcher_core/minted_patcher.py:255` — `codebox.tex` backup unconditionally overwrites `.bak`. Fix: Guard backup with `if not bak_codebox.exists():`.
7. **DEFECT-R2-07**: `patcher_core/minted_patcher.py:74-80` — Destructive `shutil.rmtree` on `palenight_ext` before `copytree`. Fix: Use `shutil.copytree(..., dirs_exist_ok=True)` without wiping the directory first.
8. **DEFECT-R2-08**: `patcher_core/env_checker.py:161, 178, 378, 418` — `subprocess.run(..., text=True)` without explicit UTF-8 encoding. Fix: Add `encoding="utf-8", errors="replace"` to these calls.
9. **DEFECT-R2-09**: `patcher_core/minted_patcher.py:222` & `patcher_core/vscode_patcher.py:326` — Quoted path strings passed to `--workspace` cause `WinError 123`. Fix: Strip whitespace and quotes (`str(...).strip().strip('"')`) before `pathlib.Path(...).resolve()`.
10. **DEFECT-R2-10**: `patcher_core/vscode_patcher.py:243-244` — Cumulative timestamped backups created unconditionally on every run. Fix: Only create backup when `settings.json` is actually about to be modified (or avoid creating duplicate backups on already-patched configurations).

### Regression Testing:
- Create `tests/test_r2_safety.py` containing at least 10 regression tests (1 per defect).
- Verify each test targets the exact safety vulnerability and verifies the fix.
- Run `python -m pytest` with `WaitMsBeforeAsync=10000` to verify all 22 existing tests + new R2 tests pass.

### Strict Safety Constraints:
- NEVER touch real system state (no site-packages, MiKTeX, real VS Code settings). Use `tmp_path` and mocks only.
- NEVER modify `setup_latex_cpp_release.zip`.
- Do NOT git commit or push.

### Deliverables:
- Write `changes.md` and `handoff.md` in `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\worker_r2\`.
- Send completion message to orchestrator via `send_message`.

## 2026-10-23T03:54:46Z
From: fdea7623-faff-40a8-91ce-a8645c6833b8
Fix all 10 REAL DEFECTS identified by reviewer_r2 (DEFECT-R2-01 through DEFECT-R2-10) and implement comprehensive pytest regression tests in tests/test_r2_safety.py.

