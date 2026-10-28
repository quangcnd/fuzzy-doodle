# Baseline Codebase & Test Suite Survey (M0)

**Date**: 2026-10-23  
**Explorer**: `explorer_m0`  
**Repository**: `c:\Users\admin\Documents\antigravity\clever-salk`  
**Branch**: `main` (commit HEAD `351db88` / origin/main)  

---

## 1. Executive Summary

This survey establishes the baseline repository state before the execution of the 3 sequential review rounds requested by the user.

Key baseline facts established:
- **Git working copy status**: Exactly **10 files modified** with **1000 insertions(+) and 276 deletions(-)** against `HEAD`. Untracked directories include `.agents/`, `tests/`, `LICENSE`, `requirements.txt`.
- **Test environment**: Python 3.14.3 (`D:\Runtimes\Python\python.exe`) with `pytest-9.1.1` installed (isolated test dependency).
- **Baseline test suite**: **12 tests passed** (100% pass rate, 0 failures, 0 errors, duration 0.16s) across `tests/test_cpp_highlighting.py` (8 tests) and `tests/test_patchers.py` (4 tests).
- **Release archive integrity**: `setup_latex_cpp_release.zip` has size **55,639 bytes** and SHA256 `034023A9ECAD2C514656BF79948925E4F0188817E078E04A38AF9F7554A9D1E8`. It represents the pre-patch release state and is now outdated relative to the ~1000 lines of uncommitted changes.
- **Environment safety**: No modifications have been made to site-packages (except installing `pytest`), MiKTeX installations, or user VS Code settings. All working tree changes remain uncommitted.

---

## 2. Architecture & Repository Map

The repository contains an automated installation and patcher tool designed for Windows / LaTeX / C++ competitive programming and document authoring environments:

```
clever-salk/
├── .gitignore                          [MODIFIED: ignores *.zip]
├── README.md                           [MODIFIED: updated CLI, flags, verify, notes]
├── LICENSE                             [UNTRACKED: MIT License]
├── requirements.txt                    [UNTRACKED: textual, pygments, pillow, latexminted]
├── run_patcher.bat                     [MODIFIED: py -3 vs python, UTF-8, exitcode propagation]
├── setup_latex_cpp.py                  [MODIFIED: bootstrap error handling, --verify, return codes]
├── setup_latex_cpp_release.zip         [UNCHANGED: original release bundle]
├── latex_templates/
│   └── lib/
│       └── codebox.tex                 [UNCHANGED: minted tcolorbox template with Palenight colors]
├── palenight_source/
│   ├── palenight.py                    [UNCHANGED: Pygments Style subclass for Palenight]
│   └── palenight_ext/
│       ├── __init__.py                 [UNCHANGED]
│       ├── config.py                   [UNCHANGED: token styling, colors, bracket styles]
│       ├── fonts.py                    [UNCHANGED: PIL font fallback and rendering]
│       ├── indent_rainbow.py           [UNCHANGED: indent-level background processor]
│       ├── cpp_analyzer.py             [MODIFIED: semantic analyzer, bracket isolation, lambdas]
│       └── patchers.py                 [MODIFIED: PALENIGHT_DEBUG logging, safe patching]
├── patcher_core/
│   ├── __init__.py                     [UNCHANGED: exports modules and classes]
│   ├── env_checker.py                  [MODIFIED: find_all_miktex_roots, texmf discovery]
│   ├── minted_patcher.py               [MODIFIED: multi-root patching, safe whl hook, verify_patch]
│   ├── ui.py                           [MODIFIED: safe project detection, repo isolation]
│   ├── vscode_patcher.py               [MODIFIED: clean_jsonc, recipe/tool merge, timestamped bak]
│   └── tui_app.py                      [UNCHANGED: Textual TUI interface]
└── tests/                              [UNTRACKED: automated test suite]
    ├── test_cpp_highlighting.py        [8 test cases: C++ semantic & bracket analysis]
    └── test_patchers.py                [4 test cases: JSONC cleaning, merge safety, repo exclusion]
```

### Module Responsibilities:
1. **Entry Point & CLI (`setup_latex_cpp.py`)**:
   - Auto-bootstraps missing Python runtime libraries (`textual`, `pygments`, `pillow`, `latexminted`) via pip.
   - CLI flags: `--tui`, `--cli-menu`, `--verify`, `--all`, `--minted`, `--vscode`, `--workshop-only`, `--coderunner-only`, `--check`, `--workspace <path>`, `-y` / `--yes`.
   - Dispatches to `run_textual_tui()` (Textual interactive TUI) or classic CLI menu or direct command-line execution.
