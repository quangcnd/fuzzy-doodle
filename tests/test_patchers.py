"""Bộ ca kiểm thử tự động cho VSCodePatcher, JSONC Cleaner và các quy tắc an toàn."""
from __future__ import annotations

import json
import pathlib
import unittest

from patcher_core.vscode_patcher import clean_jsonc, VSCodePatcher, LATEX_WORKSHOP_TOOLS, LATEX_WORKSHOP_RECIPES
from patcher_core.ui import _detect_default_latex_project, ROOT_DIR


class TestPatchersSafety(unittest.TestCase):
    def test_clean_jsonc_comments_and_trailing_commas(self):
        jsonc_sample = """
        {
            // Đây là comment dòng đơn
            "name": "test",
            "url": "https://example.com/api?a=1&b=2", // Comment sau URL có chứa //
            /* Đây là comment
               nhiều dòng */
            "items": [
                "a, } b", // Chuỗi có chứa dấu phẩy và ngoặc nhọn
                "c",
            ],
            "nested": {
                "val": 123,
            },
        }
        """
        cleaned = clean_jsonc(jsonc_sample)
        data = json.loads(cleaned)

        self.assertEqual(data["name"], "test")
        self.assertEqual(data["url"], "https://example.com/api?a=1&b=2")
        self.assertEqual(data["items"], ["a, } b", "c"])
        self.assertEqual(data["nested"]["val"], 123)

    def test_merge_tools_preserves_custom_tools(self):
        custom_tool = {
            "name": "custom_lualatex",
            "command": "lualatex",
            "args": ["-shell-escape", "%DOC%"],
            "env": {},
        }
        existing_tools = [custom_tool]

        merged = VSCodePatcher._merge_tools(existing_tools)

        # Công cụ custom của người dùng phải được giữ nguyên
        tool_names = [t["name"] for t in merged]
        self.assertIn("custom_lualatex", tool_names)
        self.assertIn("xelatex", tool_names)
        self.assertIn("latexmk (xelatex)", tool_names)
        self.assertIn("pdflatex", tool_names)

    def test_merge_recipes_preserves_custom_recipes(self):
        custom_recipe = {
            "name": "my_custom_pipeline",
            "tools": ["custom_lualatex", "biber"],
        }
        existing_recipes = [custom_recipe]

        merged = VSCodePatcher._merge_recipes(existing_recipes)

        recipe_names = [r["name"] for r in merged]
        self.assertIn("my_custom_pipeline", recipe_names)
        self.assertIn("xelatex", recipe_names)
        self.assertIn("latexmk (xelatex)", recipe_names)
        self.assertIn("pdflatex", recipe_names)

    def test_repo_directory_is_never_detected_as_user_project(self):
        # Kiểm tra _detect_default_latex_project tuyệt đối không trả về chính ROOT_DIR
        detected = _detect_default_latex_project(ROOT_DIR)
        if detected is not None:
            self.assertNotEqual(detected.resolve(), ROOT_DIR.resolve())
            self.assertFalse(ROOT_DIR in detected.resolve().parents)
            self.assertFalse(detected.resolve() in ROOT_DIR.resolve().parents)


if __name__ == "__main__":
    unittest.main()
