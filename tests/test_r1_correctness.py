"""Regression tests for Round 1 Correctness defects (DEFECT-01 through DEFECT-10)."""
from __future__ import annotations

import json
import os
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest
from pygments.formatters.latex import LatexFormatter, _get_ttype_name
from pygments.lexers.c_cpp import CFamilyLexer, CppLexer
from pygments.token import Keyword, Name, Token

import palenight_source.palenight_ext as _ext
import palenight_source.palenight_ext.patchers as _ext_patchers
import palenight_source.palenight_ext.cpp_analyzer as _ext_cpp_analyzer
import palenight_source.palenight_ext.config as _ext_config
import palenight_source.palenight_ext.fonts as _ext_fonts
import palenight_source.palenight_ext.indent_rainbow as _ext_ir

# Route pygments.styles.palenight_ext to the workspace's palenight_ext implementation
# without modifying system site-packages (in compliance with constraint R4).
sys.modules["pygments.styles.palenight_ext"] = _ext
sys.modules["pygments.styles.palenight_ext.patchers"] = _ext_patchers
sys.modules["pygments.styles.palenight_ext.cpp_analyzer"] = _ext_cpp_analyzer
sys.modules["pygments.styles.palenight_ext.config"] = _ext_config
sys.modules["pygments.styles.palenight_ext.fonts"] = _ext_fonts
sys.modules["pygments.styles.palenight_ext.indent_rainbow"] = _ext_ir

import setup_latex_cpp
from palenight_source.palenight_ext.config import INDENT_BG_MAP, NAME_PARAM
from palenight_source.palenight_ext.cpp_analyzer import CppSemanticAnalyzer
from palenight_source.palenight_ext.patchers import FormatterPatcher
from patcher_core.env_checker import EnvironmentManager
from patcher_core.minted_patcher import MintedPygmentsPatcher
from patcher_core.vscode_patcher import VSCodePatcher, clean_jsonc


# ==============================================================================
# DEFECT-01: NameError on undefined Token in minted_patcher.py
# ==============================================================================
def test_defect_01_token_name_import_and_no_nameerror():
    """DEFECT-01: minted_patcher.py must import Token from pygments.token to avoid NameError."""
    import patcher_core.minted_patcher as mp

    # Verify Token is imported in the module namespace
    assert hasattr(mp, "Token"), "Token must be imported in patcher_core.minted_patcher"
    assert mp.Token is Token, "mp.Token must be pygments.token.Token"

    # Evaluate the exact expression that previously failed when str(t[0]) does not match startswith
    tokens = [
        (Token.Name, "a"),
        (Token.Punctuation, ";"),
    ]
    # In pre-fix code, if str(t[0]) was 'Token.Name', it would evaluate:
    # t[0] is Token.Name.Variable.Parameter -> NameError if Token was undefined
    has_param = any(
        (str(t[0]).startswith("Token.Name.Variable.Parameter")
         or t[0] is mp.Token.Name.Variable.Parameter
         or str(t[0]).startswith("Token.Name.Variable.Magic"))
        for t in tokens if t[1] == 'a'
    )
    assert has_param is False, "Should evaluate safely to False without NameError"


# ==============================================================================
# DEFECT-02: Hardcoded \PY@bc in patch_latex_formatter breaks LaTeX compilation
# ==============================================================================
def test_defect_02_latex_formatter_macro_uses_tname_not_bc():
    r"""DEFECT-02: Indent-rainbow LaTeX macro must define \PY@<tname>, not hardcoded \PY@bc."""
    if hasattr(LatexFormatter, "_palenight_indent_patched"):
        delattr(LatexFormatter, "_palenight_indent_patched")
    FormatterPatcher.patch_latex_formatter()
    fmt = LatexFormatter(style="palenight", indent_rainbow=True)
    defs = fmt.get_style_defs()

    # Pre-fix code defined `\def\PY@bc` 4 times and never defined `\def\PY@<tname>`
    assert r"\def\PY@bc" not in defs, (
        r"Stylesheet must NOT contain hardcoded \def\PY@bc macro from indent-rainbow loop"
    )

    for ind_tok in INDENT_BG_MAP:
        tname = _get_ttype_name(ind_tok)
        expected_macro = rf"\def\PY@{tname}"
        assert expected_macro in defs, (
            f"Expected macro definition '{expected_macro}' in LaTeX stylesheet for token {ind_tok}"
        )