2. **Environment Checker (`patcher_core/env_checker.py`)**:
   - `EnvironmentManager`: detects Python executable, Pygments installation path, MiKTeX binaries (`latex`, `pdflatex`, `xelatex`, `latexmk`, `initexmf`, `mpm`, `kpsewhich`).
   - Discovers all TEXMF root directories across user and system levels (`find_all_miktex_roots`).
3. **Minted & Pygments Patcher (`patcher_core/minted_patcher.py`)**:
   - Copies `palenight.py` and `palenight_ext/` into local Python Pygments `styles/`.
   - Inserts monkeypatch hook into `pygments/lexers/c_cpp.py`.
   - Updates MiKTeX `latexminted.py` to prioritize `site-packages` over internal `.whl`.
   - Injects `palenight` style and hook into internal `pygments-*.whl` inside MiKTeX `scripts/minted/`.
   - Supports non-destructive verification via `verify_patch()`.
4. **VS Code Settings Patcher (`patcher_core/vscode_patcher.py`)**:
   - Updates `%APPDATA%\Code\User\settings.json`, profile settings, and workspace `.vscode/settings.json`.
   - Custom `clean_jsonc()` function to safely strip single-line comments `//`, block comments `/* */`, and trailing commas.
   - Merges `latex-workshop.latex.tools` and `latex-workshop.latex.recipes` by key `name` (preserving custom recipes).
   - Configures Code Runner `code-runner.executorMap` for C++17 and XeLaTeX, preserving custom user C++ commands.
   - Generates dual backups (`.bak` and `.bak.<timestamp>`).
5. **C++ Semantic Analyzer (`palenight_source/palenight_ext/cpp_analyzer.py`)**:
   - Runs post-lexing semantic analysis on tokens from Pygments `CppLexer`.
   - Extracts multiline `#define` macros and isolates macro bracket depth from outer code.
   - Assigns 3-level rainbow bracket tokens (`BRACKET_LEVELS`).
   - Identifies functions, class constructors, member initializers (`: x{1}, y(2)`), lambdas (`[...] (...) { ... }`), operator overloads, and distinguishes them from variables.
   - Distinguishes template brackets `<...>` from comparison expressions `a < b && c > d`.
   - Tracks parameter scopes across nested blocks and shadows.

---

## 3. Detailed Git Status & Diff Analysis

`git diff --stat` against `HEAD`:
```
 .gitignore                                     |   2 +
 README.md                                      |  80 +++++-
 palenight_source/palenight_ext/cpp_analyzer.py | 363 +++++++++++++++++++++----
 palenight_source/palenight_ext/patchers.py     |  20 +-
 patcher_core/env_checker.py                    |  72 +++++
 patcher_core/minted_patcher.py                 | 338 ++++++++++++++++-------
 patcher_core/ui.py                             |  22 +-
 patcher_core/vscode_patcher.py                 | 267 +++++++++++++-----
 run_patcher.bat                                |  16 +-
 setup_latex_cpp.py                             |  96 +++++--
 10 files changed, 1000 insertions(+), 276 deletions(-)
```

### File-by-File Analysis:

#### 1. `.gitignore` (+2 lines)
- Added `*.zip` to prevent accidental inclusion of generated or release zip files into git.

#### 2. `README.md` (+80 lines, -1 line)
- Added documentation for `--verify` flag, CLI Menu mode, and updated CLI flag table.
- Added usage instructions for Windows launcher (`run_patcher.bat`) and UTF-8 handling.
- Added sections explaining global Pygments monkeypatching, upgrading Pygments/MiKTeX, and `PALENIGHT_DEBUG=1` diagnostic mode.

