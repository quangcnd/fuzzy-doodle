# Project: Setup LaTeX C++ Patcher 3-Round Review & Hardening

## Overview
Automated patcher tool (Textual TUI + CLI menu + non-interactive flags) for Minted/Pygments C++ semantic highlighting, Palenight theme, LaTeX template files, and VS Code settings.
Task: Conduct 3 sequential review rounds with independent reviewers, fix defects, ensure strict environment safety, write pytest regression tests for every fix (failing on pre-fix, passing on post-fix), and generate `REVIEW_REPORT.md`.

## Constraints & Safety Rules
1. Never modify real machine state: NO touching real site-packages/Pygments, MiKTeX, or real VS Code settings/extensions.
2. No pip install other than pytest.
3. All tests must use temporary directories and/or mocks.
4. Do NOT modify `setup_latex_cpp_release.zip` (must remain byte-identical: SHA256 034023A9ECAD2C514656BF79948925E4F0188817E078E04A38AF9F7554A9D1E8).
5. Do NOT git commit or push; leave changes in working tree.
6. 3 sequential rounds with distinct, independent reviewers:
   - Round 1: Correctness (Reviewer 1)
   - Round 2: Safety of system modifications (Reviewer 2)
   - Round 3: Independent holistic review + regression check (Reviewer 3)
7. Fix policy: Fix every real defect (bug, crash, data loss, incorrect behaviour). No stylistic refactoring.
8. Each fixed bug must have a pytest regression test verifying it failed pre-fix and passes post-fix.
9. Full test suite (`python -m pytest`) must pass at the end of each round and upon completion.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Test Baseline | Map git diff, codebase, existing tests baseline | None | DONE |
| M1 | Round 1: Correctness | Reviewer 1 review, bug fixes, regression tests, verification | M0 | DONE |
| M2 | Round 2: Safety | Reviewer 2 review, safety fixes, regression tests, verification | M1 | DONE |
| M3 | Round 3: Holistic & Regression | Reviewer 3 full review, fix verification, regression tests | M2 | DONE |
| M4 | Final Report & Acceptance | Assemble REVIEW_REPORT.md, full pytest suite run, safety check | M3 | DONE |