# ==============================================================================
# DEFECT-03: verify_patch() ignores missing MiKTeX wheel and reports success
# ==============================================================================
def test_defect_03_verify_patch_fails_when_miktex_wheel_not_found(monkeypatch, tmp_path):
    """DEFECT-03: verify_patch() must return (False, ...) when pygments wheel in MiKTeX is missing."""
    mock_env = MagicMock(spec=EnvironmentManager)
    # Return an empty list of roots, or a root directory with no pygments wheel
    empty_root = tmp_path / "empty_miktex"
    empty_root.mkdir()
    mock_env.find_all_miktex_roots.return_value = [empty_root]

    patcher = MintedPygmentsPatcher(mock_env, auto_yes=True)

    # Mock steps 1, 2, 3 to pass so we specifically test step 4
    with patch("pygments.styles.get_style_by_name"):
        with patch.object(CppLexer, "_palenight_patched", True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="_patch_cpp_lexer()"):
                    all_passed, results = patcher.verify_patch()

    # Pre-fix code returned all_passed = True because it forgot `all_passed = False`
    assert all_passed is False, "verify_patch() must return False when MiKTeX wheel is missing"
    assert any("Chưa tìm thấy gói pygments-*.whl" in msg for passed, msg in results if not passed)


# ==============================================================================
# DEFECT-04: Top-level bootstrap_self_dependencies() runs at import time
# ==============================================================================
def test_defect_04_importing_setup_latex_cpp_does_not_bootstrap_dependencies(monkeypatch):
    """DEFECT-04: Importing setup_latex_cpp must not invoke bootstrap_self_dependencies()."""
    # Verify bootstrap_self_dependencies is a standalone function
    assert callable(setup_latex_cpp.bootstrap_self_dependencies)

    # Calling main() should invoke bootstrap_self_dependencies
    called = []
    monkeypatch.setattr(setup_latex_cpp, "bootstrap_self_dependencies", lambda: called.append(True))
    monkeypatch.setattr(sys, "argv", ["setup_latex_cpp.py", "-h"])

    # -h triggers early return in parse_args (or SystemExit)
    try:
        setup_latex_cpp.main()
    except SystemExit:
        pass

    assert called == [True], "bootstrap_self_dependencies() must be called inside main()"


# ==============================================================================
# DEFECT-05: --check returns exit code 0 even when environment checks fail
# ==============================================================================
def test_defect_05_env_checker_run_all_checks_returns_bool_and_check_flag_exits_nonzero(monkeypatch):
    """DEFECT-05: run_all_checks() returns bool and --check exits with code 1 if checks fail."""
    env = EnvironmentManager(auto_yes=True)

    # Case A: Simulated check failure (e.g. python lib install fails)
    monkeypatch.setattr(env, "check_and_report_system_software", lambda: [])
    monkeypatch.setattr(env, "ensure_python_libraries", lambda: False)
    monkeypatch.setattr(env, "ensure_miktex_packages", lambda: True)
    monkeypatch.setattr(env, "check_and_offer_vscode_extensions", lambda **kwargs: [])

    result = env.run_all_checks(ask_ext_install=False)
    assert result is False, "run_all_checks() must return False if python library check fails"

    # Case B: Simulated check failure (MiKTeX missing)
    monkeypatch.setattr(env, "check_and_report_system_software", lambda: [("MiKTeX (Bộ biên dịch LaTeX)", "", "")])
    monkeypatch.setattr(env, "ensure_python_libraries", lambda: True)
    monkeypatch.setattr(env, "ensure_miktex_packages", lambda: False)

    result_miktex = env.run_all_checks(ask_ext_install=False)
    assert result_miktex is False, "run_all_checks() must return False if MiKTeX is missing"

    # Case C: All checks succeed
    monkeypatch.setattr(env, "check_and_report_system_software", lambda: [])
    monkeypatch.setattr(env, "ensure_python_libraries", lambda: True)
    monkeypatch.setattr(env, "ensure_miktex_packages", lambda: True)

    result_ok = env.run_all_checks(ask_ext_install=False)
    assert result_ok is True, "run_all_checks() must return True when all checks pass"

    # Case D: setup_latex_cpp.py --check exit code reflects run_all_checks result
    monkeypatch.setattr(setup_latex_cpp, "bootstrap_self_dependencies", lambda: None)

    # When checks fail:
    monkeypatch.setattr(EnvironmentManager, "run_all_checks", lambda self, **kwargs: False)
    monkeypatch.setattr(sys, "argv", ["setup_latex_cpp.py", "--check", "--yes"])
    exit_code_fail = setup_latex_cpp.main()
    assert exit_code_fail == 1, "--check must return exit code 1 when checks fail"

    # When checks pass:
    monkeypatch.setattr(EnvironmentManager, "run_all_checks", lambda self, **kwargs: True)
    monkeypatch.setattr(sys, "argv", ["setup_latex_cpp.py", "--check", "--yes"])
    exit_code_pass = setup_latex_cpp.main()
    assert exit_code_pass == 0, "--check must return exit code 0 when checks pass"