#### 3. `run_patcher.bat` (+15 lines, -1 line)
- Added environment variable exports: `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.
- Checks if `py -3` is available; runs `py -3 setup_latex_cpp.py %*`, otherwise falls back to `python setup_latex_cpp.py %*`.
- Captures `%errorlevel%` into `%EXITCODE%`, reports non-zero exit codes, and exits with `/b %EXITCODE%`.

#### 4. `setup_latex_cpp.py` (+80 lines, -14 lines)
- **Bootstrap enhancement**: If pip installation of any required library fails, appends to `failed_pkgs`, calls `importlib.invalidate_caches()`, displays manual recovery command, and exits with code 1 instead of continuing with missing imports.
- **CLI flag additions**: Added `--verify`.
- **Validation**: Added mutual exclusivity check between `--workshop-only` and `--coderunner-only`.
- **Flag normalization**: If `--workshop-only` or `--coderunner-only` is provided without `--vscode` or `--all`, automatically enables `args.vscode = True`.
- **Verification mode**: Executes `minted_patcher.verify_patch()`, prints formatted check items, and returns 0 or 1.
- **TUI handling**: Catches `KeyboardInterrupt` gracefully (returns 0), extracts integer exit code from `run_textual_tui()`.
- **Menu update**: Added option `[5]` to run `--verify` from the interactive terminal menu.

#### 5. `patcher_core/env_checker.py` (+72 lines)
- Implemented `find_all_miktex_roots() -> List[pathlib.Path]`:
  - Queries `kpsewhich -format=texmfscripts latexminted.py` to deduce root.
  - Runs `initexmf --report` to parse `UserData`, `UserInstall`, `UserConfig`, `CommonData`, `CommonInstall`, `Root*`.
  - Deduces root from `miktex_bin_dir`.
  - Scans standard Windows candidate directories (`%LOCALAPPDATA%\MiKTeX`, `%APPDATA%\MiKTeX`, `%ProgramData%\MiKTeX`, `%ProgramFiles%\MiKTeX`, `D:\Apps\MikTex`, `C:\Apps\MikTex`).

#### 6. `patcher_core/minted_patcher.py` (+251 lines, -87 lines)
- **Error handling**: Wrapped `CPP_LEXER_HOOK` to check `PALENIGHT_DEBUG` environment variable and print tracebacks to `sys.stderr` when enabled.
- **Safety checks**: Wrapped file copying into Pygments styles directory with try-except blocks; returns `False` on failure.
- **Multi-root MiKTeX support**: Iterates through all TEXMF roots returned by `env.find_all_miktex_roots()`.
- **Internal wheel safety**: When patching internal `pygments-*.whl` in MiKTeX `scripts/minted/`:
  - Keeps the original internal `c_cpp.py` of that wheel, only inserting hook lines into it if missing (avoiding version incompatibilities with the host Python's Pygments version).
  - Copies `palenight.py` and `palenight_ext/` into the wheel.
  - Creates `.whl.bak` before modification; writes to temporary `.whl.tmp` and renames atomically via `shutil.move`.
- **Safe workspace synchronization**: In `_offer_latex_template_sync`, if `auto_yes=True` and no `--workspace` was explicitly provided, skips workspace update instead of guessing or modifying the current directory.
- **Integrity verification**: Implemented `verify_patch() -> Tuple[bool, List[Tuple[bool, str]]]` checking:
  1. Pygments style `palenight` loading and style rule count.
  2. `CppLexer` hook activation and semantic parameter tokenization.
  3. Physical presence of hook in `pygments/lexers/c_cpp.py`.
  4. Presence of patched `pygments-*.whl` in MiKTeX roots.

#### 7. `patcher_core/ui.py` (+15 lines, -7 lines)
- Modified `_detect_default_latex_project(root_dir) -> Optional[pathlib.Path]`:
  - Strictly checks candidate paths against `root_dir` and its parents/children.
  - Checks if candidate contains `setup_latex_cpp.py` or `.git` directory and excludes it.
  - Returns `None` if no valid user project is found outside the repository, preventing the tool from ever mutating its own repository as a LaTeX workspace.

#### 8. `patcher_core/vscode_patcher.py` (+194 lines, -73 lines)
- **JSONC cleaner**: Implemented state-machine `clean_jsonc(text)`:
  - Tracks string literal state `in_string` and escape characters `\` to avoid stripping `//` inside URLs (e.g. `https://...`) or strings containing commas and brackets.
  - Strips `//` line comments and `/* */` block comments (preserving line breaks).
  - Removes trailing commas before `}` and `]`.
- **Merge logic**:
  - `_merge_tools`: merges tools into `latex-workshop.latex.tools` by tool `name`, updating existing tools while preserving any user-defined tools.
  - `_merge_recipes`: merges recipes into `latex-workshop.latex.recipes` by recipe `name`, preserving user-defined recipes.
- **Code Runner preservation**: Checks if `code-runner.executorMap.cpp` is customized by the user. If non-standard, preserves the user's custom command and prints an informational notice.
- **Timestamped backups**: In addition to `.json.bak`, creates `settings.json.bak.<YYYYMMDD_HHMMSS>`.
- **Workspace safety**: In `--yes` mode, skips workspace patching if `--workspace` is not provided.
- **Return status**: Returns boolean `patch_success`.

#### 9. `palenight_source/palenight_ext/patchers.py` (+12 lines, -4 lines)
- Replaced bare `except: pass` in `patch_cpp_lexer`, `patch_image_formatter`, and `patch_latex_formatter` with `_palenight_log_error` which logs exceptions when `PALENIGHT_DEBUG` is active.

