# Round 1 — Correctness Review Report

**Reviewer**: `reviewer_r1_gen2`  
**Date**: 2026-10-23  
**Working Directory**: `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\reviewer_r1_gen2\`  
**Review Type**: Objective Correctness Review & Adversarial Stress-Test (Static Analysis)  

---

## 1. Executive Summary & Verdict

**Verdict**: **`REQUEST_CHANGES`**

The codebase demonstrates substantial architectural enhancements in multi-root MiKTeX discovery, VS Code recipe merging, JSONC comment handling, and C++ semantic tokenization. However, static correctness and adversarial inspection revealed **10 REAL DEFECTS** (including 5 High/Critical severity issues that cause runtime crashes, syntax errors in generated LaTeX code, false-positive verification reporting, broken module import purity, and silent check failures) as well as **4 Minor/Stylistic issues**.

In accordance with the Project Fix Policy (R3), all **10 Real Defects** must be resolved and covered by regression tests before proceeding to Round 2.

---

## 2. Summary of Findings

| ID | File:Line | Severity | Classification | Summary |
| :--- | :--- | :--- | :--- | :--- |
| **DEFECT-01** | `patcher_core/minted_patcher.py:302` | **HIGH** | REAL DEFECT | `NameError: name 'Token' is not defined` when evaluating token parameter check. |
| **DEFECT-02** | `palenight_source/palenight_ext/patchers.py:253` | **CRITICAL** | REAL DEFECT | LaTeX Formatter macro definition hardcodes `@bc` instead of `@tname`, breaking LaTeX compilation with `Undefined control sequence`. |
| **DEFECT-03** | `patcher_core/minted_patcher.py:344-347` | **HIGH** | REAL DEFECT | `verify_patch()` omits `all_passed = False` when MiKTeX wheel is missing/unpatched, returning success (exit code 0). |
| **DEFECT-04** | `setup_latex_cpp.py:73` | **HIGH** | REAL DEFECT | `bootstrap_self_dependencies()` runs at module top-level on import, violating module purity and risking unintended `pip install` / `sys.exit(1)`. |
| **DEFECT-05** | `setup_latex_cpp.py:140-165` & `patcher_core/env_checker.py:476-482` | **HIGH** | REAL DEFECT | `setup_latex_cpp.py --check` returns exit code 0 even when Python or MiKTeX package installations fail because `run_all_checks()` returns `None`. |
| **DEFECT-06** | `palenight_source/palenight_ext/cpp_analyzer.py:502` | **MEDIUM** | REAL DEFECT | Function prototypes returning template types (e.g. `vector<int> solve(int a);`) fail `is_prototype` check because `prev_val == '>'` is omitted. |
| **DEFECT-07** | `palenight_source/palenight_ext/cpp_analyzer.py:533` | **MEDIUM** | REAL DEFECT | `is_inside_template_brackets(k)` called with closing bracket index `k` always returns `False`, failing local template variable shadowing. |
| **DEFECT-08** | `palenight_source/palenight_ext/cpp_analyzer.py:532` | **MEDIUM** | REAL DEFECT | Local pointer/reference variable declarations (`Type* x`, `Type& x`) fail to register as shadowed locals because `prev_val in ('*', '&')` is omitted. |
| **DEFECT-09** | `patcher_core/vscode_patcher.py:124-130` | **MEDIUM** | REAL DEFECT | `clean_jsonc` fails to strip trailing commas when followed by a comment before `}`/`]`, causing `JSONDecodeError`. |
| **DEFECT-10** | `patcher_core/vscode_patcher.py:284-290` | **MEDIUM** | REAL DEFECT | `VSCodePatcher.run_patch()` returns `True` (exit 0) when no VS Code settings file is found or patched, masking silent failure. |
| **ISSUE-11** | `patcher_core/tui_app.py:313` | **MINOR** | MINOR/STYLISTIC | `value=str(DEFAULT_LATEX_PROJECT)` fills input field with literal string `"None"` when project is `None`. |
| **ISSUE-12** | `run_patcher.bat:20` | **MINOR** | MINOR/STYLISTIC | Unconditional `pause` halts automation during non-interactive `-y` / `--yes` runs. |
| **ISSUE-13** | `palenight_source/palenight_ext/cpp_analyzer.py:438-443` | **MINOR** | MINOR/STYLISTIC | `operator[]` parameter parsing expects `(` instead of `[`/`]`. |
| **ISSUE-14** | `palenight_source/palenight_ext/cpp_analyzer.py:258-262` | **MINOR** | MINOR/STYLISTIC | Pass-by-value template parameter types in function declarations (e.g. `vector<Node> v`) have `Node` classified as `Name.Variable`. |

---

## 3. Detailed Findings: Real Defects

### DEFECT-01: NameError on undefined `Token` in `minted_patcher.py`
- **Location**: `patcher_core/minted_patcher.py:301-304`
- **Severity**: **HIGH**
- **Classification**: REAL DEFECT
- **Description**:
  In `verify_patch()`, the lexer hook check evaluates:
  ```python
  has_param = any(
      (str(t[0]).startswith("Token.Name.Variable.Parameter") or t[0] is Token.Name.Variable.Parameter or str(t[0]).startswith("Token.Name.Variable.Magic"))
      for t in tokens if t[1] == 'a'
  )
  ```
  `Token` is not imported anywhere in `patcher_core/minted_patcher.py`. If `str(t[0])` does not start with `"Token.Name.Variable.Parameter"` (for example, if semantic analysis fails or returns an unmodified Pygments token `Token.Name`), short-circuit evaluation fails over to `t[0] is Token.Name.Variable.Parameter`, raising `NameError: name 'Token' is not defined`. This turns a verification test failure into an unhandled exception caught as `Lỗi khi kiểm tra CppLexer hook: name 'Token' is not defined`.
- **Reproduction**:
  ```python
  from patcher_core.minted_patcher import MintedPygmentsPatcher
  from patcher_core.env_checker import EnvironmentManager
  # If a token for 'a' is Token.Name:
  t = ("Token.Name", "a")
  # Evaluating `str(t[0]).startswith("Token.Name.Variable.Parameter") or t[0] is Token.Name.Variable.Parameter`
  # raises NameError: name 'Token' is not defined
  ```
- **Proposed Fix**:
  Import `Token` at the top of `patcher_core/minted_patcher.py`:
  ```python
  from pygments.token import Token
  ```
  or simplify the predicate to safe string checks:
  ```python
  has_param = any(
      (str(t[0]).startswith("Token.Name.Variable.Parameter") or str(t[0]).startswith("Token.Name.Variable.Magic"))
      for t in tokens if t[1] == 'a'
  )
  ```

---

### DEFECT-02: Hardcoded `\PY@bc` in `patch_latex_formatter` breaks LaTeX Compilation
- **Location**: `palenight_source/palenight_ext/patchers.py:242-260`
- **Severity**: **CRITICAL**
- **Classification**: REAL DEFECT
- **Description**:
  In `patch_latex_formatter`, `_latex_create_stylesheet` configures custom commands for indent-rainbow tokens:
  ```python
  for ind_tok, hex_bg in INDENT_BG_MAP.items():
      tname = _get_ttype_name(ind_tok)
      if ir_active:
          ...
          cmndef = (
              rf'\def\{cp}@bc##1{{'
              rf'\ifcsname ifIndentRainbow\endcsname'
              rf'\ifIndentRainbow{box_cmd}\else##1\fi'
              rf'\else{box_cmd}\fi}}'
          )
          self.ttype2name[ind_tok] = tname
          self.cmd2def[tname] = cmndef
  ```
  Line 253 hardcodes `@bc` instead of `@{tname}`. When Pygments' `LatexFormatter` outputs a document, it formats indent tokens using `\PY{<tname>}{...}`, which calls `\csname PY@<tname>\endcsname`. Because the macro was defined with `@bc`, LaTeX throws `! Undefined control sequence \PY@<tname>`. Furthermore, in the loop over `INDENT_BG_MAP`, `\def\<cp>@bc##1` is defined 4 times, overwriting itself on each iteration so only `INDENT_4`'s color survives in `\PY@bc`.
- **Reproduction**:
  ```python
  from pygments.formatters.latex import LatexFormatter
  from palenight_source.palenight_ext.patchers import FormatterPatcher
  FormatterPatcher.patch_latex_formatter()
  fmt = LatexFormatter(style="palenight")
  stylesheet = fmt.get_style_defs()
  # Look for definitions: `\def\PY@w` or similar tname is missing, while `\def\PY@bc` is defined multiple times.
  assert r"\def\PY@bc" in stylesheet
  # Any document referencing the actual token name will fail in XeLaTeX / pdfLaTeX.
  ```
- **Proposed Fix**:
  Change line 253 in `palenight_source/palenight_ext/patchers.py` from:
  ```python
  rf'\def\{cp}@bc##1{{'
  ```
  to:
  ```python
  rf'\def\{cp}@{tname}##1{{'
  ```

---

### DEFECT-03: `verify_patch()` ignores missing MiKTeX wheel and reports success
- **Location**: `patcher_core/minted_patcher.py:344-347`
- **Severity**: **HIGH**
- **Classification**: REAL DEFECT
- **Description**:
  In `MintedPygmentsPatcher.verify_patch()`, Step 4 checks whether `pygments-*.whl` inside MiKTeX `scripts/minted/` has been patched:
  ```python
  if not found_whl:
      results.append((False, "Chưa tìm thấy gói pygments-*.whl được patch trong MiKTeX (hoặc chưa cài MiKTeX)."))

  return all_passed, results
  ```
  Notice that `all_passed = False` was omitted! If checks 1, 2, and 3 pass, `all_passed` remains `True`. `verify_patch()` returns `(True, results)`. In `setup_latex_cpp.py`:
  ```python
  ok, details = minted_patcher.verify_patch()
  ...
  if ok:
      print("🎉 HỆ THỐNG ĐÃ ĐƯỢC PATCH ĐẦY ĐỦ VÀ SẴN SÀNG!")
      return 0
  ```
  Even though MiKTeX was unpatched or absent, `--verify` prints success and exits with code 0!
- **Reproduction**:
  Run `verify_patch()` in an environment where Pygments is patched but MiKTeX `scripts/minted/pygments-*.whl` does not contain `palenight.py`. `verify_patch()` returns `(True, ...)`.
- **Proposed Fix**:
  Inside `if not found_whl:`, add `all_passed = False`:
  ```python
  if not found_whl:
      all_passed = False
      results.append((False, "Chưa tìm thấy gói pygments-*.whl được patch trong MiKTeX (hoặc chưa cài MiKTeX)."))
  ```
  Also update the return type signature on line 270 from `Tuple[bool, List[str]]` to `Tuple[bool, List[Tuple[bool, str]]]`.

---

### DEFECT-04: Top-level `bootstrap_self_dependencies()` runs at import time
- **Location**: `setup_latex_cpp.py:72-73`
- **Severity**: **HIGH**
- **Classification**: REAL DEFECT
- **Description**:
  Line 73 calls `bootstrap_self_dependencies()` at module top level:
  ```python
  # Tự động cài đặt thư viện cần thiết cho bản thân chương trình ngay khi khởi chạy
  bootstrap_self_dependencies()
  ```
  When `setup_latex_cpp` is imported by tests, sub-scripts, or analysis tools, it immediately executes subprocesses invoking `pip install --upgrade` if any dependency is absent, and calls `sys.exit(1)` if installation fails. This violates standard Python library conventions (importing a module must never execute side effects or terminate the interpreter) and directly violates Project Constraint R4 ("Never touch the real machine state: do not pip install anything other than pytest").
- **Reproduction**:
  ```python
  # In an environment missing 'latexminted':
  import setup_latex_cpp
  # Side effect: executes pip install latexminted during import!
  ```
- **Proposed Fix**:
  Remove `bootstrap_self_dependencies()` from line 73. Call it inside `main()` or inside `if __name__ == "__main__":` before importing or running the CLI.

---

### DEFECT-05: `--check` returns exit code 0 even when environment checks fail
- **Location**: `setup_latex_cpp.py:140-165` & `patcher_core/env_checker.py:476-482`
- **Severity**: **HIGH**
- **Classification**: REAL DEFECT
- **Description**:
  In `patcher_core/env_checker.py`:
  ```python
  def run_all_checks(self, ask_ext_install: bool = True) -> None:
      """Chạy trọn bộ 4 bước kiểm tra & tự động cài đặt."""
      self.check_and_report_system_software()
      self.ensure_python_libraries()
      self.ensure_miktex_packages()
      self.check_and_offer_vscode_extensions(ask_install=ask_ext_install)
  ```
  `run_all_checks()` returns `None`, discarding whether `ensure_python_libraries()` or `ensure_miktex_packages()` returned `False`.
  In `setup_latex_cpp.py`:
  ```python
  if args.check or args.all or args.minted or args.vscode:
      ...
      env.run_all_checks(ask_ext_install=not args.check)

      success = True
      if args.all or args.minted:
          if not minted_patcher.run_patch(...):
              success = False
      if args.all or args.vscode:
          ...
      if success:
          print("🎉 HOÀN TẤT QUÁ TRÌNH KIỂM TRA & PATCH HỆ THỐNG!")
          return 0
      else:
          return 1
  ```
  When only `--check` is passed: `args.all`, `args.minted`, and `args.vscode` are all `False`. `success` remains `True` unconditionally! Even if pip fails or MiKTeX tools are missing, `setup_latex_cpp.py --check` exits with code 0!
- **Reproduction**:
  Run `python setup_latex_cpp.py --check` in an environment where a required python library or MiKTeX package is missing and cannot be installed. The return code is 0 instead of 1.
- **Proposed Fix**:
  Update `EnvironmentManager.run_all_checks()` to return `bool`:
  ```python
  def run_all_checks(self, ask_ext_install: bool = True) -> bool:
      missing_sw = self.check_and_report_system_software()
      ok_py = self.ensure_python_libraries()
      ok_mik = self.ensure_miktex_packages()
      self.check_and_offer_vscode_extensions(ask_install=ask_ext_install)
      # Return False if critical components failed
      return ok_py and ok_mik and not any("MiKTeX" in s[0] for s in missing_sw)
  ```
  And in `setup_latex_cpp.py`:
  ```python
  checks_ok = env.run_all_checks(ask_ext_install=not args.check)
  if args.check:
      success = checks_ok
  ```

---

### DEFECT-06: Function prototypes returning template types fail parameter recognition
- **Location**: `palenight_source/palenight_ext/cpp_analyzer.py:495-504`
- **Severity**: **MEDIUM**
- **Classification**: REAL DEFECT
- **Description**:
  In `cpp_analyzer.py`, prototype detection handles declarations like `int compute(int val_a, double val_b);`:
  ```python
  if chk < n and tokens[chk][2] == ';':
      if prev_tok in (Keyword.Type, Name.Class, Name.Builtin) or prev_val in ('*', '&') or prev_val in type_aliases or prev_val in type_macros:
          is_prototype = True
  ```
  When a function prototype returns a template type, e.g. `vector<int> solve(int a, int b);`:
  The token immediately preceding `solve` is `>` (`prev_val == '>'`, `prev_tok == Punctuation`).
  Because `prev_val == '>'` is omitted from the condition, `is_prototype` evaluates to `False`. The tokens `a` and `b` inside `(int a, int b)` are not parsed as parameters and fail to be styled as `NAME_PARAM`.
- **Reproduction**:
  ```python
  from palenight_source.palenight_ext.cpp_analyzer import CppSemanticAnalyzer
  from pygments.lexers.c_cpp import CFamilyLexer, CppLexer
  from palenight_source.palenight_ext.config import NAME_PARAM
  tokens = list(CppSemanticAnalyzer.analyze(CppLexer(), CFamilyLexer, "vector<int> solve(int a, int b);"))
  a_toks = [tok for _, tok, val in tokens if val == 'a']
  # Current result: a_toks does NOT contain NAME_PARAM
  assert NAME_PARAM in a_toks, "Parameter 'a' in template prototype must be NAME_PARAM"
  ```
- **Proposed Fix**:
  Add `or prev_val == '>'` to line 502:
  ```python
  if prev_tok in (Keyword.Type, Name.Class, Name.Builtin) or prev_val in ('*', '&', '>') or prev_val in type_aliases or prev_val in type_macros:
      is_prototype = True
  ```

---

### DEFECT-07: `is_inside_template_brackets(k)` called with closing bracket index always returns `False`
- **Location**: `palenight_source/palenight_ext/cpp_analyzer.py:531-536`
- **Severity**: **MEDIUM**
- **Classification**: REAL DEFECT
- **Description**:
  In `cpp_analyzer.py`:
  ```python
  if func_param_stack and (
      prev_tok in (Keyword.Type, Name.Class, Name.Builtin)
      or (prev_val == '>' and is_inside_template_brackets(k))
      or (prev_val in type_macros)
  ):
      shadowed_locals_by_depth.setdefault(depth, set()).add(val)
  ```
  Here `k` is the index of `>`. Inside `is_inside_template_brackets(pos)`:
  Forward search for closing `>` starts at `m_idx = pos + 1` = `k + 1`. Because `pos` was already at the closing `>`, searching *after* `k` never encounters `>` and returns `False`. Consequently, any local variable of template type inside a function (e.g. `vector<int> a;`) is never added to `shadowed_locals_by_depth`. If `a` shadows an outer parameter, it fails to shadow properly.
  (Note: In contrast, line 572 correctly used `is_inside_template_brackets(k - 1)`).
- **Reproduction**:
  ```python
  code = "void solve(int a) { vector<int> a; a.push_back(1); }"
  # 'a' in `vector<int> a;` fails to be detected as a local shadowed variable.
  ```
- **Proposed Fix**:
  Change line 533 to:
  ```python
  or (prev_val == '>' and k >= 1 and is_inside_template_brackets(k - 1))
  ```

---

### DEFECT-08: Local pointer/reference variable declarations fail to register as shadowed locals
- **Location**: `palenight_source/palenight_ext/cpp_analyzer.py:531-536`
- **Severity**: **MEDIUM**
- **Classification**: REAL DEFECT
- **Description**:
  In line 532:
  ```python
  if func_param_stack and (
      prev_tok in (Keyword.Type, Name.Class, Name.Builtin)
      or (prev_val == '>' and is_inside_template_brackets(k))
      or (prev_val in type_macros)
  ):
      shadowed_locals_by_depth.setdefault(depth, set()).add(val)
  ```
  In C++, local variables declared as pointers or references (e.g. `int* p = nullptr;` or `MyClass& ref = obj;`) have `prev_val in ('*', '&')` and `prev_tok == Operator`. Unlike line 502 where `prev_val in ('*', '&')` was handled, line 532 omitted it. If a local pointer or reference variable shares a name with an outer parameter, it fails to be recognized as a local variable, and accesses in the body are incorrectly tokenized as `NAME_PARAM` rather than local variables.
- **Reproduction**:
  ```python
  code = "void solve(int* x) { int* x = nullptr; x = get(); }"
  # The second 'x' is not registered as a shadowed local.
  ```
- **Proposed Fix**:
  Add `or prev_val in ('*', '&')` to line 532:
  ```python
  if func_param_stack and (
      prev_tok in (Keyword.Type, Name.Class, Name.Builtin)
      or prev_val in ('*', '&')
      or (prev_val == '>' and k >= 1 and is_inside_template_brackets(k - 1))
      or (prev_val in type_macros)
  ):
      shadowed_locals_by_depth.setdefault(depth, set()).add(val)
  ```

---

### DEFECT-09: `clean_jsonc` fails to remove trailing commas followed by comments
- **Location**: `patcher_core/vscode_patcher.py:124-130`
- **Severity**: **MEDIUM**
- **Classification**: REAL DEFECT
- **Description**:
  In `clean_jsonc`:
  ```python
  if c == ',':
      j = i + 1
      while j < n and text[j] in ' \t\r\n':
          j += 1
      if j < n and text[j] in '}]':
          i += 1
          continue
  ```
  If there is a comment following a trailing comma (e.g. `,\n  // comment\n}` or `, /* comment */ }`), `text[j]` is `'/'`, which is not in `'}]'`. The trailing comma is retained. When comments are later removed, the trailing comma remains directly before `}` or `]`, causing standard Python `json.loads` to crash with `JSONDecodeError: Expecting property name enclosed in double quotes`.
- **Reproduction**:
  ```python
  from patcher_core.vscode_patcher import clean_jsonc
  import json
  sample = '{\n  "key": "val", // comment\n}'
  cleaned = clean_jsonc(sample)
  json.loads(cleaned) # Fails with JSONDecodeError because trailing comma was not removed
  ```
- **Proposed Fix**:
  Perform two passes in `clean_jsonc`: Pass 1 strips `//` and `/* */` comments while preserving string literals; Pass 2 removes trailing commas before `}` or `]`. Alternatively, allow lookahead `j` to skip comments.

---

### DEFECT-10: `VSCodePatcher.run_patch()` returns `True` when nothing was patched
- **Location**: `patcher_core/vscode_patcher.py:281-290`
- **Severity**: **MEDIUM**
- **Classification**: REAL DEFECT
- **Description**:
  In `VSCodePatcher.run_patch()`:
  ```python
  if not target_files:
      print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy thư mục cấu hình `%APPDATA%\\Code\\User`.")

  patch_success = True
  for label, s_path in target_files:
      ...
  ```
  If VS Code is not installed on the machine (common in headless/minimal containers or machines without VS Code) and no `--workspace` argument is provided, `target_files` is empty and `ws_path` is None. `patch_success` remains `True`. `setup_latex_cpp.py --vscode` exits with code 0 and reports full success even though zero files were patched.
- **Reproduction**:
  Run `python setup_latex_cpp.py --vscode --yes` in an environment where `%APPDATA%\Code\User` does not exist. Return code is 0.
- **Proposed Fix**:
  If `not target_files and not ws_path`, set `patch_success = False` and print a notice that no target settings files were found.

---

## 4. Detailed Findings: Minor / Stylistic Issues

### ISSUE-11: `value=str(DEFAULT_LATEX_PROJECT)` renders literal `"None"` in TUI input
- **Location**: `patcher_core/tui_app.py:313`
- **Severity**: **MINOR**
- **Classification**: MINOR/STYLISTIC
- **Description**: If `DEFAULT_LATEX_PROJECT` is `None`, `str(None)` produces `"None"`. The TUI input box starts with `"None"` as the workspace directory.
- **Proposed Fix**: Use `value=str(DEFAULT_LATEX_PROJECT or "")`.

---

### ISSUE-12: Unconditional `pause` in `run_patcher.bat`
- **Location**: `run_patcher.bat:20`
- **Severity**: **MINOR**
- **Classification**: MINOR/STYLISTIC
- **Description**: Line 20 runs `pause` unconditionally. In automated/headless/non-interactive workflows (such as `-y` / `--yes`), this halts until a key is pressed.
- **Proposed Fix**: Skip `pause` if `-y` or `--yes` is present in `%*`.

---

### ISSUE-13: `operator[]` parameter parsing logic in `cpp_analyzer.py`
- **Location**: `palenight_source/palenight_ext/cpp_analyzer.py:438-443`
- **Severity**: **MINOR**
- **Classification**: MINOR/STYLISTIC
- **Description**: Lines 438-443 assume operator parameters are enclosed in `(...)`. For `operator[]`, parameters are enclosed in `[...]` (e.g. `int& operator[](size_t idx)`), so line 443 fails to find `(` and skips parameter analysis.
- **Proposed Fix**: Check for `[` as an alternate opening bracket for `operator[]`.

---

### ISSUE-14: Pass-by-value template parameter types classified as `Name.Variable`
- **Location**: `palenight_source/palenight_ext/cpp_analyzer.py:258-262`
- **Severity**: **MINOR**
- **Classification**: MINOR/STYLISTIC
- **Description**: In `is_inside_template_brackets`, when inside parentheses, line 260 requires the token following `>` to be in `('(', '{', '::', '>', '*', '&')`. For pass-by-value parameters like `void f(vector<Node> v)`, the token after `>` is the parameter identifier `v`, causing `is_inside_template_brackets` to return `False` and `Node` to be styled as `Name.Variable`.
- **Proposed Fix**: Expand whitelist or recognize function parameter signatures.

---

## 5. Verified Claims Analysis

- **Claim 1 (Gen 1 Finding 1)**: `patcher_core/minted_patcher.py:302` uses `Token.Name.Variable.Parameter` without importing `Token`.
  - **Verification**: Verified via `view_file` on `minted_patcher.py`. Confirmed: `Token` is never imported in the module. If `str(t[0])` is not matched, evaluation triggers `NameError`. **(CONFIRMED DEFECT-01)**
- **Claim 2 (Gen 1 Finding 2)**: `setup_latex_cpp.py` with `--check` discards check results and exits with 0.
  - **Verification**: Verified via `view_file` on `setup_latex_cpp.py:140-165` and `env_checker.py:476-482`. Confirmed: `run_all_checks()` returns `None`, `success` stays `True`, exit code is always 0. **(CONFIRMED DEFECT-05)**
- **Claim 3 (Gen 1 Finding 3)**: `bootstrap_self_dependencies()` executes at top-level on import.
  - **Verification**: Verified via `view_file` on `setup_latex_cpp.py:73`. Confirmed: executes unconditionally on module import. **(CONFIRMED DEFECT-04)**

---

## 6. Adversarial Attack Surface & Stress-Test Analysis

1. **Adversarial Input: JSONC with comments following trailing commas**:
   - Stress test: `{"k": 1, /* comment */ }`
   - Expected: Parsed cleanly into `{"k": 1}`.
   - Result: **FAILS** in `clean_jsonc` due to DEFECT-09 (`JSONDecodeError`).

2. **Adversarial Input: LaTeX stylesheet generation with indent-rainbow**:
   - Stress test: Calling `LatexFormatter(style="palenight").get_style_defs()` with indent rainbow enabled.
   - Expected: Stylesheet defines `\def\PY@<tname>` for each indent level token.
   - Result: **FAILS** due to DEFECT-02 (hardcoded `\def\PY@bc` leaves `\PY@<tname>` undefined).

3. **Adversarial Scenario: `verify_patch()` on partially installed environment**:
   - Stress test: Pygments style is present, but MiKTeX wheel is missing or unpatched.
   - Expected: `verify_patch()` returns `(False, ...)` and CLI exits with code 1.
   - Result: **FAILS** due to DEFECT-03 (returns `(True, ...)` and exit code 0).

4. **Adversarial Scenario: Module import in pytest test runner**:
   - Stress test: `import setup_latex_cpp` in an isolated test runner.
   - Expected: Module imports cleanly without modifying system or calling pip.
   - Result: **FAILS** due to DEFECT-04 (runs pip install and `sys.exit(1)` on missing packages).

5. **Adversarial C++ Code: Function prototype returning template type**:
   - Stress test: `vector<int> solve(int a, int b);`
   - Expected: `a` and `b` highlighted as `NAME_PARAM`.
   - Result: **FAILS** due to DEFECT-06 (`is_prototype` returns False).
