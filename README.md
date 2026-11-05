# 🎓 Quản lý Sinh viên

Website quản lý sinh viên xây dựng bằng **Flask + SQLite**, có đăng nhập phân quyền **Giảng viên** và **Sinh viên**.

> Đồ án môn Lập trình Web — Sinh viên năm 2, ngành Công nghệ thông tin.

## ✨ Tính năng

**Giảng viên**
- Quản lý sinh viên: thêm / sửa / xóa / tìm kiếm
- Quản lý môn học (mã môn, tên môn, số tín chỉ)
- Nhập điểm cho từng sinh viên theo từng môn
- Trang tổng quan: tổng số sinh viên, điểm trung bình toàn trường, top 5 GPA cao nhất

**Sinh viên**
- Đăng nhập bằng MSSV, xem hồ sơ cá nhân
- Xem bảng điểm và GPA (tính theo tín chỉ) của chính mình

## 🛠️ Công nghệ

- **Backend:** Python, Flask
- **Database:** SQLite (file `qlsv.db`, tự tạo khi chạy lần đầu)
- **Frontend:** HTML, CSS, Jinja2 (không dùng framework JS ngoài)
- **Bảo mật mật khẩu:** Werkzeug (`generate_password_hash` / `check_password_hash`)

## 🚀 Cài đặt & chạy

```bash
# 1. Clone về máy
git clone <link-repo-cua-ban>
cd qlsv

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Chạy ứng dụng
python app.py
```

Mở trình duyệt tại: **http://127.0.0.1:5000**

## 🔑 Tài khoản mặc định

| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Giảng viên | `giangvien` | `giangvien123` |
| Sinh viên | MSSV (VD: `SV001`) | trùng với MSSV |

> Tài khoản sinh viên được **tự động tạo** khi giảng viên thêm sinh viên mới.

## 📁 Cấu trúc thư mục

```
qlsv/
├── app.py                 # Toàn bộ route, logic xử lý, truy vấn SQL
├── requirements.txt        # Danh sách thư viện cần cài
├── qlsv.db                 # Database SQLite (tự sinh, không commit lên git)
├── templates/               # Giao diện HTML (Jinja2)
│   ├── base.html            # Khung chung: header, nav, footer
│   ├── login.html           # Trang đăng nhập
│   ├── gv_dashboard.html    # Tổng quan (giảng viên)
│   ├── gv_students.html     # Danh sách + tìm kiếm sinh viên
│   ├── sv_form.html         # Form thêm / sửa sinh viên
│   ├── gv_subjects.html     # Quản lý môn học
│   ├── gv_grades.html       # Nhập điểm cho 1 sinh viên
│   └── sv_dashboard.html    # Hồ sơ + bảng điểm (sinh viên)
└── static/css/style.css    # Giao diện
```

## 🗄️ Thiết kế database

```
users (id, username, password_hash, role)
students (id, mssv, name, birthday, gender, class_name, user_id → users.id)
subjects (id, ma_mon, ten_mon, so_tin_chi)
grades (id, student_id → students.id, subject_id → subjects.id, diem)
```

- `grades` có ràng buộc `UNIQUE(student_id, subject_id)` → mỗi sinh viên chỉ có 1 điểm cho 1 môn.
- GPA tính theo công thức trung bình có trọng số tín chỉ:
  `GPA = Σ(điểm × tín_chỉ) / Σ(tín_chỉ)`

## 📌 Ghi chú

- Đây là đồ án học tập, mật khẩu đã được băm (hash) nhưng chưa có các lớp bảo mật nâng cao (CSRF token, rate limit...) — phù hợp để học, chưa nên dùng cho môi trường thật.
- Khi deploy thật, cần đổi `app.secret_key` trong `app.py` sang một chuỗi bí mật khác.

## 📄 License

Dự án phục vụ mục đích học tập.
