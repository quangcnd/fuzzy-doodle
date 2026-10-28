# Changes Implemented by worker_r1 (Round 1 Fixes)

## 1. Overview
All 10 REAL DEFECTS identified by `reviewer_r1_gen2` in Round 1 (Correctness) have been resolved with minimal, precise modifications. Comprehensive regression tests covering every single defect were authored in `tests/test_r1_correctness.py`.

---

## 2. Summary of Changes by Defect

### DEFECT-01: NameError on undefined `Token` in `minted_patcher.py`
- **File**: `patcher_core/minted_patcher.py:11`
- **Change**: Imported `Token` from `pygments.token`.
- **Rationale**: Prevents `NameError: name 'Token' is not defined` when evaluating token checks in `verify_patch()`.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_01_token_name_import_and_no_nameerror`

### DEFECT-02: Hardcoded `\PY@bc` in `patch_latex_formatter`
- **File**: `palenight_source/palenight_ext/patchers.py:253`
- **Change**: Replaced `rf'\def\{cp}@bc##1{{'` with `rf'\def\{cp}@{tname}##1{{'`.
- **Rationale**: Previously defined `\def\PY@bc` 4 times (overwriting previous levels) and left `\PY@<tname>` undefined, crashing LaTeX compilation with `Undefined control sequence \PY@<tname>`. Now defines `\PY@wIndentL1` through `\PY@wIndentL4`.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_02_latex_formatter_macro_uses_tname_not_bc`

### DEFECT-03: `verify_patch()` reports success when MiKTeX wheel is missing
- **File**: `patcher_core/minted_patcher.py:345`
- **Change**: Added `all_passed = False` inside `if not found_whl:`. Also updated return type annotation to `Tuple[bool, List[Tuple[bool, str]]]`.
- **Rationale**: Previously omitted setting `all_passed = False`, causing `verify_patch()` to return `True` (and CLI `--verify` exit code 0) even when the required wheel was absent or unpatched.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_03_verify_patch_fails_when_miktex_wheel_not_found`

### DEFECT-04: Top-level `bootstrap_self_dependencies()` executed on import
- **File**: `setup_latex_cpp.py:73` and `setup_latex_cpp.py:112`
- **Change**: Removed top-level invocation of `bootstrap_self_dependencies()` at module scope. Placed call at the entry of `main()`.
- **Rationale**: Importing `setup_latex_cpp` previously triggered subprocess `pip install` and `sys.exit(1)` on missing packages, violating import purity and safety constraint R4.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_04_importing_setup_latex_cpp_does_not_bootstrap_dependencies`

### DEFECT-05: `--check` returns exit code 0 on check failure
- **Files**: `patcher_core/env_checker.py:476` and `setup_latex_cpp.py:137-142`
- **Change**:
  - `EnvironmentManager.run_all_checks()` now aggregates check statuses and returns `bool`: `return bool(ok_py and ok_mik and has_critical_sw)`.
  - `setup_latex_cpp.py` checks `checks_ok = env.run_all_checks(...)` and assigns `if args.check: success = checks_ok`.
- **Rationale**: Previously `run_all_checks()` returned `None`, and `--check` exited with code 0 even when pip package installation failed or MiKTeX was missing.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_05_env_checker_run_all_checks_returns_bool_and_check_flag_exits_nonzero`

### DEFECT-06: Template prototype return types fail parameter recognition
- **File**: `palenight_source/palenight_ext/cpp_analyzer.py:502`
- **Change**: Added `or prev_val in ('*', '&', '>')` to prototype declaration detection.
- **Rationale**: Prototypes returning templates (e.g. `vector<int> solve(int a, double b);`) have `>` as the token before the function identifier. Omitting `>` caused `is_prototype` to evaluate to `False`, failing to tokenize parameters as `NAME_PARAM`.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_06_cpp_analyzer_template_prototype_parameter_highlighting`

### DEFECT-07: `is_inside_template_brackets(k)` called with closing bracket index returns `False`
- **File**: `palenight_source/palenight_ext/cpp_analyzer.py:534`
- **Change**: Passed `k - 1` instead of `k`: `(prev_val == '>' and k >= 1 and is_inside_template_brackets(k - 1))`.
- **Rationale**: Forward scanning for matching `>` begins at `pos + 1`. Passing the closing `>` index `k` caused the scan to search after `k`, which always returned `False`. Local template variables (e.g. `vector<int> a;`) therefore failed to register as shadowed locals.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_07_cpp_analyzer_shadowed_local_template_variable`

### DEFECT-08: Local pointer/reference variables fail to register as shadowed locals
- **File**: `palenight_source/palenight_ext/cpp_analyzer.py:533`
- **Change**: Added `or prev_val in ('*', '&')` to local variable declaration check.
- **Rationale**: Local pointer (`Type* x;`) and reference (`Type& y;`) declarations have `*` or `&` as the preceding token. Omitting them caused local pointers/references to not register as shadowed locals, erroneously retaining parameter highlighting on body usages.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_08_cpp_analyzer_shadowed_local_pointer_and_reference`

### DEFECT-09: `clean_jsonc` fails to remove trailing commas followed by comments
- **File**: `patcher_core/vscode_patcher.py:82-135`
- **Change**: Implemented robust 2-pass parser:
  - Pass 1 strips `//` and `/* ... */` comments while preserving string literals and escapes.
  - Pass 2 strips trailing commas before `}` or `]`.
- **Rationale**: Single-pass comma lookahead failed when comments intervened between a comma and closing brace, retaining trailing commas and causing `json.loads` `JSONDecodeError`.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_09_clean_jsonc_trailing_commas_with_comments`

### DEFECT-10: `VSCodePatcher.run_patch()` returns `True` when zero target files found
- **File**: `patcher_core/vscode_patcher.py:355-357`
- **Change**: Added check `if not target_files and not (ws_path and ws_path.is_dir()): return False`.
- **Rationale**: In headless environments or systems without `%APPDATA%\Code\User` and without `--workspace`, `run_patch()` previously returned `True`, masking complete failure to patch any settings files.
- **Regression Test**: `tests/test_r1_correctness.py::test_defect_10_vscode_run_patch_fails_when_no_targets`

---

## 3. Test Suite Verification
- **Test File Added**: `tests/test_r1_correctness.py` (10 tests, 1 per defect)
- **Total Tests Collected**: 22 tests (12 existing + 10 new regression tests)
- **Result**: `22 passed in 0.28s`
- **Release Zip**: `setup_latex_cpp_release.zip` untouched (byte-identical)
- **Git Commits**: Zero commits created.