#### 10. `palenight_source/palenight_ext/cpp_analyzer.py` (+317 lines, -46 lines)
- **Multiline macro continuation**: `_expand_macros` now checks for trailing `\` on lines ending with `\n`, allowing multi-line `#define` macros to be fully tokenized and parsed.
- **Macro bracket isolation**: Records macro ranges `macro_ranges` and resets/restores `depth` at macro boundary tokens, preventing unbalanced braces in `#define BEGIN {` from altering bracket colors in the rest of the file.
- **Punctuation normalization**: Separates multi-character punctuation containing brackets while preserving `::` scope operators.
- **Template vs comparison expression resolution**: In `is_inside_template_brackets`, evaluates binary operators (`&&`, `||`, `!`, `?`), number tokens following `>`, and parentheses nesting to prevent expressions like `f(a < b, c > d)` or `a < b && c > d` from being treated as template arguments.
- **Function body & qualifier scanner**: Implemented `find_body_open(pos)` which skips `const`, `noexcept`, `override`, `final`, `-> ReturnType`, and member initializer lists `: x{a}, y(b)` to locate the real function body `{`.
- **Lambda expressions**: Detects `[...] (...) { ... }` construct and maps lambda parameters to `NAME_PARAM`.
- **Constructor initializer lists**: Distinguishes member names in `: x{a}, y(b)` from functions, classifying them as `Name.Variable`.
- **Function prototype declarations**: Identifies parameters in declarations ending with `;` (e.g. `int compute(int val_a, double val_b);`) and marks them as `NAME_PARAM`.
- **Operator overloads**: Supports `operator<`, `operator()`, `operator[]` and tokens their parameters correctly.
- **Type aliases**: Collects `using T = ...` and `typedef ... T;` identifiers and highlights them as `Name.Builtin`.
- **Nested scope stack**: Replaced single `current_func_params` with `func_param_stack: list[tuple[int, set[str]]]` to handle nested blocks and lambda expressions.
- **Built-in preservation**: Bypasses `Name.Builtin` tokens (`true`, `false`, `nullptr`) from being misclassified as variables.

---

## 4. Baseline Test Suite Status

Command: `python -m pytest -v`  
Environment: Python 3.14.3, pytest-9.1.1, pluggy-1.7.0  
Root directory: `C:\Users\admin\Documents\antigravity\clever-salk`  

### Test Suite Execution Summary:
- Total tests collected: 12
- Passed: 12 (100%)
- Failed: 0
- Errors: 0
- Time: 0.16s

### Test Catalog:

| Test File | Test Class | Test Case | Target / Functionality | Baseline Result |
| :--- | :--- | :--- | :--- | :--- |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_builtins_true_false_nullptr` | Verifies `true`, `false`, `nullptr` retain built-in tokens and are not overridden to `Name.Variable` | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_constructor_init_list_with_braces` | Verifies member names in `: x{a}, y{b}` are `Name.Variable` and parameters are `NAME_PARAM` | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_function_prototype_parameters` | Verifies parameters in function prototypes ending with `;` are marked `NAME_PARAM` | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_lambda_parameters` | Verifies lambda expression parameters `[&](int x, int y)` are marked `NAME_PARAM` | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_multiline_macro_continuation` | Verifies multiline `#define` macros with `\` continuations are parsed with C++ token types | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_template_vs_comparison_ambiguity` | Verifies comparison `f(a < b, c > d)` is not confused with template brackets `vector<int>` | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_type_aliases_using_and_typedef` | Verifies `using` and `typedef` identifiers are highlighted as `Name.Builtin` | PASSED |
| `tests/test_cpp_highlighting.py` | `TestCppSemanticAnalyzer` | `test_unbalanced_brace_in_macro_isolation` | Verifies unbalanced `{` in `#define BEGIN {` does not shift outer rainbow bracket levels | PASSED |
| `tests/test_patchers.py` | `TestPatchersSafety` | `test_clean_jsonc_comments_and_trailing_commas` | Verifies `clean_jsonc` handles single/multiline comments, URLs with `//`, and strings with `,}` | PASSED |
| `tests/test_patchers.py` | `TestPatchersSafety` | `test_merge_recipes_preserves_custom_recipes` | Verifies merging `latex-workshop.latex.recipes` retains existing custom user recipes | PASSED |
| `tests/test_patchers.py` | `TestPatchersSafety` | `test_merge_tools_preserves_custom_tools` | Verifies merging `latex-workshop.latex.tools` retains existing custom user tools | PASSED |
| `tests/test_patchers.py` | `TestPatchersSafety` | `test_repo_directory_is_never_detected_as_user_project` | Verifies `_detect_default_latex_project` never selects the patcher repository or its parent | PASSED |

