import mysql.connector
from mysql.connector import Error
from tkinter import messagebox
import datetime
import re
import sys
from decimal import Decimal

# -----------------------
# DATABASE CONFIG
# -----------------------
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "6667"
DB_NAME = "employee_management"

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


# -----------------------
# Helper for error display
# -----------------------
def _show_error(title, msg):
    """Show messagebox if GUI is active, otherwise print to stderr."""
    try:
        messagebox.showerror(title, msg)
    except Exception:
        print(f"[{title}] {msg}", file=sys.stderr)


# -----------------------
# CONNECTION
# -----------------------
def create_connection():
    """Create and return a new MySQL connection or None if it fails."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            autocommit=False
        )
        return conn
    except Error as e:
        _show_error("DB Connection Error", str(e))
        return None


# -----------------------
# INITIALIZE DATABASE & TABLES
# -----------------------
def initialize_database():
    """Create the database if it doesn't exist."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor(buffered=True)   # ✅ FIXED
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    except Error as e:
        _show_error("DB Error", f"Error creating database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_tables():
    """Create all required tables and default departments."""
    conn = create_connection()
    if conn is None:
        return
    cursor = None
    try:
        cursor = conn.cursor(buffered=True)

        # Departments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            dept_id INT PRIMARY KEY AUTO_INCREMENT,
            dept_name VARCHAR(100) NOT NULL UNIQUE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Employees
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            emp_id INT PRIMARY KEY AUTO_INCREMENT,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100),
            email VARCHAR(150) UNIQUE,
            phone VARCHAR(20),
            hire_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            job_title VARCHAR(100),
            dept_id INT,
            base_salary DECIMAL(12,2) DEFAULT 0,
            status ENUM('ACTIVE','INACTIVE','TERMINATED') DEFAULT 'ACTIVE',
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Attendance
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            att_id INT PRIMARY KEY AUTO_INCREMENT,
            emp_id INT NOT NULL,
            att_date DATE NOT NULL,
            in_time DATETIME,
            out_time DATETIME,
            status ENUM('PRESENT','ABSENT','LEAVE') DEFAULT 'PRESENT',
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE,
            UNIQUE(emp_id, att_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Payroll
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            payroll_id INT PRIMARY KEY AUTO_INCREMENT,
            emp_id INT NOT NULL,
            `year_month` VARCHAR(7) NOT NULL,
            gross_pay DECIMAL(12,2),
            allowances DECIMAL(12,2),
            deductions DECIMAL(12,2),
            net_pay DECIMAL(12,2),
            generated_on DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(emp_id, `year_month`),
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Insert default departments
        for dept in ["HR", "IT", "Finance", "Sales", "Marketing", "Admin"]:
            cursor.execute(
                "INSERT INTO departments (dept_name) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE dept_name=dept_name",
                (dept,)
            )

        conn.commit()
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("DB Error", str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# -----------------------
# DEPARTMENT FUNCTIONS
# -----------------------
def fetch_departments():
    """Fetch all department names from the database."""
    conn = create_connection()
    if conn is None:
        return []
    cursor = conn.cursor(buffered=True)   # ✅ FIXED
    try:
        cursor.execute("SELECT dept_name FROM departments ORDER BY dept_name")
        departments = [row[0] for row in cursor.fetchall()]
        return departments
    except Error as e:
        _show_error("DB Error", f"Error fetching departments: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


# -----------------------
# VALIDATION UTILITIES
# -----------------------
def _validate_email(email):
    return EMAIL_RE.match(email) is not None


def _validate_phone(phone):
    if not phone:
        return True
    return bool(re.match(r'^[\d+\-\s()]{3,20}$', phone))


def _resolve_dept_id(conn, dept):
    """Accept either dept_id or dept_name."""
    if dept is None or dept == "":
        return None
    if isinstance(dept, int) or (isinstance(dept, str) and dept.isdigit()):
        return int(dept)
    cur = conn.cursor(buffered=True)   # ✅ FIXED
    try:
        cur.execute("SELECT dept_id FROM departments WHERE dept_name=%s", (dept,))
        row = cur.fetchone()
        if row:
            return row[0]
        return None
    finally:
        cur.close()


# -----------------------
# EMPLOYEE FUNCTIONS
# -----------------------
def add_employee_db(first, last, email, phone, job, dept, salary):
    if not first:
        _show_error("Validation Error", "First name is required.")
        return False

    if email and not _validate_email(email):
        _show_error("Validation Error", "Invalid email format.")
        return False

    if phone and not _validate_phone(phone):
        _show_error("Validation Error", "Invalid phone number.")
        return False

    try:
        salary_decimal = Decimal(str(salary or 0))
        if salary_decimal < 0:
            raise ValueError
    except Exception:
        _show_error("Validation Error", "Invalid salary value.")
        return False

    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(buffered=True)
    try:
        dept_id = _resolve_dept_id(conn, dept)
        cursor.execute("""
            INSERT INTO employees (first_name, last_name, email, phone, job_title, dept_id, base_salary)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (first, last or None, email or None, phone or None, job or None, dept_id, salary_decimal))
        conn.commit()
        return True
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("DB Error", str(e))
        return False
    finally:
        cursor.close()
        conn.close()


def fetch_employees_db():
    conn = create_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT e.emp_id, e.first_name, e.last_name, e.email, e.phone,
                   e.job_title, COALESCE(d.dept_name, '') AS dept_name, e.base_salary
            FROM employees e
            LEFT JOIN departments d ON e.dept_id = d.dept_id
            ORDER BY e.emp_id
        """)
        rows = cursor.fetchall()
        return rows
    except Error as e:
        _show_error("Error", str(e))
        return []
    finally:
        cursor.close()
        conn.close()


def update_employee_db(emp_id, first, last, email, phone, job, dept, salary):
    if not first:
        _show_error("Validation Error", "First name is required.")
        return False
    if email and not _validate_email(email):
        _show_error("Validation Error", "Invalid email format.")
        return False
    if phone and not _validate_phone(phone):
        _show_error("Validation Error", "Invalid phone number.")
        return False

    try:
        salary_decimal = Decimal(str(salary or 0))
        if salary_decimal < 0:
            raise ValueError
    except Exception:
        _show_error("Validation Error", "Invalid salary value.")
        return False

    try:
        emp_id_int = int(emp_id)
    except Exception:
        _show_error("Validation Error", "Invalid employee ID.")
        return False

    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(buffered=True)
    try:
        dept_id = _resolve_dept_id(conn, dept)
        cursor.execute("""
            UPDATE employees
            SET first_name=%s, last_name=%s, email=%s, phone=%s,
                job_title=%s, dept_id=%s, base_salary=%s
            WHERE emp_id=%s
        """, (first, last or None, email or None, phone or None, job or None, dept_id, salary_decimal, emp_id_int))
        conn.commit()
        return cursor.rowcount > 0
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("Error", str(e))
        return False
    finally:
        cursor.close()
        conn.close()


def delete_employee_db(emp_id):
    try:
        emp_id_int = int(emp_id)
    except Exception:
        _show_error("Validation Error", "Invalid employee ID.")
        return False

    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("DELETE FROM employees WHERE emp_id=%s", (emp_id_int,))
        conn.commit()
        return cursor.rowcount > 0
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("Error", str(e))
        return False
    finally:
        cursor.close()
        conn.close()


# -----------------------
# ATTENDANCE FUNCTIONS
# -----------------------
def mark_in_time(emp_id):
    if not emp_id or not str(emp_id).isdigit():
        _show_error("Validation Error", "Employee ID must be a number.")
        return False

    today = datetime.date.today()
    now = datetime.datetime.now()
    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("SELECT att_id FROM attendance WHERE emp_id=%s AND att_date=%s", (emp_id, today))
        if cursor.fetchone():
            _show_error("Warning", "Attendance entry for today already exists. Use Out-Time or Mark.")
            return False

        cursor.execute("SELECT emp_id FROM employees WHERE emp_id=%s", (emp_id,))
        if not cursor.fetchone():
            _show_error("Error", f"Employee ID {emp_id} not found.")
            return False

        cursor.execute("""
            INSERT INTO attendance (emp_id, att_date, in_time, status)
            VALUES (%s, %s, %s, 'PRESENT')
        """, (emp_id, today, now))
        conn.commit()
        try:
            messagebox.showinfo("Success", f"In-Time marked at {now.strftime('%H:%M:%S')}")
        except Exception:
            pass
        return True
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("Error", str(e))
        return False
    finally:
        cursor.close()
        conn.close()


def mark_out_time(emp_id):
    if not emp_id or not str(emp_id).isdigit():
        _show_error("Validation Error", "Employee ID must be a number.")
        return False

    today = datetime.date.today()
    now = datetime.datetime.now()
    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT att_id, out_time FROM attendance WHERE emp_id=%s AND att_date=%s", (emp_id, today))
        record = cursor.fetchone()
        if not record:
            _show_error("Warning", "No In-Time found for today. Cannot mark Out-Time.")
            return False
        if record["out_time"]:
            _show_error("Warning", "Out-Time already marked for today.")
            return False

        cursor.execute("UPDATE attendance SET out_time=%s WHERE emp_id=%s AND att_date=%s", (now, emp_id, today))
        conn.commit()
        try:
            messagebox.showinfo("Success", f"Out-Time marked at {now.strftime('%H:%M:%S')}")
        except Exception:
            pass
        return True
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("Error", str(e))
        return False
    finally:
        cursor.close()
        conn.close()


# -----------------------
# PAYROLL FUNCTIONS
# -----------------------
def upsert_payroll_for_employee(emp_id, year_month, base_salary):
    try:
        emp_id_int = int(emp_id)
    except Exception:
        _show_error("Validation Error", "Employee ID must be a number.")
        return False

    if not year_month or len(year_month) != 7 or year_month[4] != "-":
        _show_error("Validation Error", "year_month must be in YYYY-MM format.")
        return False

    try:
        base_salary_dec = Decimal(str(base_salary or 0))
        if base_salary_dec < 0:
            raise ValueError
    except Exception:
        _show_error("Validation Error", "Invalid base salary for calculation.")
        return False

    allowances = (base_salary_dec * Decimal("0.10")).quantize(Decimal('0.01'))
    deductions = (base_salary_dec * Decimal("0.05")).quantize(Decimal('0.01'))
    gross = (base_salary_dec + allowances).quantize(Decimal('0.01'))
    net = (gross - deductions).quantize(Decimal('0.01'))

    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute("""
            INSERT INTO payroll (emp_id, `year_month`, gross_pay, allowances, deductions, net_pay)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                gross_pay=VALUES(gross_pay),
                allowances=VALUES(allowances),
                deductions=VALUES(deductions),
                net_pay=VALUES(net_pay),
                generated_on=CURRENT_TIMESTAMP
        """, (emp_id_int, year_month, gross, allowances, deductions, net))
        conn.commit()
        return True
    except Error as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _show_error("Error", str(e))
        return False
    finally:
        cursor.close()
        conn.close()


def generate_payroll_db(year_month):
    if not year_month or len(year_month) != 7 or year_month[4] != "-":
        _show_error("Validation Error", "year_month must be in YYYY-MM format.")
        return False

    conn = create_connection()
    if conn is None:
        return False
    cursor = conn.cursor(buffered=True)   # ✅ FIXED
    try:
        cursor.execute("SELECT emp_id, base_salary FROM employees WHERE status='ACTIVE'")
        records = cursor.fetchall()
    except Error as e:
        _show_error("Error", str(e))
        return False
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    success = True
    for emp_id, base_salary in records:
        if not upsert_payroll_for_employee(emp_id, year_month, base_salary):
            success = False

    try:
        if success:
            messagebox.showinfo("Success", "Payroll generated successfully for all active employees.")
        else:
            messagebox.showwarning("Partial Success", "Payroll generation completed, but some employees may have failed.")
    except Exception:
        pass

    return success


def fetch_payroll_db(emp_id=None, year_month=None):
    conn = create_connection()
    if conn is None:
        return []
    cursor = conn.cursor(buffered=True)
    try:
        base_query = """
            SELECT p.payroll_id, p.emp_id, e.first_name, e.last_name,
                   p.`year_month`, p.gross_pay, p.allowances, p.deductions, p.net_pay
            FROM payroll p
            JOIN employees e ON p.emp_id = e.emp_id
        """
        clauses = []
        params = []

        if emp_id is not None:
            try:
                emp_id_int = int(emp_id)
                clauses.append("p.emp_id = %s")
                params.append(emp_id_int)
            except Exception:
                return []

        if year_month is not None:
            clauses.append("p.`year_month` = %s")
            params.append(year_month)

        if clauses:
            base_query += " WHERE " + " AND ".join(clauses)

        base_query += " ORDER BY p.`year_month` DESC, p.emp_id"

        cursor.execute(base_query, tuple(params))
        rows = cursor.fetchall()
        return rows
    except Error as e:
        _show_error("DB Error", str(e))
        return []
    finally:
        cursor.close()
        conn.close()
