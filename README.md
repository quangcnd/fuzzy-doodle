# Công Cụ Tự Động Cài Đặt & Patch Minted/Pygments C++ / LaTeX & VS Code

Bộ công cụ tích hợp giao diện **TUI (Textual)** và **CLI Menu** giúp tự động kiểm tra các phần mềm nền tảng còn thiếu, tự động cài đặt thư viện Python & gói LaTeX (MiKTeX), đồng thời tùy chọn patch **Minted / Pygments / LaTeX** (tô màu C++ Semantic, Rainbow Brackets, Indent-Rainbow chuẩn VS Code Palenight) và cấu hình **VS Code** (`LaTeX Workshop` + `Code Runner`).

---

## Hướng dẫn sử dụng (HDSD)

### Cách 1: Chạy bằng file thực thi nhanh (Khuyên dùng trên Windows)
Nhấp đúp chuột vào file **`run_patcher.bat`** hoặc mở Terminal tại thư mục này và chạy:

```powershell
python setup_latex_cpp.py
```
*(Nếu trên máy có Python Launcher, script sẽ tự động dùng `py -3` và kích hoạt chế độ UTF-8 đầy đủ).*

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

### Cách 2: Chạy bằng Menu văn bản cổ điển (Terminal CLI)
Nếu môi trường không hỗ trợ hiển thị TUI hoặc bạn thích giao diện console truyền thống:

```powershell
python setup_latex_cpp.py --cli-menu
```

---

### Cách 3: Chạy nhanh bằng dòng lệnh (Non-interactive mode)

```powershell
# Kiểm tra tính toàn vẹn của hệ thống sau khi patch hoặc nâng cấp Pygments/MiKTeX
python setup_latex_cpp.py --verify

# Chỉ kiểm tra phần mềm thiếu & tự cài thư viện Python / MiKTeX
python setup_latex_cpp.py --check

# Patch toàn bộ tự động
python setup_latex_cpp.py --all --yes

# Chỉ định rõ thư mục Project LaTeX cần cập nhật lib/codebox.tex và .vscode/settings.json
python setup_latex_cpp.py --all --workspace "D:\Project\Latex" --yes

# Chỉ patch Minted / Pygments / LaTeX (MiKTeX)
python setup_latex_cpp.py --minted --yes

# Chỉ patch VS Code (cả LaTeX Workshop + Code Runner)
python setup_latex_cpp.py --vscode --yes

# Chỉ patch riêng LaTeX Workshop hoặc riêng Code Runner
python setup_latex_cpp.py --workshop-only --yes
python setup_latex_cpp.py --coderunner-only --yes
```

---

## Danh sách cờ dòng lệnh (CLI Flags)

| Tham số | Ý nghĩa |
| :--- | :--- |
| `--tui` | Bắt buộc mở giao diện TUI Textual (Mặc định khi không truyền tham số). |
| `--cli-menu` | Mở menu lựa chọn tương tác cổ điển trên Terminal. |
| `--verify` | Kiểm tra toàn diện tính toàn vẹn của Pygments hook, MiKTeX và cấu hình hệ thống. |
| `--all` | Chạy thẳng quy trình: Kiểm tra môi trường + Patch Minted/LaTeX + Patch VS Code. |
| `--minted` | Chạy thẳng quy trình patch Minted/Pygments/LaTeX (không sửa VS Code). |
| `--vscode` | Chạy thẳng quy trình patch cấu hình VS Code (LaTeX Workshop / Code Runner). |
| `--workshop-only` | Khi dùng với `--vscode`: chỉ cập nhật công cụ và recipes của LaTeX Workshop. |
| `--coderunner-only` | Khi dùng với `--vscode`: chỉ cập nhật executor C++17 và LaTeX của Code Runner. |
| `--check` | Chỉ kiểm tra phần mềm thiếu và cài đặt thư viện Python / gói MiKTeX còn thiếu. |
| `--workspace <PATH>` | Chỉ định thư mục Project LaTeX đích cần đồng bộ `lib/codebox.tex` và `.vscode/settings.json`. |
| `-y`, `--yes` | Chế độ tự động xác nhận toàn bộ câu hỏi (Non-interactive mode). |

---

## Các lưu ý quan trọng khi sử dụng

1. **Monkeypatch toàn cục lên Pygments `CppLexer`**:
   - Khi patch, bộ phân tích ngữ nghĩa sẽ gài một hook toàn cục vào lớp `CppLexer` của Pygments trên máy.
   - Bất kỳ công cụ Python nào khác trên cùng môi trường sử dụng Pygments (ví dụ: lệnh `pygmentize`, `Sphinx`, `Jupyter Notebook`) khi tô màu code C++ đều sẽ được hưởng cơ chế tô màu ngữ nghĩa này.

2. **Khi nâng cấp Pygments hoặc MiKTeX**:
   - Nếu bạn chạy `pip install -U pygments` hoặc MiKTeX tự động cập nhật gói `minted` / file `.whl`, các file đã patch có thể bị khôi phục về bản gốc.
   - Bạn chỉ cần chạy lệnh sau để kiểm tra:
     ```powershell
     python setup_latex_cpp.py --verify
     ```
   - Nếu phát hiện thiếu, chạy lại lệnh patch nhanh:
     ```powershell
     python setup_latex_cpp.py --minted --yes
     ```

3. **Chế độ Debug (`PALENIGHT_DEBUG=1`)**:
   - Mặc định, nếu gặp lỗi không tương thích phiên bản ngoài ý muốn, hook sẽ tự động bỏ qua để không làm gián đoạn việc biên dịch LaTeX.
   - Để kiểm tra chi tiết lỗi (nếu có), bạn có thể bật biến môi trường trước khi chạy:
     ```powershell
     $env:PALENIGHT_DEBUG="1"   # Trên PowerShell
     set PALENIGHT_DEBUG=1      # Trên Command Prompt (CMD)
     ```

---

## Giấy phép (License)
Dự án được phân phối dưới giấy phép [MIT License](LICENSE).
