import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from db_config import (
    add_employee_db as add_employee,
    fetch_employees_db as fetch_all_employees,
    update_employee_db as update_employee,
    delete_employee_db as delete_employee,
    create_connection,
    initialize_database,
    create_tables,
    fetch_departments,
    mark_in_time,
    mark_out_time,
    generate_payroll_db,
    fetch_payroll_db,
    upsert_payroll_for_employee
)
import mysql.connector

# Theme utilities
import ui_theme as theme

# Initialize DB / tables
initialize_database()
create_tables()

# ---------------- Window + Header ----------------
root = tk.Tk()
header = theme.style_window(root, "Employee Management & HR System", size="1180x720")
root.configure(bg=theme.COLORS["bg"])

# Style
style = ttk.Style()
style.configure("TCombobox", padding=5)

# ======================================================
# TAB CONTROL
# ======================================================
tab_control = ttk.Notebook(root)
tab_employee = tk.Frame(tab_control, bg=theme.COLORS["bg"])
tab_attendance = tk.Frame(tab_control, bg=theme.COLORS["bg"])
tab_payroll = tk.Frame(tab_control, bg=theme.COLORS["bg"])

tab_control.add(tab_employee, text="Employees")
tab_control.add(tab_attendance, text="Attendance")
tab_control.add(tab_payroll, text="Payroll")
tab_control.pack(expand=1, fill="both", padx=12, pady=(8,12))

# ======================================================
# EMPLOYEE TAB
# ======================================================
emp_frame = theme.styled_labelframe(tab_employee, text="Employee Information")
emp_frame.pack(padx=20, pady=15, fill="x")

labels = ["First Name", "Last Name", "Email", "Phone", "Job Title", "Base Salary"]
entries = {}

def refresh_departments():
    try:
        dept_vals = fetch_departments()
        widget = entries.get("Department")
        if isinstance(widget, ttk.Combobox):
            widget["values"] = dept_vals
            if widget.get() and widget.get() not in dept_vals:
                widget.set("")
    except:
        pass

for i, label in enumerate(labels):
    r = i // 2
    c = (i % 2) * 2
    lbl = tk.Label(emp_frame, text=label + ":", bg=emp_frame.cget("bg"))
    lbl.grid(row=r, column=c, sticky="w", padx=8, pady=6)
    theme.style_label(lbl)
    entry = tk.Entry(emp_frame, width=32)
    theme.style_entry(entry)
    entry.grid(row=r, column=c+1, padx=8, pady=6)
    entries[label] = entry

dept_frame = theme.styled_labelframe(emp_frame, text="Department Information")
dept_frame.grid(row=3, column=0, columnspan=4, sticky="we", padx=4, pady=(10,6))

tk.Label(dept_frame, text="Department ID:", bg=dept_frame.cget("bg")).grid(row=0, column=0, padx=8, pady=6, sticky="w")
dept_id_entry = tk.Entry(dept_frame, width=18)
theme.style_entry(dept_id_entry)
dept_id_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

tk.Label(dept_frame, text="Department Name:", bg=dept_frame.cget("bg")).grid(row=0, column=2, padx=8, pady=6, sticky="w")
dept_combobox = ttk.Combobox(dept_frame, values=fetch_departments(), width=28)
dept_combobox.grid(row=0, column=3, padx=6, pady=6, sticky="w")

entries["Department"] = dept_combobox
entries["Department ID"] = dept_id_entry

