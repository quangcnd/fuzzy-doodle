"""Module phân tích ngữ nghĩa C++ & Rainbow Brackets độc lập, dễ tái sử dụng cho mọi style."""
from __future__ import annotations

import re
from pygments.token import (
    Keyword, Name, Comment, String, Whitespace, Punctuation, Number, Operator
)
from .config import BRACKET_LEVELS, NAME_PARAM
from .indent_rainbow import IndentRainbowProcessor


class CppSemanticAnalyzer:
    """Module phân tích cú pháp & ngữ cảnh C++ tự động (không phụ thuộc danh sách từ khóa cứng):
    - Tự động tách và học tên macro từ mọi dòng `#define` / `#undef` (kể cả macro nhiều dòng `\\`).
    - Cô lập độ sâu ngoặc (bracket depth) trong macro để tránh lệch màu rainbow brackets.
    - Nhận diện hàm `template`, phương thức `struct`/`class`, constructor `Node()`, lambda `[...] (...)`.
    - Phân biệt chính xác tham số prototype hàm và constructor init-list dạng `: x{1}, y(2)`.
    - Tránh nhập nhằng template trong biểu thức so sánh như `f(a < b, c > d)`.
    - Theo dõi phạm vi biến cục bộ và tham số theo từng tầng `{...}` (hỗ trợ nested functions / lambdas).
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
        macro_ranges = []  # list of (start_expanded_idx, end_expanded_idx)

        while i < m:
            idx, tok, val = raw_tokens[i]
            if tok is Comment.Preproc and val == '#' and i + 1 < m and raw_tokens[i + 1][1] is Comment.Preproc:
                full_line = val + raw_tokens[i + 1][2]
                j = i + 2
                while j < m and raw_tokens[j][1] is Comment.Preproc:
                    full_line += raw_tokens[j][2]
                    if raw_tokens[j][2] == '\n':
                        line_before = full_line[:-1].rstrip(' \t\r')
                        if not line_before.endswith('\\'):
                            j += 1
                            break
                    j += 1

                match = cls.DEFINE_RE.match(full_line)
                if match:
                    d_kw, ws1, m_name, m_args, m_body = match.groups()
                    defined_macros.add(m_name)

                    m_start = len(expanded)
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

                    m_end = len(expanded)
                    macro_ranges.append((m_start, m_end))
                    i = j
                    continue

                umatch = cls.UNDEF_RE.match(full_line)
                if umatch:
                    u_kw, ws1, m_name, rest = umatch.groups()
                    defined_macros.discard(m_name)
                    type_macros.discard(m_name)
                    m_start = len(expanded)
                    cur = idx
                    expanded.append((cur, Comment.Preproc, u_kw))
                    cur += len(u_kw)
                    expanded.append((cur, Whitespace, ws1))
                    cur += len(ws1)
                    expanded.append((cur, Name.Function, m_name))
                    cur += len(m_name)
                    if rest:
                        expanded.append((cur, Comment.Preproc, rest))
                    m_end = len(expanded)
                    macro_ranges.append((m_start, m_end))
                    i = j
                    continue

            expanded.append((idx, tok, val))
            i += 1
        return expanded, macro_ranges

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
        raw_tokens, macro_ranges = cls._expand_macros(lexer, cfamily_cls, raw_tokens, defined_macros, type_macros)
        raw_tokens = cls._split_char_escapes(raw_tokens)

        # Tách Punctuation ghép liền và gập '::'
        tokens = []
        skip_next = False
        for i, (idx, tok, val) in enumerate(raw_tokens):
            if skip_next:
                skip_next = False
                continue

            if tok is Punctuation and val == ':' and i + 1 < len(raw_tokens):
                next_tok, next_val = raw_tokens[i + 1][1], raw_tokens[i + 1][2]
                if next_tok is Punctuation and next_val == ':':
                    tokens.append((idx, Punctuation, '::'))
                    skip_next = True
                    continue

            if tok is Punctuation and len(val) > 1 and any(c in cls.OPEN_BRACKETS or c in cls.CLOSE_BRACKETS for c in val):
                cur_off = idx
                for char in val:
                    tokens.append((cur_off, Punctuation, char))
                    cur_off += len(char)
            else:
                tokens.append((idx, tok, val))

        n = len(tokens)
        depth = 0
        shadowed_locals_by_depth = {}
        # func_param_stack: list of (brace_depth, set_of_param_names)
        func_param_stack: list[tuple[int, set[str]]] = []

        macro_starts = {start: end for start, end in macro_ranges}
        macro_ends = {end: start for start, end in macro_ranges}
        saved_macro_depth: int | None = None

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
                if tv in (';', '{', '}'):
                    break
                if tv in ('|', '!', '?') or (tv == '&' and k >= 1 and tokens[k - 1][2] == '&'):
                    return False  # `a < b && c > d` là so sánh, không phải template
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

                        # Kiểm tra xem có đang nằm trong biểu thức ngoặc tròn `(...)` như `f(a < b, c > d)`
                        p_enc = before_lt - 1
                        enc_d = 0
                        is_in_paren_expr = False
                        while p_enc >= 0:
                            t_enc = tokens[p_enc][2]
                            if t_enc == ')':
                                enc_d += 1
                            elif t_enc == '(':
                                if enc_d > 0:
                                    enc_d -= 1
                                else:
                                    is_in_paren_expr = True
                                    break
                            elif t_enc in (';', '{', '}'):
                                break
                            p_enc -= 1

                        fwd_balance = 0
                        m_idx = pos + 1
                        while m_idx < n:
                            mtv = tokens[m_idx][2]
                            if mtv in (';', '{', '}', '|', '!', '?'):
                                return False
                            if mtv == '&' and m_idx + 1 < n and tokens[m_idx + 1][2] == '&':
                                return False
                            if mtv == '<':
                                fwd_balance += 1
                            elif mtv == '>':
                                if fwd_balance > 0:
                                    fwd_balance -= 1
                                else:
                                    nx_m = next_non_ws(m_idx)
                                    if nx_m < n:
                                        if tokens[nx_m][1] in Number:
                                            return False  # `b > 0`
                                        if is_in_paren_expr:
                                            # Trong biểu thức `(...)`, sau `>` phải là `(`, `{`, `::`, `*`, `&`, `>`
                                            if tokens[nx_m][2] not in ('(', '{', '::', '>', '*', '&'):
                                                return False
                                    return True
                            m_idx += 1
                        return False
                k -= 1
            return False

        QUALIFIERS = {'const', 'noexcept', 'override', 'final', 'volatile', 'mutable', '&'}

        def find_body_open(pos):
            """Từ token ngay sau ')' của một khai báo: bỏ qua `const noexcept override final &`,
            `-> T` và init-list `: a(x), b{y}`. Trả về (index của '{', [index các member init-list])
            hoặc (None, []) nếu đó không phải định nghĩa hàm."""
            k = pos
            prev_sig = None
            while k < n:
                tk, v = tokens[k][1], tokens[k][2]
                if tk in Whitespace:
                    k += 1
                    continue
                if v == '{':
                    return k, []
                if v in QUALIFIERS:
                    prev_sig = v
                    k += 1
                    continue
                if v == '(' and prev_sig == 'noexcept':
                    d, k = 1, k + 1
                    while k < n and d:
                        d += (tokens[k][2] == '(') - (tokens[k][2] == ')')
                        k += 1
                    prev_sig = ')'
                    continue
                if v == '-' and k + 1 < n and tokens[k + 1][2] == '>':
                    k += 2
                    while k < n and tokens[k][2] not in ('{', ';'):
                        k += 1
                    return (k, []) if k < n and tokens[k][2] == '{' else (None, [])
                if v == ':':
                    members, d, last_name = [], 0, None
                    k += 1
                    while k < n:
                        tk2, v2 = tokens[k][1], tokens[k][2]
                        if tk2 in Whitespace:
                            k += 1
                            continue
                        if d == 0 and v2 == ';':
                            return None, []
                        if d == 0 and v2 == '{' and last_name is None:
                            return k, members
                        if v2 in ('(', '[', '{'):
                            if d == 0 and v2 in ('(', '{') and last_name is not None:
                                members.append(last_name)
                            d += 1
                            if d == 1:
                                last_name = None
                        elif v2 in (')', ']', '}'):
                            d -= 1
                        elif d == 0:
                            if tk2 in Name:
                                last_name = k
                            elif v2 != ',':
                                last_name = None
                        k += 1
                    return None, []
                k += 1
            return None, []

        def get_active_params():
            active = set()
            for _, pset in func_param_stack:
                active.update(pset)
            return active

        # Thu thập typedef và using type alias
        type_aliases = set()
        for idx_a, (_, tok_a, val_a) in enumerate(tokens):
            if tok_a is Keyword and val_a == 'using':
                n1 = next_non_ws(idx_a)
                n2 = next_non_ws(n1) if n1 < n else n
                if n2 < n and tokens[n1][1] in Name and tokens[n2][2] == '=':
                    type_aliases.add(tokens[n1][2])
            elif tok_a is Keyword and val_a == 'typedef':
                k_a, last_name = idx_a + 1, None
                while k_a < n and tokens[k_a][2] != ';':
                    if tokens[k_a][2] == '{':
                        last_name = None
                        break
                    if tokens[k_a][1] in Name:
                        last_name = tokens[k_a][2]
                    k_a += 1
                if last_name:
                    type_aliases.add(last_name)

        init_members = set()

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
            # Cô lập bracket depth cho macro `#define`
            if i in macro_starts:
                saved_macro_depth = depth
            if i in macro_ends and saved_macro_depth is not None:
                depth = saved_macro_depth
                saved_macro_depth = None

            idx, tok, val = tokens[i]

            if tok in Punctuation:
                if val in cls.OPEN_BRACKETS:
                    # Nhận diện lambda expression: `[...] (...) { ... }`
                    if val == '[':
                        prev_k = prev_non_ws(i)
                        is_subscript = False
                        if prev_k >= 0:
                            ptk, pv = tokens[prev_k][1], tokens[prev_k][2]
                            if ptk in Name or pv in (']', ')'):
                                is_subscript = True
                        if not is_subscript:
                            cap_close = i + 1
                            c_depth = 1
                            while cap_close < n and c_depth > 0:
                                if tokens[cap_close][2] == '[':
                                    c_depth += 1
                                elif tokens[cap_close][2] == ']':
                                    c_depth -= 1
                                cap_close += 1
                            cap_close_idx = cap_close - 1
                            if cap_close_idx < n and tokens[cap_close_idx][2] == ']':
                                after_cap = next_non_ws(cap_close_idx)
                                if after_cap < n and tokens[after_cap][2] == '(':
                                    p_d, e = 1, after_cap + 1
                                    while e < n and p_d > 0:
                                        p_d += (tokens[e][2] == '(') - (tokens[e][2] == ')')
                                        e += 1
                                    body_open, _ = find_body_open(e)
                                    if body_open is not None:
                                        lambda_params = set()
                                        for pp in range(after_cap + 1, e - 1):
                                            if tokens[pp][1] in Name:
                                                nx = next_non_ws(pp)
                                                if nx < n and tokens[nx][2] in (',', ')', '=', '['):
                                                    tokens[pp] = (tokens[pp][0], NAME_PARAM, tokens[pp][2])
                                                    lambda_params.add(tokens[pp][2])
                                                elif tokens[pp][2] in type_macros or tokens[pp][2] in type_aliases:
                                                    tokens[pp] = (tokens[pp][0], Name.Builtin, tokens[pp][2])
                                                else:
                                                    tokens[pp] = (tokens[pp][0], Name.Class, tokens[pp][2])
                                        func_param_stack.append((depth + 1, lambda_params))

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
                    if val == '}':
                        while func_param_stack and depth < func_param_stack[-1][0]:
                            func_param_stack.pop()
                    continue

            if val == 'operator' and (tok is Keyword or tok in Name):
                # `bool operator<(const P &o) const {` -> tô tham số như một hàm bình thường
                q = next_non_ws(i)
                if q < n and tokens[q][2] in ('(', '['):
                    q = next_non_ws(next_non_ws(q))  # operator() / operator[]
                else:
                    while q < n and tokens[q][1] in Operator:
                        q = next_non_ws(q)
                if q < n and tokens[q][2] == '(':
                    pd, e = 1, q + 1
                    while e < n and pd > 0:
                        pd += (tokens[e][2] == '(') - (tokens[e][2] == ')')
                        e += 1
                    body_open, _ = find_body_open(e)
                    op_params = set()
                    for pp in range(q + 1, e - 1):
                        if tokens[pp][1] in Name:
                            nx = next_non_ws(pp)
                            if nx < n and tokens[nx][2] in (',', ')', '=', '['):
                                tokens[pp] = (tokens[pp][0], NAME_PARAM, tokens[pp][2])
                                op_params.add(tokens[pp][2])
                            elif tokens[pp][2] in type_macros or tokens[pp][2] in type_aliases:
                                tokens[pp] = (tokens[pp][0], Name.Builtin, tokens[pp][2])
                            else:
                                tokens[pp] = (tokens[pp][0], Name.Class, tokens[pp][2])
                    if body_open is not None:
                        func_param_stack.append((depth + 1, op_params))
                continue

            if tok in Name:
                if tok in Name.Builtin:  # true / false / nullptr: giữ màu của Pygments
                    continue
                if i in init_members:  # `: x(x), y{y}` -> member là biến, không phải hàm
                    tokens[i] = (idx, Name.Variable, val)
                    continue

                j = next_non_ws(i)
                next_tok = tokens[j][1] if j < n else None
                next_val = tokens[j][2] if j < n else ''

                k = prev_non_ws(i)
                prev_tok = tokens[k][1] if k >= 0 else None
                prev_val = tokens[k][2] if k >= 0 else ''

                if next_val == '(':
                    p = j + 1
                    p_depth = 1
                    while p < n and p_depth > 0:
                        if tokens[p][2] == '(':
                            p_depth += 1
                        elif tokens[p][2] == ')':
                            p_depth -= 1
                        p += 1
                    close_idx = p - 1
                    body_open, ctor_members = find_body_open(close_idx + 1)
                    is_func_def = (
                        body_open is not None
                        and prev_val not in ('=', 'return', '.', '->')
                    )

                    # Kiểm tra xem có phải prototype declaration: `int f(int a, int b);`
                    is_prototype = False
                    if not is_func_def:
                        chk = close_idx + 1
                        while chk < n and (tokens[chk][1] in Whitespace or tokens[chk][2] in QUALIFIERS):
                            chk += 1
                        if chk < n and tokens[chk][2] == ';':
                            if prev_tok in (Keyword.Type, Name.Class, Name.Builtin) or prev_val in ('*', '&', '>') or prev_val in type_aliases or prev_val in type_macros:
                                is_prototype = True

                    if is_func_def or is_prototype:
                        tokens[i] = (idx, Name.Class if val in defined_classes else Name.Function, val)
                        if is_func_def:
                            init_members.update(ctor_members)
                        params_set = set()
                        p_cur = j + 1
                        while p_cur < close_idx:
                            if tokens[p_cur][1] in Name:
                                nx = next_non_ws(p_cur)
                                if nx < n and tokens[nx][2] in (',', ')', '=', '['):
                                    tokens[p_cur] = (tokens[p_cur][0], NAME_PARAM, tokens[p_cur][2])
                                    params_set.add(tokens[p_cur][2])
                                elif tokens[p_cur][2] in type_macros or tokens[p_cur][2] in type_aliases:
                                    tokens[p_cur] = (tokens[p_cur][0], Name.Builtin, tokens[p_cur][2])
                                else:
                                    tokens[p_cur] = (tokens[p_cur][0], Name.Class, tokens[p_cur][2])
                            p_cur += 1
                        if is_func_def:
                            func_param_stack.append((depth + 1, params_set))
                        continue

                if tok is Name.Function or tok is NAME_PARAM or tok is Name.Class:
                    continue

                active_params = get_active_params()

                if func_param_stack and (
                    prev_tok in (Keyword.Type, Name.Class, Name.Builtin)
                    or prev_val in ('*', '&')
                    or (prev_val == '>' and k >= 1 and is_inside_template_brackets(k - 1))
                    or (prev_val in type_macros)
                ):
                    shadowed_locals_by_depth.setdefault(depth, set()).add(val)

                is_shadowed_local = any(val in s for s in shadowed_locals_by_depth.values())

                if val in type_aliases:
                    tokens[i] = (idx, Name.Builtin, val)
                    continue

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
                        fp = next_non_ws(j)
                        if fp < n and (tokens[fp][1] is Keyword.Type or tokens[fp][2] == 'const'):
                            is_var_init = False  # `int f(int a);` / `int f(const T&)` là khai báo hàm

                    if is_var_init:
                        tokens[i] = (idx, Name.Variable, val)
                    else:
                        tokens[i] = (idx, Name.Function, val)
                elif prev_val == '::':
                    tokens[i] = (idx, Name.Function if next_val == '(' else Name.Class, val)
                elif prev_val in ('.', '->'):
                    tokens[i] = (idx, Name.Attribute, val)
                elif val in active_params and not is_shadowed_local:
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
