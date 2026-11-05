from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "doi-chuoi-nay-khi-trien-khai-that"

DB_PATH = os.path.join(os.path.dirname(__file__), "qlsv.db")

# ---------- Flask-Login: quản lý đăng nhập ----------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục!"
login_manager.login_message_category = "error"

# ---------- Flask-WTF: chống tấn công CSRF cho mọi form POST ----------
csrf = CSRFProtect(app)


# ---------- Kết nối & khởi tạo database ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('giangvien','sinhvien'))
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mssv TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            birthday TEXT,
            gender TEXT,
            class_name TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_mon TEXT NOT NULL UNIQUE,
            ten_mon TEXT NOT NULL,
            so_tin_chi INTEGER NOT NULL DEFAULT 3
        );

        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            diem REAL NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            UNIQUE(student_id, subject_id)
        );
    """)
    conn.commit()

    gv = conn.execute("SELECT id FROM users WHERE username = 'giangvien'").fetchone()
    if not gv:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'giangvien')",
            ("giangvien", generate_password_hash("giangvien123")),
        )

    so_mon = conn.execute("SELECT COUNT(*) AS c FROM subjects").fetchone()["c"]
    if so_mon == 0:
        mon_hoc_mau = [
            ("NMLT", "Nhập môn lập trình", 3),
            ("CTDL", "Cấu trúc dữ liệu & giải thuật", 4),
            ("CSDL", "Cơ sở dữ liệu", 3),
            ("MMT", "Mạng máy tính", 3),
            ("OOP", "Lập trình hướng đối tượng", 3),
        ]
        conn.executemany(
            "INSERT INTO subjects (ma_mon, ten_mon, so_tin_chi) VALUES (?, ?, ?)",
            mon_hoc_mau,
        )

    conn.commit()
    conn.close()


# ---------- Model User cho Flask-Login ----------
class User(UserMixin):
    def __init__(self, row):
        self.id = str(row["id"])
        self.username = row["username"]
        self.role = row["role"]


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return User(row) if row else None


# ---------- Decorator kiểm tra vai trò (chạy sau khi đã đăng nhập) ----------
def role_required(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role != role:
                flash("Bạn không có quyền truy cập trang này!", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------- Đăng nhập / Đăng xuất ----------
@app.route("/dang-nhap", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if row and check_password_hash(row["password_hash"], password):
            login_user(User(row))
            flash(f"Xin chào {username}!", "success")
            return redirect(url_for("index"))
        flash("Sai tên đăng nhập hoặc mật khẩu!", "error")
    return render_template("login.html")


@app.route("/dang-xuat")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    if current_user.role == "giangvien":
        return redirect(url_for("gv_dashboard"))
    return redirect(url_for("sv_dashboard"))


# =========================================================
# ==================  PHẦN GIẢNG VIÊN  ====================
# =========================================================
@app.route("/giangvien")
@role_required("giangvien")
def gv_dashboard():
    conn = get_db()
    tong_sv = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
    tong_mon = conn.execute("SELECT COUNT(*) AS c FROM subjects").fetchone()["c"]
    diem_tb = conn.execute("SELECT AVG(diem) AS tb FROM grades").fetchone()["tb"]
    bang_xep_hang = conn.execute("""
        SELECT s.name, s.mssv,
               ROUND(SUM(g.diem * sub.so_tin_chi) * 1.0 / SUM(sub.so_tin_chi), 2) AS gpa
        FROM students s
        JOIN grades g ON g.student_id = s.id
        JOIN subjects sub ON sub.id = g.subject_id
        GROUP BY s.id
        ORDER BY gpa DESC
        LIMIT 5
    """).fetchall()
    conn.close()
    return render_template(
        "gv_dashboard.html", tong_sv=tong_sv, tong_mon=tong_mon,
        diem_tb=diem_tb, bang_xep_hang=bang_xep_hang,
    )


@app.route("/giangvien/sinh-vien")
@role_required("giangvien")
def gv_students():
    keyword = request.args.get("q", "").strip()
    conn = get_db()
    if keyword:
        rows = conn.execute(
            "SELECT * FROM students WHERE mssv LIKE ? OR name LIKE ? ORDER BY id DESC",
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("gv_students.html", students=rows, keyword=keyword)


@app.route("/giangvien/sinh-vien/them", methods=["GET", "POST"])
@role_required("giangvien")
def gv_add_student():
    if request.method == "POST":
        mssv = request.form["mssv"].strip()
        name = request.form["name"].strip()
        birthday = request.form.get("birthday", "")
        gender = request.form.get("gender", "")
        class_name = request.form.get("class_name", "")

        if not mssv or not name:
            flash("MSSV và Họ tên không được để trống!", "error")
            return redirect(url_for("gv_add_student"))

        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'sinhvien')",
                (mssv, generate_password_hash(mssv)),
            )
            user_id = cur.lastrowid
            conn.execute(
                "INSERT INTO students (mssv, name, birthday, gender, class_name, user_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (mssv, name, birthday, gender, class_name, user_id),
            )
            conn.commit()
            flash(f"Đã thêm {name}. Tài khoản đăng nhập của sinh viên: {mssv} / mật khẩu: {mssv}", "success")
        except sqlite3.IntegrityError:
            flash("MSSV này đã tồn tại!", "error")
        finally:
            conn.close()
        return redirect(url_for("gv_students"))

    return render_template("sv_form.html", student=None, action="Thêm")


@app.route("/giangvien/sinh-vien/sua/<int:student_id>", methods=["GET", "POST"])
@role_required("giangvien")
def gv_edit_student(student_id):
    conn = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        birthday = request.form.get("birthday", "")
        gender = request.form.get("gender", "")
        class_name = request.form.get("class_name", "")
        conn.execute(
            "UPDATE students SET name=?, birthday=?, gender=?, class_name=? WHERE id=?",
            (name, birthday, gender, class_name, student_id),
        )
        conn.commit()
        conn.close()
        flash("Cập nhật thành công!", "success")
        return redirect(url_for("gv_students"))

    student = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    conn.close()
    if student is None:
        flash("Không tìm thấy sinh viên!", "error")
        return redirect(url_for("gv_students"))
    return render_template("sv_form.html", student=student, action="Sửa")


@app.route("/giangvien/sinh-vien/xoa/<int:student_id>")
@role_required("giangvien")
def gv_delete_student(student_id):
    conn = get_db()
    sv = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if sv:
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        if sv["user_id"]:
            conn.execute("DELETE FROM users WHERE id=?", (sv["user_id"],))
        conn.commit()
    conn.close()
    flash("Đã xóa sinh viên!", "success")
    return redirect(url_for("gv_students"))


# ---------- Quản lý môn học ----------
@app.route("/giangvien/mon-hoc", methods=["GET", "POST"])
@role_required("giangvien")
def gv_subjects():
    conn = get_db()
    if request.method == "POST":
        ma_mon = request.form["ma_mon"].strip()
        ten_mon = request.form["ten_mon"].strip()
        so_tin_chi = request.form.get("so_tin_chi") or 3
        try:
            conn.execute(
                "INSERT INTO subjects (ma_mon, ten_mon, so_tin_chi) VALUES (?, ?, ?)",
                (ma_mon, ten_mon, so_tin_chi),
            )
            conn.commit()
            flash(f"Đã thêm môn {ten_mon}!", "success")
        except sqlite3.IntegrityError:
            flash("Mã môn này đã tồn tại!", "error")
    subjects = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    conn.close()
    return render_template("gv_subjects.html", subjects=subjects)


@app.route("/giangvien/mon-hoc/xoa/<int:subject_id>")
@role_required("giangvien")
def gv_delete_subject(subject_id):
    conn = get_db()
    conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    conn.commit()
    conn.close()
    flash("Đã xóa môn học!", "success")
    return redirect(url_for("gv_subjects"))


# ---------- Nhập điểm cho sinh viên ----------
@app.route("/giangvien/diem/<int:student_id>", methods=["GET", "POST"])
@role_required("giangvien")
def gv_grades(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if student is None:
        conn.close()
        flash("Không tìm thấy sinh viên!", "error")
        return redirect(url_for("gv_students"))

    if request.method == "POST":
        subject_id = request.form["subject_id"]
        diem_raw = request.form["diem"]
        try:
            diem = float(diem_raw)
            if not (0 <= diem <= 10):
                raise ValueError
        except ValueError:
            flash("Điểm phải là số từ 0 đến 10!", "error")
            conn.close()
            return redirect(url_for("gv_grades", student_id=student_id))

        conn.execute("""
            INSERT INTO grades (student_id, subject_id, diem) VALUES (?, ?, ?)
            ON CONFLICT(student_id, subject_id) DO UPDATE SET diem = excluded.diem
        """, (student_id, subject_id, diem))
        conn.commit()
        flash("Đã lưu điểm!", "success")
        conn.close()
        return redirect(url_for("gv_grades", student_id=student_id))

    diem_list = conn.execute("""
        SELECT g.id, sub.ten_mon, sub.so_tin_chi, g.diem
        FROM grades g JOIN subjects sub ON sub.id = g.subject_id
        WHERE g.student_id = ?
        ORDER BY sub.ten_mon
    """, (student_id,)).fetchall()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY ten_mon").fetchall()

    gpa_row = conn.execute("""
        SELECT SUM(g.diem * sub.so_tin_chi) * 1.0 / SUM(sub.so_tin_chi) AS gpa
        FROM grades g JOIN subjects sub ON sub.id = g.subject_id
        WHERE g.student_id = ?
    """, (student_id,)).fetchone()
    gpa = round(gpa_row["gpa"], 2) if gpa_row["gpa"] is not None else None

    conn.close()
    return render_template(
        "gv_grades.html", student=student, diem_list=diem_list, subjects=subjects, gpa=gpa,
    )


@app.route("/giangvien/diem/xoa/<int:grade_id>/<int:student_id>")
@role_required("giangvien")
def gv_delete_grade(grade_id, student_id):
    conn = get_db()
    conn.execute("DELETE FROM grades WHERE id=?", (grade_id,))
    conn.commit()
    conn.close()
    flash("Đã xóa điểm!", "success")
    return redirect(url_for("gv_grades", student_id=student_id))


# =========================================================
# ===================  PHẦN SINH VIÊN  ====================
# =========================================================
@app.route("/sinh-vien")
@role_required("sinhvien")
def sv_dashboard():
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE user_id=?", (int(current_user.id),)
    ).fetchone()
    if student is None:
        conn.close()
        flash("Không tìm thấy hồ sơ sinh viên!", "error")
        return redirect(url_for("login"))

    diem_list = conn.execute("""
        SELECT sub.ten_mon, sub.so_tin_chi, g.diem
        FROM grades g JOIN subjects sub ON sub.id = g.subject_id
        WHERE g.student_id = ?
        ORDER BY sub.ten_mon
    """, (student["id"],)).fetchall()

    gpa_row = conn.execute("""
        SELECT SUM(g.diem * sub.so_tin_chi) * 1.0 / SUM(sub.so_tin_chi) AS gpa
        FROM grades g JOIN subjects sub ON sub.id = g.subject_id
        WHERE g.student_id = ?
    """, (student["id"],)).fetchone()
    gpa = round(gpa_row["gpa"], 2) if gpa_row["gpa"] is not None else None

    conn.close()
    return render_template("sv_dashboard.html", student=student, diem_list=diem_list, gpa=gpa)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
