"""Module phân tích ngữ nghĩa C++ & Rainbow Brackets độc lập, dễ tái sử dụng cho mọi style."""
import re
from pygments.token import (
    Keyword, Name, Comment, String, Whitespace, Punctuation
)
from .config import BRACKET_LEVELS, NAME_PARAM
from .indent_rainbow import IndentRainbowProcessor


class CppSemanticAnalyzer:
    """Module phân tích cú pháp & ngữ cảnh C++ tự động (không phụ thuộc danh sách từ khóa cứng):
    - Tự động tách và học tên macro từ mọi dòng `#define` / `#undef`.
    - Nhận diện hàm `template`, phương thức `struct`/`class`, constructor `Node()`.
    - Theo dõi phạm vi biến cục bộ theo từng tầng `{...}` để xử lý variable shadowing.
    - Nhận diện kiểu bên trong `<...>`, hằng macro in hoa (`INT_MAX`), ký tự thoát `'\n'`.
    - Tô màu Rainbow Brackets 3 cấp độ và gọi `IndentRainbowProcessor`.
    """

    OPEN_BRACKETS = {'(', '[', '{'}
    CLOSE_BRACKETS = {')', ']', '}'}
    DEFINE_RE = re.compile(r'^(\s*#\s*define\b)(\s+)([A-Za-z_]\w*)(\([^)]*\))?(.*)$', re.DOTALL)
    UNDEF_RE = re.compile(r'^(\s*#\s*undef\b)(\s+)([A-Za-z_]\w*)(.*)$', re.DOTALL)
    UPPER_MACRO_CONST_RE = re.compile(r'^[A-Z][A-Z0-9]*_[A-Z0-9_]+$')

    @classmethod
    def _is_macro_param_styled_as_param(cls, param_name, m_body):
        if not m_body:
            return True
        if re.search(rf'\(\s*{re.escape(param_name)}\s*\)\s*\.|\b{re.escape(param_name)}\s*\.', m_body):
            return False
        return True

    @classmethod
    def _expand_macros(cls, lexer, cfamily_cls, raw_tokens, defined_macros, type_macros):
        expanded = []
        i = 0
        m = len(raw_tokens)
        while i < m:
            idx, tok, val = raw_tokens[i]
            if tok is Comment.Preproc and val == '#' and i + 1 < m and raw_tokens[i + 1][1] is Comment.Preproc:
                full_line = val + raw_tokens[i + 1][2]
                j = i + 2
                while j < m and raw_tokens[j][1] is Comment.Preproc and raw_tokens[j][2] != '\n':
                    full_line += raw_tokens[j][2]
                    j += 1

                match = cls.DEFINE_RE.match(full_line)
                if match:
                    d_kw, ws1, m_name, m_args, m_body = match.groups()
                    defined_macros.add(m_name)

                    cur = idx
                    expanded.append((cur, Comment.Preproc, d_kw))
                    cur += len(d_kw)
                    expanded.append((cur, Whitespace, ws1))
                    cur += len(ws1)
                    expanded.append((cur, Name.Function, m_name))
                    cur += len(m_name)

                    param_style_map = {}
                    if m_args:
                        for sub_off, sub_tok, sub_val in cfamily_cls.get_tokens_unprocessed(lexer, m_args, ('statement',)):
                            if sub_tok in Name:
                                use_param_color = cls._is_macro_param_styled_as_param(sub_val, m_body)
                                param_style_map[sub_val] = NAME_PARAM if use_param_color else Name.Variable
                                sub_tok = param_style_map[sub_val]
                            expanded.append((cur + sub_off, sub_tok, sub_val))
                        cur += len(m_args)

                    if m_body:
                        body_tokens = list(cfamily_cls.get_tokens_unprocessed(lexer, m_body, ('root', 'function')))
                        non_ws_body = [bt for bt in body_tokens if bt[1] not in Whitespace]
                        if not m_args and non_ws_body:
                            if all(bt[1] is Keyword.Type for bt in non_ws_body) or (
                                any(bt[2] == '<' for bt in non_ws_body) and non_ws_body[-1][2] == '>'
                            ):
                                type_macros.add(m_name)

                        is_single_ident_alias = (
                            len(non_ws_body) == 1
                            and non_ws_body[0][1] is Name
                            and (m_name.startswith('_') or non_ws_body[0][2].startswith('_'))
                        )
                        for sub_off, sub_tok, sub_val in body_tokens:
                            if sub_tok in Name:
                                if sub_val in param_style_map:
                                    sub_tok = param_style_map[sub_val]
                                elif is_single_ident_alias:
                                    sub_tok = Name.Function
                            expanded.append((cur + sub_off, sub_tok, sub_val))

                    i = j
                    continue

                umatch = cls.UNDEF_RE.match(full_line)
                if umatch:
                    u_kw, ws1, m_name, rest = umatch.groups()
                    defined_macros.discard(m_name)
                    type_macros.discard(m_name)
                    cur = idx
                    expanded.append((cur, Comment.Preproc, u_kw))
                    cur += len(u_kw)
                    expanded.append((cur, Whitespace, ws1))
                    cur += len(ws1)
                    expanded.append((cur, Name.Function, m_name))
                    cur += len(m_name)
                    if rest:
                        expanded.append((cur, Comment.Preproc, rest))
                    i = j
                    continue

            expanded.append((idx, tok, val))
            i += 1
        return expanded

    @staticmethod
    def _split_char_escapes(raw_tokens):
        out = []
        for idx, tok, val in raw_tokens:
            if tok is String.Char and len(val) >= 2 and val.startswith('\\'):
                out.append((idx, String.Escape, val))
            else:
                out.append((idx, tok, val))
        return out

    @classmethod
    def analyze(cls, lexer, cfamily_cls, text, stack=('root',)):
        raw_tokens = list(cfamily_cls.get_tokens_unprocessed(lexer, text, stack))

        defined_macros = set()
        type_macros = set()
        raw_tokens = cls._expand_macros(lexer, cfamily_cls, raw_tokens, defined_macros, type_macros)
        raw_tokens = cls._split_char_escapes(raw_tokens)

        # Tách Punctuation ghép liền và gộp '::'
        tokens = []
        for idx, tok, val in raw_tokens:
            if tok in Punctuation and len(val) > 1:
                for offset, ch in enumerate(val):
                    tokens.append((idx + offset, tok, ch))
            else:
                tokens.append((idx, tok, val))

        merged_tokens = []
        idx_t = 0
        while idx_t < len(tokens):
            if (idx_t + 1 < len(tokens)
                    and tokens[idx_t][2] == ':'
                    and tokens[idx_t + 1][2] == ':'):
                merged_tokens.append((tokens[idx_t][0], Punctuation, '::'))
                idx_t += 2
            else:
                merged_tokens.append(tokens[idx_t])
                idx_t += 1
        tokens = merged_tokens

        n = len(tokens)
        depth = 0
        current_func_params = set()
        shadowed_locals_by_depth = {}
        func_brace_depth = None

        def prev_non_ws(pos):
            k = pos - 1
            while k >= 0 and tokens[k][1] in Whitespace:
                k -= 1
            return k

        def next_non_ws(pos):
            k = pos + 1
            while k < n and tokens[k][1] in Whitespace:
                k += 1
            return k

        def is_inside_template_brackets(pos):
            angle_balance = 0
            k = pos - 1
            while k >= 0:
                tk, tv = tokens[k][1], tokens[k][2]
                if tv in (';', '{', '}', '(', ')'):
                    break
                if tv == '>':
                    angle_balance += 1
                elif tv == '<':
                    if angle_balance > 0:
                        angle_balance -= 1
                    else:
                        after_lt = next_non_ws(k)
                        if after_lt < n and tokens[after_lt][2] in ('class', 'typename'):
                            return False
                        before_lt = prev_non_ws(k)
                        if before_lt < 0:
                            return False
                        btok = tokens[before_lt][1]
                        if not (btok in Name or btok in Keyword):
                            return False
                        fwd_balance = 0
                        m_idx = pos + 1
                        while m_idx < n:
                            mtv = tokens[m_idx][2]
                            if mtv in (';', '{', '}', '(', ')'):
                                return False
                            if mtv == '<':
                                fwd_balance += 1
                            elif mtv == '>':
                                if fwd_balance > 0:
                                    fwd_balance -= 1
                                else:
                                    return True
                            m_idx += 1
                        return False
                k -= 1
            return False

        # Thu thập struct / class / enum / union được định nghĩa trong file
        defined_classes = set()
        for idx_c, (_, tok_c, val_c) in enumerate(tokens):
            if tok_c is Name.Class:
                defined_classes.add(val_c)
            elif tok_c is Keyword and val_c in ('struct', 'class', 'enum', 'union'):
                nx_c = next_non_ws(idx_c)
                if nx_c < n and tokens[nx_c][1] in Name:
                    defined_classes.add(tokens[nx_c][2])

        # Quét ngữ cảnh
        for i in range(n):
            idx, tok, val = tokens[i]

            if tok in Punctuation:
                if val in cls.OPEN_BRACKETS:
                    b_tok = BRACKET_LEVELS[depth % 3]
                    tokens[i] = (idx, b_tok, val)
                    depth += 1
                    continue
                elif val in cls.CLOSE_BRACKETS:
                    if val == '}' and depth in shadowed_locals_by_depth:
                        del shadowed_locals_by_depth[depth]
                    depth = max(0, depth - 1)
                    b_tok = BRACKET_LEVELS[depth % 3]
                    tokens[i] = (idx, b_tok, val)
                    if val == '}' and func_brace_depth is not None and depth < func_brace_depth:
                        current_func_params.clear()
                        shadowed_locals_by_depth.clear()
                        func_brace_depth = None
                    continue

            if tok in Name:
                j = next_non_ws(i)
                next_tok = tokens[j][1] if j < n else None
                next_val = tokens[j][2] if j < n else ''

                k = prev_non_ws(i)
                prev_tok = tokens[k][1] if k >= 0 else None
                prev_val = tokens[k][2] if k >= 0 else ''

                # 1. Kiểm tra định nghĩa hàm / phương thức / constructor
                if next_val == '(':
                    p = j + 1
                    p_depth = 1
                    while p < n and p_depth > 0:
                        if tokens[p][2] == '(':
                            p_depth += 1
                        elif tokens[p][2] == ')':
                            p_depth -= 1
                        p += 1
                    after_paren = next_non_ws(p - 1) if p <= n else n
                    is_func_def = (
                        after_paren < n
                        and tokens[after_paren][2] == '{'
                        and prev_val not in ('=', 'return', '.', '->')
                    )
                else:
                    is_func_def = False

                if is_func_def:
                    tokens[i] = (idx, Name.Class if val in defined_classes else Name.Function, val)
                    current_func_params.clear()
                    shadowed_locals_by_depth.clear()
                    func_brace_depth = depth + 1
                    p = j + 1
                    while p < after_paren - 1:
                        if tokens[p][1] in Name:
                            nx = next_non_ws(p)
                            if nx < n and tokens[nx][2] in (',', ')', '=', '['):
                                tokens[p] = (tokens[p][0], NAME_PARAM, tokens[p][2])
                                current_func_params.add(tokens[p][2])
                            elif tokens[p][2] in type_macros:
                                tokens[p] = (tokens[p][0], Name.Builtin, tokens[p][2])
                            else:
                                tokens[p] = (tokens[p][0], Name.Class, tokens[p][2])
                        p += 1
                    continue

                if tok is Name.Function or tok is NAME_PARAM or tok is Name.Class:
                    continue

                if func_brace_depth is not None and (
                    prev_tok in (Keyword.Type, Name.Class, Name.Builtin)
                    or (prev_val == '>' and is_inside_template_brackets(k))
                    or (prev_val in type_macros)
                ):
                    shadowed_locals_by_depth.setdefault(depth, set()).add(val)

                is_shadowed_local = any(val in s for s in shadowed_locals_by_depth.values())

                if val in defined_classes:
                    tokens[i] = (idx, Name.Class, val)
                    continue

                if val in defined_macros:
                    if val in type_macros or is_inside_template_brackets(i) or (
                        next_tok in Name and (prev_tok is Keyword or prev_val in ('{', ';', '}', '(', ','))
                    ):
                        tokens[i] = (idx, Name.Builtin, val)
                    else:
                        tokens[i] = (idx, Name.Function, val)
                    continue

                if cls.UPPER_MACRO_CONST_RE.match(val) or val in ('EOF', 'NULL'):
                    tokens[i] = (idx, Name.Function, val)
                    continue

                if val.startswith('__'):
                    tokens[i] = (idx, Name.Function, val)
                elif prev_val in ('{', ';', '}') and next_val == ';':
                    tokens[i] = (idx, Name.Function, val)
                elif prev_val == ',' and next_val == ')' and val.startswith('std'):
                    tokens[i] = (idx, NAME_PARAM, val)
                elif next_val == '(':
                    is_var_init = False
                    if prev_tok in (Keyword.Type, Name.Class, Name.Builtin) and prev_val not in cls.CLOSE_BRACKETS:
                        is_var_init = True
                    elif prev_val == '>':
                        if k >= 1 and is_inside_template_brackets(k - 1):
                            is_var_init = True
                    elif prev_tok is Name.Function and prev_val in defined_macros and k >= 1 and tokens[prev_non_ws(k)][2] in ('{', ';', '}'):
                        is_var_init = True

                    if is_var_init:
                        tokens[i] = (idx, Name.Variable, val)
                    else:
                        tokens[i] = (idx, Name.Function, val)
                elif prev_val == '::':
                    tokens[i] = (idx, Name.Function if next_val == '(' else Name.Class, val)
                elif prev_val in ('.', '->'):
                    tokens[i] = (idx, Name.Attribute, val)
                elif val in current_func_params and not is_shadowed_local:
                    tokens[i] = (idx, NAME_PARAM, val)
                elif next_tok in Name and (
                    prev_tok is Keyword or prev_val in ('{', ';', '}', '(', ',')
                ):
                    tokens[i] = (idx, Name.Builtin, val)
                elif is_inside_template_brackets(i):
                    tokens[i] = (idx, Name.Builtin, val)
                else:
                    tokens[i] = (idx, Name.Variable, val)

        override_ir = getattr(lexer, "_indent_rainbow_opt", None)
        return IndentRainbowProcessor.process(tokens, enabled=override_ir)
