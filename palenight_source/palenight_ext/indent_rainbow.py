"""Module xử lý hiệu ứng thụt lề 4 cấp độ (plugin VS Code `indent-rainbow`) có thể bật/tắt."""
import os
from pygments.token import Whitespace
from .config import PalenightConfig, INDENT_LEVELS


class IndentRainbowProcessor:
    """Module độc lập chịu trách nhiệm phân tách khoảng trắng đầu dòng thành các cột
    mang token `INDENT_1..INDENT_4` và nội suy cho các dòng trống nằm giữa khối code.
    Hỗ trợ bật/tắt linh hoạt qua:
      1. Tham số lexer/formatter: `-O indent_rainbow=false` (hoặc `true`, `0`, `1`, `off`, `on`)
      2. Biến môi trường: `PALENIGHT_INDENT_RAINBOW=0`
      3. Hàm Python: `IndentRainbowProcessor.set_enabled(False)`
      4. Thuộc tính cấu hình: `PalenightConfig.ENABLE_INDENT_RAINBOW = False`
    """

    @classmethod
    def set_enabled(cls, enabled: bool):
        """Bật hoặc tắt tính năng indent-rainbow bằng code Python."""
        PalenightConfig.ENABLE_INDENT_RAINBOW = bool(enabled)

    @classmethod
    def is_enabled(cls, override=None) -> bool:
        """Kiểm tra trạng thái bật/tắt hiện tại của indent-rainbow."""
        if override is not None:
            if isinstance(override, bool):
                return override
            s = str(override).strip().lower()
            if s in ("0", "false", "no", "off", "none", "disable", "disabled"):
                return False
            if s in ("1", "true", "yes", "on", "enable", "enabled"):
                return True

        env_val = os.environ.get("PALENIGHT_INDENT_RAINBOW")
        if env_val is not None:
            s = env_val.strip().lower()
            if s in ("0", "false", "no", "off"):
                return False
            if s in ("1", "true", "yes", "on"):
                return True

        return bool(PalenightConfig.ENABLE_INDENT_RAINBOW)

    @classmethod
    def process(cls, tokens, tab_width=None, enabled=None):
        if not cls.is_enabled(enabled):
            return tokens
        if tab_width is None:
            tab_width = PalenightConfig.TAB_WIDTH

        # Bước 0: Tách mọi token có chứa '\n' ở giữa (như Comment.Multiline /* ... */)
        flat_tokens = []
        for idx, tok, val in tokens:
            if '\n' in val and len(val) > 1:
                offset = 0
                for part in val.splitlines(True):
                    flat_tokens.append((idx + offset, tok, part))
                    offset += len(part)
            else:
                flat_tokens.append((idx, tok, val))

        # Bước 1: Gom token theo từng dòng
        lines = []
        cur_line = []
        for item in flat_tokens:
            cur_line.append(item)
            if item[2].endswith('\n'):
                lines.append(cur_line)
                cur_line = []
        if cur_line:
            lines.append(cur_line)

        # Bước 2: Tính số space đầu dòng của từng dòng có code
        line_indents = []
        line_is_blank = []
        for line in lines:
            full_str = ''.join(val for _, _, val in line)
            stripped = full_str.rstrip('\r\n')
            if stripped.strip() == '':
                line_is_blank.append(True)
                line_indents.append(0)
            else:
                line_is_blank.append(False)
                if line[0][1] in Whitespace:
                    expanded = stripped.expandtabs(tab_width)
                    lead_len = len(expanded) - len(expanded.lstrip(' '))
                    line_indents.append(lead_len)
                else:
                    line_indents.append(0)

        # Bước 3: Nội suy mức thụt lề cho các dòng trống nằm giữa hàm/struct
        num_lines = len(lines)
        for ln in range(num_lines):
            if line_is_blank[ln]:
                prev_indent = 0
                for p in range(ln - 1, -1, -1):
                    if not line_is_blank[p]:
                        prev_indent = line_indents[p]
                        break
                next_indent = 0
                inferred = 0
                for q in range(ln + 1, num_lines):
                    if not line_is_blank[q]:
                        next_indent = line_indents[q]
                        first_code = ''.join(v for _, _, v in lines[q]).lstrip()
                        if first_code.startswith('}'):
                            inferred = prev_indent
                        else:
                            inferred = min(prev_indent, next_indent) if (prev_indent and next_indent) else max(prev_indent, next_indent)
                        break
                line_indents[ln] = (inferred // tab_width) * tab_width

        # Bước 4: Phát lại danh sách token với các cột thụt lề INDENT_1..INDENT_4
        result = []
        for ln, line in enumerate(lines):
            if line_is_blank[ln]:
                target_spaces = line_indents[ln]
                base_idx = line[0][0]
                nl_str = ''.join(val for _, _, val in line)
                nl_only = '\n' if nl_str.endswith('\n') else ''
                col = 0
                while col < target_spaces:
                    step = min(tab_width, target_spaces - col)
                    lvl_tok = INDENT_LEVELS[(col // tab_width) % 4]
                    result.append((base_idx + col, lvl_tok, ' ' * step))
                    col += step
                if nl_only:
                    result.append((base_idx + target_spaces, Whitespace, nl_only))
                continue

            at_line_start = True
            col = 0
            for idx, tok, val in line:
                if at_line_start and tok in Whitespace and val not in ('\n', '\r\n'):
                    raw_ws = val.rstrip('\r\n')
                    nl_tail = val[len(raw_ws):]
                    expanded = raw_ws.expandtabs(tab_width)
                    pos = 0
                    while pos < len(expanded):
                        if expanded[pos] == ' ':
                            rem_in_tab = tab_width - (col % tab_width)
                            end_pos = min(pos + rem_in_tab, len(expanded))
                            chunk = expanded[pos:end_pos]
                            lvl_tok = INDENT_LEVELS[(col // tab_width) % 4]
                            result.append((idx + pos, lvl_tok, chunk))
                            col += len(chunk)
                            pos = end_pos
                        else:
                            result.append((idx + pos, Whitespace, expanded[pos:]))
                            break
                    if nl_tail:
                        result.append((idx + len(raw_ws), Whitespace, nl_tail))
                else:
                    if tok not in Whitespace or val != '':
                        at_line_start = False
                    result.append((idx, tok, val))

        return result