# ---------- FIXED: buffered=True everywhere ----------
def set_dept_id_from_name(event=None):
    name = dept_combobox.get().strip()
    if not name:
        dept_id_entry.delete(0, tk.END)
        return
    try:
        conn = create_connection()
        if conn:
            cur = conn.cursor(buffered=True)
            cur.execute("SELECT dept_id FROM departments WHERE dept_name=%s", (name,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            dept_id_entry.delete(0, tk.END)
            if row:
                dept_id_entry.insert(0, str(row[0]))
    except:
        pass

def set_dept_name_from_id(event=None):
    val = dept_id_entry.get().strip()
    if not val or not val.isdigit():
        dept_combobox.set("")
        return
    try:
        conn = create_connection()
        if conn:
            cur = conn.cursor(buffered=True)
            cur.execute("SELECT dept_name FROM departments WHERE dept_id=%s", (int(val),))
            row = cur.fetchone()
            cur.close()
            conn.close()
            dept_combobox.set(row[0] if row else "")
    except:
        pass

dept_combobox.bind("<<ComboboxSelected>>", set_dept_id_from_name)
dept_id_entry.bind("<FocusOut>", set_dept_name_from_id)

# CRUD Functions
def refresh_employees():
    emp_tree.delete(*emp_tree.get_children())
    employees = fetch_all_employees()
    for i, emp in enumerate(employees):
        values = (
            emp.get("emp_id", ""),
            emp.get("first_name", ""),
            emp.get("last_name", ""),
            emp.get("email", ""),
            emp.get("phone", ""),
            emp.get("job_title", ""),
            emp.get("dept_name", ""),
            str(emp.get("base_salary", ""))
        )
        tag = "even" if i % 2 == 0 else "odd"
        emp_tree.insert("", tk.END, values=values, tags=(tag,))

def clear_entries():
    for k, widget in entries.items():
        if isinstance(widget, ttk.Combobox):
            widget.set("")
        else:
            widget.delete(0, tk.END)

def add_action():
    first = entries["First Name"].get().strip()
    last = entries["Last Name"].get().strip()
    email = entries["Email"].get().strip()
    phone = entries["Phone"].get().strip()
    job = entries["Job Title"].get().strip()
    dept = entries["Department"].get().strip()
    salary = entries["Base Salary"].get().strip()

    if not first or salary == "":
        messagebox.showwarning("Input Missing", "Please fill required fields.")
        return

    try:
        salary_val = float(salary)
        if salary_val < 0:
            raise ValueError
    except:
        messagebox.showerror("Error", "Invalid salary.")
        return

    if add_employee(first, last, email, phone, job, dept, salary_val):
        messagebox.showinfo("Success", "Employee added!")
        refresh_employees()
        clear_entries()

def update_action():
    selected = emp_tree.focus()
    if not selected:
        messagebox.showwarning("No Selection", "Select an employee.")
        return

    vals = emp_tree.item(selected, "values")
    if not vals:
        return

    try:
        emp_id = int(vals[0])
    except:
        messagebox.showerror("Error", "Invalid employee ID.")
        return

    first = entries["First Name"].get().strip()
    last = entries["Last Name"].get().strip()
    email = entries["Email"].get().strip()
    phone = entries["Phone"].get().strip()
    job = entries["Job Title"].get().strip()
    dept = entries["Department"].get().strip()
    salary = entries["Base Salary"].get().strip()

    if not first:
        messagebox.showwarning("Input Missing", "First Name required.")
        return

    salary_val = float(salary) if salary else 0.0

    if update_employee(emp_id, first, last, email, phone, job, dept, salary_val):
        messagebox.showinfo("Success", "Updated!")
        refresh_employees()

def delete_action():
    selected = emp_tree.focus()
    if not selected:
        messagebox.showwarning("No Selection", "Select an employee.")
        return

    emp_id = int(emp_tree.item(selected, "values")[0])
    if messagebox.askyesno("Confirm", f"Delete Employee {emp_id}?"):
        if delete_employee(emp_id):
            messagebox.showinfo("Deleted", "Employee removed.")
            refresh_employees()
            clear_entries()

def on_emp_select(event):
    sel = emp_tree.focus()
    if not sel:
        return
    vals = emp_tree.item(sel, "values")
    if not vals or len(vals) < 8:
        return

    entries["First Name"].delete(0, tk.END); entries["First Name"].insert(0, vals[1])
    entries["Last Name"].delete(0, tk.END); entries["Last Name"].insert(0, vals[2])
    entries["Email"].delete(0, tk.END); entries["Email"].insert(0, vals[3])
    entries["Phone"].delete(0, tk.END); entries["Phone"].insert(0, vals[4])
    entries["Job Title"].delete(0, tk.END); entries["Job Title"].insert(0, vals[5])
    entries["Department"].set(vals[6] or "")
    entries["Base Salary"].delete(0, tk.END); entries["Base Salary"].insert(0, vals[7] or "")

    # FIX -------- buffered cursor
    try:
        emp_id = int(vals[0])
        conn = create_connection()
        if conn:
            cur = conn.cursor(buffered=True)
            cur.execute("SELECT dept_id FROM employees WHERE emp_id=%s", (emp_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            entries["Department ID"].delete(0, tk.END)
            if row:
                entries["Department ID"].insert(0, str(row[0]))
    except:
        pass

btn_frame = tk.Frame(tab_employee, bg=theme.COLORS["bg"])
btn_frame.pack(pady=6)

theme.colorful_button(btn_frame, "Add", add_action, "accent2").grid(row=0, column=0, padx=8)
theme.colorful_button(btn_frame, "Update", update_action, "header").grid(row=0, column=1, padx=8)
theme.colorful_button(btn_frame, "Delete", delete_action, "accent1").grid(row=0, column=2, padx=8)
theme.colorful_button(btn_frame, "Refresh", lambda: (refresh_employees(), refresh_departments(), clear_entries()), "accent2").grid(row=0, column=3, padx=8)

emp_table_frame = tk.Frame(tab_employee, bg=theme.COLORS["bg"])
emp_table_frame.pack(fill="both", expand=True, padx=15, pady=8)

emp_columns = ("ID", "First", "Last", "Email", "Phone", "Job Title", "Department", "Base Salary")
emp_tree = ttk.Treeview(emp_table_frame, columns=emp_columns, show="headings", selectmode="browse", height=10)

for col in emp_columns:
    emp_tree.heading(col, text=col)
    emp_tree.column(col, width=120, anchor="center")

theme.style_treeview(emp_tree)
emp_tree.pack(fill="both", expand=True, side="left")

scroll_y = ttk.Scrollbar(emp_table_frame, orient="vertical", command=emp_tree.yview)
scroll_y.pack(side="right", fill="y")
emp_tree.configure(yscrollcommand=scroll_y.set)
theme.style_scrollbar(scroll_y)

emp_tree.bind("<<TreeviewSelect>>", on_emp_select)
refresh_employees()
refresh_departments()

# ======================================================
# ATTENDANCE TAB
# ======================================================
att_frame = theme.styled_labelframe(tab_attendance, text="Mark Attendance")
att_frame.pack(padx=20, pady=15, fill="x")

tk.Label(att_frame, text="Employee ID:", bg=att_frame.cget("bg")).grid(row=0, column=0, padx=6, pady=6)
emp_id_entry = tk.Entry(att_frame)
theme.style_entry(emp_id_entry)
emp_id_entry.grid(row=0, column=1, padx=6, pady=6)

tk.Label(att_frame, text="Date (YYYY-MM-DD):", bg=att_frame.cget("bg")).grid(row=0, column=2, padx=6, pady=6)
date_entry = tk.Entry(att_frame)
theme.style_entry(date_entry)
date_entry.grid(row=0, column=3, padx=6, pady=6)
date_entry.insert(0, datetime.date.today().isoformat())

tk.Label(att_frame, text="Status:", bg=att_frame.cget("bg")).grid(row=0, column=4, padx=6, pady=6)
status_combo = ttk.Combobox(att_frame, values=["PRESENT", "ABSENT", "LEAVE"], width=12)
status_combo.grid(row=0, column=5, padx=6, pady=6)
status_combo.set("PRESENT")

def mark_attendance():
    emp_id = emp_id_entry.get().strip()
    date_str = date_entry.get().strip()
    status = status_combo.get().strip().upper()

    if not emp_id or not date_str:
        messagebox.showwarning("Input Missing", "All fields required.")
        return

    try:
        eid = int(emp_id)
    except:
        messagebox.showerror("Error", "Employee ID must be integer.")
        return

    try:
        att_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        messagebox.showerror("Error", "Date format wrong.")
        return

    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor(buffered=True)  # FIXED
            cursor.execute("SELECT emp_id FROM employees WHERE emp_id=%s", (eid,))
            if not cursor.fetchone():
                messagebox.showerror("Error", "Employee not found.")
                return

            cursor.execute("""
                INSERT INTO attendance (emp_id, att_date, status)
                VALUES (%s,%s,%s)
                ON DUPLICATE KEY UPDATE status=VALUES(status)
            """, (eid, att_date, status))
            conn.commit()
            messagebox.showinfo("Success", "Attendance recorded.")
            refresh_attendance()
        except mysql.connector.Error as e:
            conn.rollback()
            messagebox.showerror("Error", str(e))
        finally:
            cursor.close()
            conn.close()

theme.colorful_button(att_frame, "Mark Status", mark_attendance, "header").grid(row=0, column=6, padx=6, pady=6)
theme.colorful_button(att_frame, "In Time", lambda: (mark_in_time(emp_id_entry.get().strip()), refresh_attendance()), "accent2").grid(row=0, column=7, padx=6)
theme.colorful_button(att_frame, "Out Time", lambda: (mark_out_time(emp_id_entry.get().strip()), refresh_attendance()), "accent1").grid(row=0, column=8, padx=6)

# -------- Attendance Table --------
att_table_frame = tk.Frame(tab_attendance, bg=theme.COLORS["bg"])
att_table_frame.pack(fill="both", expand=True, padx=15, pady=8)

att_columns = ("ID", "Emp ID", "Date", "In Time", "Out Time", "Status")
att_tree = ttk.Treeview(att_table_frame, columns=att_columns, show="headings", height=8)

for col in att_columns:
    att_tree.heading(col, text=col)
    att_tree.column(col, width=140, anchor="center")

theme.style_treeview(att_tree)
att_tree.pack(fill="both", expand=True, side="left")

scroll_y_att = ttk.Scrollbar(att_table_frame, orient="vertical", command=att_tree.yview)
scroll_y_att.pack(side="right", fill="y")
att_tree.configure(yscrollcommand=scroll_y_att.set)
theme.style_scrollbar(scroll_y_att)

def refresh_attendance():
    att_tree.delete(*att_tree.get_children())
    conn = create_connection()
    if conn:
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute("SELECT att_id, emp_id, att_date, in_time, out_time, status FROM attendance ORDER BY att_date DESC, emp_id")
            rows = cursor.fetchall()
            for i, rec in enumerate(rows):
                values = list(rec)
                values[3] = values[3].strftime('%Y-%m-%d %H:%M:%S') if values[3] else ''
                values[4] = values[4].strftime('%Y-%m-%d %H:%M:%S') if values[4] else ''
                tag = "even" if i % 2 == 0 else "odd"
                att_tree.insert("", tk.END, values=values, tags=(tag,))
        finally:
            cursor.close()
            conn.close()

refresh_attendance()

# ======================================================
# PAYROLL TAB
# ======================================================
pay_frame = theme.styled_labelframe(tab_payroll, text="Payroll Generation")
pay_frame.pack(padx=20, pady=15, fill="x")

tk.Label(pay_frame, text="Employee ID (leave empty for all):", bg=pay_frame.cget("bg")).grid(row=0, column=0, padx=6, pady=6)
pay_emp_id = tk.Entry(pay_frame)
theme.style_entry(pay_emp_id)
pay_emp_id.grid(row=0, column=1, padx=6, pady=6)

tk.Label(pay_frame, text="Year-Month (YYYY-MM):", bg=pay_frame.cget("bg")).grid(row=0, column=2, padx=6, pady=6)
pay_month = tk.Entry(pay_frame)
theme.style_entry(pay_month)
pay_month.grid(row=0, column=3, padx=6, pady=6)
pay_month.insert(0, datetime.date.today().strftime("%Y-%m"))

def generate_payroll():
    emp_id_str = pay_emp_id.get().strip()
    ym = pay_month.get().strip()

    if not ym or len(ym) != 7 or ym[4] != '-':
        messagebox.showwarning("Invalid Month", "Format must be YYYY-MM.")
        return

    if emp_id_str == "":
        if generate_payroll_db(ym):
            refresh_payroll(year_month=ym)
        return

    try:
        eid = int(emp_id_str)
    except:
        messagebox.showerror("Error", "Employee ID must be integer.")
        return

    conn = create_connection()
    if conn:
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute("SELECT base_salary FROM employees WHERE emp_id=%s AND status='ACTIVE'", (eid,))
            data = cursor.fetchone()

            if not data:
                messagebox.showerror("Error", "Employee not found or inactive.")
                return

            base_salary = data[0]

            if upsert_payroll_for_employee(eid, ym, base_salary):
                messagebox.showinfo("Success", "Payroll generated.")
                refresh_payroll(emp_id=eid, year_month=ym)
        except mysql.connector.Error as e:
            messagebox.showerror("Error", str(e))
        finally:
            cursor.close()
            conn.close()

theme.colorful_button(pay_frame, "Generate Payroll", generate_payroll, "header").grid(row=0, column=4, padx=8, pady=6)

pay_table_frame = tk.Frame(tab_payroll, bg=theme.COLORS["bg"])
pay_table_frame.pack(fill="both", expand=True, padx=15, pady=8)

pay_columns = ("ID", "Emp ID", "First", "Last", "Year-Month", "Gross Pay", "Allowances", "Deductions", "Net Pay")
pay_tree = ttk.Treeview(pay_table_frame, columns=pay_columns, show="headings", height=9)

for col in pay_columns:
    pay_tree.heading(col, text=col)
    pay_tree.column(col, width=120, anchor="center")

theme.style_treeview(pay_tree)
pay_tree.pack(fill="both", expand=True, side="left")

scroll_y_pay = ttk.Scrollbar(pay_table_frame, orient="vertical", command=pay_tree.yview)
scroll_y_pay.pack(side="right", fill="y")
pay_tree.configure(yscrollcommand=scroll_y_pay.set)
theme.style_scrollbar(scroll_y_pay)

def refresh_payroll(emp_id=None, year_month=None):
    pay_tree.delete(*pay_tree.get_children())
    rows = fetch_payroll_db(emp_id=emp_id, year_month=year_month)
    for i, rec in enumerate(rows):
        values = list(rec)
        for j in range(5, 9):
            values[j] = str(values[j]) if values[j] is not None else ""
        tag = "even" if i % 2 == 0 else "odd"
        pay_tree.insert("", tk.END, values=values, tags=(tag,))

refresh_payroll()

# ======================================================
# RUN APP
# ======================================================
root.mainloop()