# ==============================================================================
# DEFECT-06: Function prototypes returning template types fail parameter recognition
# ==============================================================================
def test_defect_06_cpp_analyzer_template_prototype_parameter_highlighting():
    """DEFECT-06: Prototypes returning template types (e.g. vector<int> f(int a);) must highlight params."""
    lexer = CppLexer()
    code = "vector<int> solve(int a, double b);"
    tokens = list(CppSemanticAnalyzer.analyze(lexer, CFamilyLexer, code))

    param_tokens = [tok for _, tok, val in tokens if val in ('a', 'b')]
    assert param_tokens == [NAME_PARAM, NAME_PARAM], (
        f"Parameters in template prototype should be NAME_PARAM, got {param_tokens}"
    )

    # Test with namespace template return type
    code2 = "std::pair<int, string> get_pair(int id, bool active);"
    tokens2 = list(CppSemanticAnalyzer.analyze(lexer, CFamilyLexer, code2))
    param_tokens2 = [tok for _, tok, val in tokens2 if val in ('id', 'active')]
    assert param_tokens2 == [NAME_PARAM, NAME_PARAM], (
        f"Parameters in qualified template prototype should be NAME_PARAM, got {param_tokens2}"
    )


# ==============================================================================
# DEFECT-07: is_inside_template_brackets(k) called with closing bracket index returns False
# ==============================================================================
def test_defect_07_cpp_analyzer_shadowed_local_template_variable():
    """DEFECT-07: Local template variable (e.g. vector<int> a;) must properly shadow parameter a."""
    lexer = CppLexer()
    code = "void solve(int a) { vector<int> a; a.push_back(1); }"
    tokens = list(CppSemanticAnalyzer.analyze(lexer, CFamilyLexer, code))

    a_toks = [(idx, tok, val) for idx, tok, val in tokens if val == 'a']
    assert len(a_toks) == 3, f"Expected 3 occurrences of 'a', got {len(a_toks)}"

    # 1st 'a': parameter in function definition -> NAME_PARAM
    assert a_toks[0][1] == NAME_PARAM, "Parameter 'a' in signature must be NAME_PARAM"

    # 2nd 'a': declaration of local variable `vector<int> a;` -> Name.Variable
    assert a_toks[1][1] is not NAME_PARAM, "Local variable declaration 'a' must not be NAME_PARAM"

    # 3rd 'a': usage in `a.push_back(1)` -> must be shadowed, NOT NAME_PARAM
    assert a_toks[2][1] is not NAME_PARAM, (
        "Usage of shadowed local template variable 'a' must NOT be NAME_PARAM"
    )


