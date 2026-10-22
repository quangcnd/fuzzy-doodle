# Công Cụ Tự Động Cài Đặt & Patch Minted/Pygments C++ / LaTeX & VS Code

Bộ công cụ tích hợp giao diện **TUI (Textual)** giúp tự động kiểm tra các phần mềm nền tảng còn thiếu, tự động cài đặt thư viện Python & gói LaTeX (MiKTeX), đồng thời tùy chọn patch **Minted / Pygments / LaTeX** (tô màu C++ Semantic, Rainbow Brackets, Indent-Rainbow chuẩn VS Code Palenight) và cấu hình **VS Code** (`LaTeX Workshop` + `Code Runner`).

---

## Hướng dẫn sử dụng (HDSD)

### Cách 1: Chạy bằng Giao diện TUI tương tác (Khuyên dùng)
Nhấp đúp chuột vào file **`run_patcher.bat`** hoặc mở Terminal tại thư mục này và chạy:

```powershell
python setup_latex_cpp.py
```

Khi khởi chạy lần đầu, chương trình sẽ **tự động kiểm tra và cài đặt các thư viện cần thiết** (`textual`, `pygments`, `pillow`, `latexminted`), sau đó mở giao diện TUI dạng danh sách đánh dấu:

```text
  [v] Kiểm tra phần mềm thiếu & Tự động cài thư viện Python (pip) + LaTeX (MiKTeX)
  [v] Patch Minted / Pygments / LaTeX (C++ Semantic, Rainbow Brackets, Indent-Rainbow, MiKTeX)
  [v] Cập nhật mẫu lib/codebox.tex vào Project LaTeX & Xóa cache _minted cũ
  [v] Patch VS Code: LaTeX Workshop (Đặt xelatex -shell-escape làm mặc định)
  [v] Patch VS Code: Code Runner (Tối ưu nút Run cho C++17 & LaTeX)
❯ [ ] Tự động cài đặt VS Code Extensions còn thiếu (LaTeX Workshop, Code Runner)
```

**Thao tác điều khiển trong TUI:**
- **Phím `↑` / `↓` hoặc Chuột**: Di chuyển giữa các mục.
- **Phím `Space` hoặc Click chuột vào mục**: Bật / tắt dấu chọn `[ ]` ↔ `[v]`.
- **Phím `A`**: Chọn tất cả / Bỏ chọn tất cả.
- **Phím `Enter` (hoặc bấm nút `▶ Thực thi`)**: Chạy toàn bộ các mục đã đánh dấu `[v]` và xem kết quả trực tiếp ở khung Log bên dưới.
- **Phím `Q` hoặc `Esc`**: Thoát chương trình.

---

### Cách 2: Chạy nhanh bằng dòng lệnh (CLI không cần mở TUI)

```powershell
# Chỉ kiểm tra phần mềm thiếu & tự cài thư viện Python / MiKTeX
python setup_latex_cpp.py --check

# Patch toàn bộ tự động (không hỏi xác nhận)
python setup_latex_cpp.py --all --yes

# Chỉ patch Minted / Pygments / LaTeX
python setup_latex_cpp.py --minted --yes

# Chỉ patch VS Code (cả LaTeX Workshop + Code Runner)
python setup_latex_cpp.py --vscode --yes

# Chỉ patch riêng LaTeX Workshop hoặc riêng Code Runner
python setup_latex_cpp.py --vscode --workshop-only --yes
python setup_latex_cpp.py --vscode --coderunner-only --yes
```
