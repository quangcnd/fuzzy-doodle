# Original User Request

## 2026-10-23T02:49:01Z

Requested by the user: "Tiến hành 3 vòng kiểm tra bằng 3 subagent khác nhau và nếu như phát hiện ra lỗi thì sửa rồi mới qua vòng tiếp theo" — i.e. run 3 sequential review rounds, each performed by a different, independent reviewer agent; any bugs found in a round must be fixed and verified before the next round starts.

The subject is the `setup_latex_cpp` patcher in the working directory: a Python tool (Textual TUI + CLI menu + non-interactive flags) that checks/installs prerequisites (Python libs, MiKTeX), patches Minted/Pygments for C++ semantic highlighting / rainbow brackets / indent-rainbow (Palenight theme), updates LaTeX template files, and patches VS Code settings (LaTeX Workshop, Code Runner).

Working directory: c:\Users\admin\Documents\antigravity\clever-salk
Integrity mode: development

## Requirements

### R1. Review scope
Review the whole repository, prioritising the ~1000 lines of uncommitted changes (`git diff` against HEAD) in `patcher_core/`, `palenight_source/`, `setup_latex_cpp.py`, `run_patcher.bat`, and `README.md`.

### R2. Three sequential rounds, distinct reviewers, distinct focus
Each round is performed by a different reviewer agent that did not author fixes in earlier rounds:
- **Round 1 — Correctness:** logic errors, crashes/unhandled exceptions, wrong CLI flag behaviour, broken imports, incorrect C++ highlighting/analyzer behaviour.
- **Round 2 — Safety of system modifications:** backups before writing, idempotency (running a patch twice must not corrupt or duplicate), ability to restore/undo, partial-failure handling, Windows paths, UTF-8/encoding, JSON(C) settings handling for VS Code.
- **Round 3 — Independent holistic review + regression check:** fresh full review, including verifying that fixes from rounds 1–2 are correct and did not introduce new defects.

A round may only start after all bugs from the previous round are fixed and verified.

### R3. Fix policy
Fix every real defect (bug, crash, data loss, incorrect behaviour). Do not refactor or make stylistic changes; minor/subjective issues are only recorded in the report.

### R4. Environment safety (hard constraint)
Never touch the real machine state: do not run real patches against the installed Pygments/site-packages, MiKTeX, or real VS Code settings/extensions; do not `pip install` anything other than `pytest`. All tests must use temporary directories and/or mocks. Do not modify `setup_latex_cpp_release.zip`.

### R5. Git & reporting
Do not commit or push; leave all changes in the working tree. Produce `REVIEW_REPORT.md` in the working directory listing, per round: reviewer focus, each finding (file:line, severity, description), whether it was fixed or only reported, and the regression test covering each fix. Note in the report that the release zip is now outdated.

## Acceptance Criteria

### Process
- [ ] Exactly 3 rounds are executed in order, each by a distinct reviewer agent, with the focus defined in R2.
- [ ] No round starts while a confirmed bug from the previous round remains unfixed.

### Verification of fixes
- [ ] Every fixed bug has at least one pytest regression test that fails on the pre-fix code and passes after the fix (demonstrated, e.g. by running it against the stashed/original version).
- [ ] The full test suite (`python -m pytest`) passes at the end of each round and at the end of the project.
- [ ] Existing tests in `tests/` still pass (or, if a test was itself wrong, the change is justified in the report).

### Safety
- [ ] No files outside the working directory and temp directories are modified (no changes to site-packages, MiKTeX, VS Code user settings/extensions).
- [ ] `setup_latex_cpp_release.zip` is byte-identical to its original; no git commits were created.

### Report
- [ ] `REVIEW_REPORT.md` exists and contains all three rounds with findings, severities, fix status, and linked tests as described in R5.
