# Dispatch to worker_r1

Role: Round 1 Fix Worker
Working Directory: c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\worker_r1\
Task: Resolve the 10 REAL DEFECTS identified in Round 1 and implement corresponding pytest regression tests in `tests/test_r1_correctness.py`.

Review Report: `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\reviewer_r1_gen2\review_r1.md`

Defects to fix:
1. DEFECT-01: In `patcher_core/minted_patcher.py:302`, import `Token` from `pygments.token` or use safe token type check so no `NameError` occurs.
2. DEFECT-02: In `palenight_source/palenight_ext/patchers.py:253`, change `rf'\def\{cp}@bc##1{{'` to `rf'\def\{cp}@{tname}##1{{'`.
3. DEFECT-03: In `patcher_core/minted_patcher.py:344-347`, add `all_passed = False` inside `if not found_whl:`.
4. DEFECT-04: In `setup_latex_cpp.py:73`, remove top-level call to `bootstrap_self_dependencies()`. Call it inside `main()` or inside `if __name__ == "__main__":` before `main()`.
5. DEFECT-05: In `patcher_core/env_checker.py:476-482`, have `run_all_checks()` return a boolean indicating success of checks, and update `setup_latex_cpp.py` so `--check` sets `success = checks_ok` and returns 1 if critical checks fail.
6. DEFECT-06: In `palenight_source/palenight_ext/cpp_analyzer.py:502`, add `or prev_val == '>'` to include function prototypes returning template types.
7. DEFECT-07: In `palenight_source/palenight_ext/cpp_analyzer.py:533`, pass `k - 1` instead of `k` to `is_inside_template_brackets(k - 1)`.
8. DEFECT-08: In `palenight_source/palenight_ext/cpp_analyzer.py:532`, add `or prev_val in ('*', '&')` to support local pointer and reference declarations.
9. DEFECT-09: In `patcher_core/vscode_patcher.py:124-130`, ensure `clean_jsonc()` properly removes trailing commas even when followed by single-line `//` or multi-line `/* */` comments before `}` or `]`.
10. DEFECT-10: In `patcher_core/vscode_patcher.py:284-290`, ensure `run_patch()` does not return `True` when zero target settings files are found or modified.

Requirements:
- DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
- Create regression tests in `tests/test_r1_correctness.py` covering all 10 fixes.
- Run `python -m pytest` to verify all existing tests (12 tests) and new regression tests pass.
- Never touch real system state (site-packages, MiKTeX, VS Code settings). Mocks and temp directories only.
- Never touch setup_latex_cpp_release.zip.
- Never git commit or push.
- Produce `changes.md` and `handoff.md` in your working directory.
- Send completion message to orchestrator.

## 2026-10-23T03:21:58Z
You are worker_r1. Your working directory is `c:\Users\admin\Documents\antigravity\clever-salk\.agents\teamwork\worker_r1\`.

Fix all 10 REAL DEFECTS identified by reviewer_r1_gen2 and implement comprehensive pytest regression tests in `tests/test_r1_correctness.py`.