---

## 5. Release Archive Baseline (`setup_latex_cpp_release.zip`)

- **File Path**: `c:\Users\admin\Documents\antigravity\clever-salk\setup_latex_cpp_release.zip`
- **File Size**: **55,639 bytes**
- **SHA256**: `034023A9ECAD2C514656BF79948925E4F0188817E078E04A38AF9F7554A9D1E8`
- **Integrity Requirement**: This archive MUST remain byte-identical and unmodified throughout all review rounds.
- **Status relative to codebase**: The zip archive corresponds to the pre-modification state of the repository. Because the working tree contains ~1000 lines of uncommitted enhancements and fixes, this release zip is considered **outdated**. Per R5, this fact will be recorded in the final review report.

---

## 6. Recommendations & Focus Areas for Review Rounds

Based on the survey of modified code, here are specific recommendations for each of the upcoming 3 sequential review rounds:

### Round 1 — Correctness (Reviewer 1)
1. **CLI Flag Combinations**:
   - Test combinations of `--all`, `--minted`, `--vscode`, `--check`, `--verify`, `--workspace`, `-y` / `--yes`.
   - Verify exit codes: ensure errors return non-zero (1) and successes return 0.
   - Verify `--workshop-only` and `--coderunner-only` mutual exclusion behavior and ensure error messages are informative.
2. **Exception Handling & Crash Prevention**:
   - Inspect all places where subprocess calls, file reading/writing, or JSON parsing might fail (e.g. unhandled `FileNotFoundError`, `PermissionError`, or encoding errors).
   - Check `tui_app.py` import fallback when Textual is missing or fails to initialize.
3. **C++ Semantic Analyzer Edge Cases**:
   - Check complex C++ constructs: nested templates (e.g. `vector<map<int, vector<string>>>`), variadic templates, rvalue references (`&&`), lambda capture syntax (`[x = 1, &y]`), macro definitions without arguments, `#undef` without preceding `#define`.
   - Check token stream boundary conditions (empty string, code starting/ending with operators or preprocessor tokens).

### Round 2 — Safety of System Modifications (Reviewer 2)
1. **Backup Mechanics & Atomicity**:
   - Verify that backups (`.bak` and timestamped backups) are created *before* any file write operation.
   - Check behavior when `.bak` already exists.
   - Check write operations: verify whether temporary files (`.tmp`) with atomic rename (`shutil.move` / `os.replace`) are used everywhere or if any direct file overwrite exists.
2. **Idempotency**:
   - Test running the patcher multiple times consecutively on mock files:
     - Does running `clean_jsonc` or `_patch_settings_file` repeatedly create duplicate entries or redundant backup cascades?
     - Does patching `c_cpp.py` repeatedly add duplicate `CPP_LEXER_HOOK` blocks?
     - Does patching `latexminted.py` multiple times keep the block clean?
3. **Path Handling & Encodings**:
   - Check Windows path handling: backslashes vs forward slashes, spaces in directory paths (`Program Files`, `Documents and Settings`), drive letters.
   - Check UTF-8 encoding on all file operations (`encoding="utf-8"` with explicit `errors` parameter).
4. **JSONC Handling**:
   - Verify `clean_jsonc` handles complex JSONC edge cases: escaped quotes inside strings (`\"`), multi-line string contents, block comments inside strings, Windows CRLF line endings.
5. **Mocking & Isolation**:
   - Confirm all tests run strictly against mock directories (`tmp_path`) and never alter actual `%APPDATA%`, `D:\Apps`, or Python `site-packages`.

### Round 3 — Independent Holistic Review & Regression Check (Reviewer 3)
1. **Holistic Consistency**:
   - Cross-check all changes against the project specification and documentation in `README.md`.
   - Verify that fixes from Round 1 and Round 2 do not conflict or introduce secondary bugs.
2. **Regression Test Verification**:
   - Confirm every bug fixed in Rounds 1 & 2 has an accompanying pytest regression test that reproduces the defect on pre-fix code and confirms resolution on post-fix code.
   - Verify the full test suite (`python -m pytest`) passes cleanly.
3. **Safety Compliance Verification**:
   - Re-verify SHA256 of `setup_latex_cpp_release.zip` equals `034023A9ECAD2C514656BF79948925E4F0188817E078E04A38AF9F7554A9D1E8`.
   - Verify git status: no commits created.
   - Verify `REVIEW_REPORT.md` is compiled with all findings and regression test references.