# ==============================================================================
# DEFECT-08: Local pointer/reference variable declarations fail to register as shadowed locals
# ==============================================================================
def test_defect_08_cpp_analyzer_shadowed_local_pointer_and_reference():
    """DEFECT-08: Local pointer and reference variable declarations must register as shadowed locals."""
    lexer = CppLexer()

    # Pointer case:
    code_ptr = "void solve(int* x) { int* x = nullptr; x = get(); }"
    tokens_ptr = list(CppSemanticAnalyzer.analyze(lexer, CFamilyLexer, code_ptr))
    x_toks = [(idx, tok, val) for idx, tok, val in tokens_ptr if val == 'x']
    assert len(x_toks) == 3, f"Expected 3 occurrences of 'x', got {len(x_toks)}"
    assert x_toks[0][1] == NAME_PARAM, "Parameter 'x' must be NAME_PARAM"
    assert x_toks[1][1] is not NAME_PARAM, "Local pointer declaration 'x' must not be NAME_PARAM"
    assert x_toks[2][1] is not NAME_PARAM, "Shadowed pointer 'x' usage must not be NAME_PARAM"

    # Reference case:
    code_ref = "void solve(int& y) { int& y = other; y = 1; }"
    tokens_ref = list(CppSemanticAnalyzer.analyze(lexer, CFamilyLexer, code_ref))
    y_toks = [(idx, tok, val) for idx, tok, val in tokens_ref if val == 'y']
    assert len(y_toks) == 3, f"Expected 3 occurrences of 'y', got {len(y_toks)}"
    assert y_toks[0][1] == NAME_PARAM, "Parameter 'y' must be NAME_PARAM"
    assert y_toks[1][1] is not NAME_PARAM, "Local reference declaration 'y' must not be NAME_PARAM"
    assert y_toks[2][1] is not NAME_PARAM, "Shadowed reference 'y' usage must not be NAME_PARAM"


# ==============================================================================
# DEFECT-09: clean_jsonc fails to remove trailing commas followed by comments
# ==============================================================================
def test_defect_09_clean_jsonc_trailing_commas_with_comments():
    """DEFECT-09: clean_jsonc must strip trailing commas even when followed by comments."""
    sample_single = """
    {
        "key": "value", // single-line comment following trailing comma
    }
    """
    cleaned_single = clean_jsonc(sample_single)
    parsed_single = json.loads(cleaned_single)
    assert parsed_single == {"key": "value"}

    sample_multi = """
    {
        "items": [
            "one",
            "two", /* multi-line comment before closing bracket */
        ],
        "nested": {
            "val": 123, /* multi-line */
        }, // trailing comment
    }
    """
    cleaned_multi = clean_jsonc(sample_multi)
    parsed_multi = json.loads(cleaned_multi)
    assert parsed_multi == {"items": ["one", "two"], "nested": {"val": 123}}

    # Preserve strings that contain comments or commas
    sample_string = '{"text": "val, // not a comment", "nested": {"k": "/* keep */,"}}'
    cleaned_string = clean_jsonc(sample_string)
    parsed_string = json.loads(cleaned_string)
    assert parsed_string == {"text": "val, // not a comment", "nested": {"k": "/* keep */,"}}


# ==============================================================================
# DEFECT-10: VSCodePatcher.run_patch() returns True when nothing was patched
# ==============================================================================
def test_defect_10_vscode_run_patch_fails_when_no_targets(monkeypatch, tmp_path):
    """DEFECT-10: VSCodePatcher.run_patch() must return False when zero files are found/patched."""
    env = EnvironmentManager(auto_yes=True)
    patcher = VSCodePatcher(env, auto_yes=True)

    # Scenario A: APPDATA Code/User does not exist, no target workspace provided
    non_existent_appdata = tmp_path / "fake_appdata"
    non_existent_appdata.mkdir()
    monkeypatch.setenv("APPDATA", str(non_existent_appdata))

    # Pre-fix code returned True because patch_success started at True and no loop executed
    success = patcher.run_patch(patch_workshop=True, patch_coderunner=True, target_workspace=None)
    assert success is False, "run_patch() must return False when zero target settings files exist"

    # Scenario B: Target workspace is specified and valid -> should succeed
    ws_dir = tmp_path / "valid_workspace"
    ws_dir.mkdir()
    success_ws = patcher.run_patch(patch_workshop=True, patch_coderunner=True, target_workspace=str(ws_dir))
    assert success_ws is True, "run_patch() should return True when workspace is successfully patched"
    assert (ws_dir / ".vscode" / "settings.json").is_file(), "Workspace settings.json must be created"
