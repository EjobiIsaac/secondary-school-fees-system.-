import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

from database import init_db, get_connection
from settings import get_all_settings, update_settings, change_user_password
from logic import (
    authenticate_user,
    add_student,
    add_fee_item,
    get_student_financial_summary,
    record_payment,
    void_payment,
    reconcile_csv_statements,
    get_defaulters_list,
    rollover_term_or_year,
)
from receipts import generate_receipt_pdf, generate_clearance_pass_pdf
from backup import create_backup, restore_backup

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class SchoolFeesApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_db()
        self.current_user = None
        self.title("🏫 Secondary School Fees Payment System")
        self.geometry("1150x700")
        self.minsize(1000, 620)
        self.show_login_screen()

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    # ================= LOGIN SCREEN =================
    def show_login_screen(self):
        self.clear_window()
        cfg = get_all_settings()

        frame = ctk.CTkFrame(self, width=420, height=440, corner_radius=15)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="🏫", font=("Arial", 44)).pack(pady=(25, 5))
        ctk.CTkLabel(
            frame, text=cfg.get("school_name", "SECONDARY SCHOOL"),
            font=("Arial", 18, "bold")
        ).pack(pady=2)
        ctk.CTkLabel(
            frame, text="Fees Management & Clearance Portal",
            font=("Arial", 12), text_color="gray"
        ).pack(pady=(0, 20))

        self.user_entry = ctk.CTkEntry(frame, width=300, placeholder_text="👤 Username (e.g. admin / bursar)")
        self.user_entry.pack(pady=8)

        self.pass_entry = ctk.CTkEntry(frame, width=300, show="*", placeholder_text="🔑 Password")
        self.pass_entry.pack(pady=8)
        self.pass_entry.bind("<Return>", lambda e: self.handle_login())

        ctk.CTkButton(
            frame, text="🔐 Sign In", width=300, height=40,
            font=("Arial", 14, "bold"), command=self.handle_login
        ).pack(pady=(18, 10))

        ctk.CTkLabel(
            frame, text="Default: admin / admin123  or  bursar / bursar123",
            font=("Arial", 11), text_color="gray"
        ).pack(pady=(5, 20))

    def handle_login(self):
        user = authenticate_user(self.user_entry.get(), self.pass_entry.get())
        if not user:
            messagebox.showerror("Login Failed", "Invalid username or password.")
            return
        self.current_user = user
        self.build_main_shell()
    # ================= MAIN NAVIGATION SHELL =================
    def build_main_shell(self):
        self.clear_window()
        cfg = get_all_settings()
        self.title(f"🏫 {cfg.get('school_name')} — [{self.current_user['role']}]")

        # Left Sidebar with Icons
        sidebar = ctk.CTkFrame(self, width=230, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="🏫 FEES MANAGER", font=("Arial", 17, "bold")).pack(pady=(20, 4))
        ctk.CTkLabel(
            sidebar,
            text=f"{cfg.get('current_year')} • {cfg.get('current_term')}",
            font=("Arial", 12, "bold"), text_color="#3B8ED0"
        ).pack(pady=(0, 15))

        nav_items = [
            ("📊  Dashboard", self.show_dashboard),
            ("🎓  Students (S1–S6)", self.show_students),
            ("💳  Collect Fees & CSV", self.show_payments),
            ("🪪  Exam / Gate Clearance", self.show_clearance),
            ("📋  Fee Structures", self.show_fee_structures),
            ("⚠️  Defaulters List", self.show_defaulters),
            ("🔄  Term / Year Rollover", self.show_rollover),
            ("🛡️  Audit Logs & Void", self.show_audit_logs),
            ("💾  USB Backup & Restore", self.show_backups),
            ("⚙️  School Settings", self.show_settings),
        ]

        for label, cmd in nav_items:
            ctk.CTkButton(
                sidebar, text=label, anchor="w", height=36,
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"), command=cmd
            ).pack(fill="x", padx=12, pady=3)

        ctk.CTkButton(
            sidebar, text="🚪  Logout", fg_color="#B22222", hover_color="#8B0000",
            command=self.show_login_screen
        ).pack(side="bottom", fill="x", padx=14, pady=16)

        self.content = ctk.CTkFrame(self, corner_radius=10)
        self.content.pack(side="right", fill="both", expand=True, padx=12, pady=12)
        self.show_dashboard()

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    # ================= 1. DASHBOARD =================
    def show_dashboard(self):
        self.clear_content()
        cfg = get_all_settings()
        currency = cfg.get("currency", "UGX")

        ctk.CTkLabel(
            self.content, text=f"📊 Overview — {cfg.get('school_name')}",
            font=("Arial", 20, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 10))

        conn = get_connection()
        active_count = conn.execute("SELECT COUNT(*) FROM students WHERE status='ACTIVE'").fetchone()[0]
        paid_sum = conn.execute(
            "SELECT COALESCE(SUM(amount_paid),0) FROM payments WHERE academic_year=? AND term=? AND is_voided=0",
            (cfg["current_year"], cfg["current_term"])
        ).fetchone()[0]
        conn.close()

        defaulters = get_defaulters_list("ALL")
        total_arrears = sum(d["balance"] for d in defaulters)

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=20, pady=10)

        stats = [
            ("🎓 Active Students", f"{active_count}", "#1F6AA5"),
            ("💰 Collected This Term", f"{currency} {paid_sum:,.0f}", "#2E8B57"),
            ("⚠️ Pending Balances", f"{currency} {total_arrears:,.0f}", "#D2691E"),
            ("🧾 Students Owing", f"{len(defaulters)}", "#8B0000"),
        ]
        for title, val, color in stats:
            box = ctk.CTkFrame(cards, fg_color=color, corner_radius=12, height=110)
            box.pack(side="left", expand=True, fill="both", padx=6)
            ctk.CTkLabel(box, text=title, font=("Arial", 13, "bold"), text_color="white").pack(pady=(18, 4))
            ctk.CTkLabel(box, text=val, font=("Arial", 18, "bold"), text_color="white").pack()

    # ================= 2. STUDENTS =================
    def show_students(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="🎓 Student Registration (S1–S6)", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        form = ctk.CTkFrame(self.content)
        form.pack(fill="x", padx=20, pady=6)

        entries = {}
        fields = [
            ("code", "Student ID (e.g. GHS-001)"),
            ("name", "Full Name"),
            ("stream", "Stream (A/B/C)"),
            ("g_name", "Guardian Name"),
            ("g_phone", "Guardian Phone"),
            ("bursary", "Bursary Discount (0)"),
            ("arrears", "Opening Arrears (0)"),
        ]
        for idx, (key, ph) in enumerate(fields):
            e = ctk.CTkEntry(form, placeholder_text=ph, width=180)
            e.grid(row=idx // 4, column=idx % 4, padx=6, pady=6)
            entries[key] = e

        cls_var = ctk.StringVar(value="S1")
        res_var = ctk.StringVar(value="BOARDING")
        trk_var = ctk.StringVar(value="GENERAL")

        ctk.CTkOptionMenu(form, values=["S1", "S2", "S3", "S4", "S5", "S6"], variable=cls_var, width=110).grid(row=2, column=0, padx=6, pady=6)
        ctk.CTkOptionMenu(form, values=["BOARDING", "DAY"], variable=res_var, width=130).grid(row=2, column=1, padx=6, pady=6)
        ctk.CTkOptionMenu(form, values=["GENERAL", "SCIENCE", "ARTS"], variable=trk_var, width=130).grid(row=2, column=2, padx=6, pady=6)

        def save_st():
            try:
                add_student(
                    entries["code"].get(), entries["name"].get(), cls_var.get(),
                    entries["stream"].get() or "A", res_var.get(), trk_var.get(),
                    entries["g_name"].get(), entries["g_phone"].get(),
                    float(entries["bursary"].get() or 0),
                    float(entries["arrears"].get() or 0),
                    self.current_user["username"],
                )
                messagebox.showinfo("Saved", "✅ Student registered successfully!")
                self.show_students()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        ctk.CTkButton(form, text="➕ Register Student", command=save_st).grid(row=2, column=3, padx=6, pady=6)

        tree = ttk.Treeview(self.content, columns=("code", "name", "cls", "res", "trk", "phone"), show="headings", height=14)
        for col, head in [("code", "ID"), ("name", "Full Name"), ("cls", "Class"), ("res", "Residence"), ("trk", "Track"), ("phone", "Guardian Tel")]:
            tree.heading(col, text=head)
            tree.column(col, width=130)
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = get_connection()
        for r in conn.execute("SELECT * FROM students WHERE status='ACTIVE' ORDER BY id DESC").fetchall():
            tree.insert("", "end", values=(r["student_code"], r["full_name"], f"{r['class_level']} {r['stream']}", r["residence"], r["track"], r["guardian_phone"]))
        conn.close()
          # ================= 3. COLLECT FEES & CSV RECONCILE =================
    def show_payments(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="💳 Record Fees & CSV Statement Import", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        box = ctk.CTkFrame(self.content)
        box.pack(fill="x", padx=20, pady=8)

        code_e = ctk.CTkEntry(box, placeholder_text="Student ID (e.g. GHS-001)", width=180)
        code_e.grid(row=0, column=0, padx=6, pady=8)
        amt_e = ctk.CTkEntry(box, placeholder_text="Amount Paid", width=150)
        amt_e.grid(row=0, column=1, padx=6, pady=8)
        method_var = ctk.StringVar(value="CASH")
        ctk.CTkOptionMenu(box, values=["CASH", "MOBILE_MONEY", "BANK_AGENT", "BANK_TRANSFER"], variable=method_var, width=160).grid(row=0, column=2, padx=6, pady=8)
        ref_e = ctk.CTkEntry(box, placeholder_text="MoMo / Bank Ref (Optional)", width=190)
        ref_e.grid(row=0, column=3, padx=6, pady=8)

        def submit_pay():
            try:
                conn = get_connection()
                st = conn.execute("SELECT id FROM students WHERE student_code = ?", (code_e.get().strip().upper(),)).fetchone()
                conn.close()
                if not st:
                    raise ValueError("Student ID not found.")
                rcp = record_payment(st["id"], float(amt_e.get()), method_var.get(), ref_e.get(), self.current_user["username"])
                pdf_path = generate_receipt_pdf(rcp)
                messagebox.showinfo("Receipt Issued", f"✅ Payment recorded!\nReceipt: {rcp}\nSaved PDF: {pdf_path}")
                self.show_payments()
            except Exception as ex:
                messagebox.showerror("Payment Error", str(ex))

        ctk.CTkButton(box, text="🧾 Save & Generate Receipt", command=submit_pay).grid(row=1, column=0, columnspan=2, padx=6, pady=8, sticky="ew")

        def import_csv():
            path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
            if not path:
                return
            try:
                res = reconcile_csv_statements(path, self.current_user["username"])
                messagebox.showinfo("CSV Import Complete", f"✅ Matched: {res['matched']}\n⏭️ Skipped Duplicates: {res['skipped']}\n⚠️ Errors: {len(res['errors'])}")
                self.show_payments()
            except Exception as ex:
                messagebox.showerror("Import Error", str(ex))

        ctk.CTkButton(box, text="📂 Import Bank / MoMo CSV", fg_color="#2E8B57", command=import_csv).grid(row=1, column=2, columnspan=2, padx=6, pady=8, sticky="ew")

        tree = ttk.Treeview(self.content, columns=("rcp", "st", "amt", "mth", "ref", "dt", "status"), show="headings", height=13)
        for c, h in [("rcp", "Receipt No"), ("st", "Student"), ("amt", "Amount"), ("mth", "Method"), ("ref", "Reference"), ("dt", "Date"), ("status", "Status")]:
            tree.heading(c, text=h)
            tree.column(c, width=120)
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = get_connection()
        rows = conn.execute("""
            SELECT p.*, s.student_code, s.full_name FROM payments p
            JOIN students s ON p.student_id = s.id ORDER BY p.id DESC LIMIT 50
        """).fetchall()
        conn.close()
        for r in rows:
            tree.insert("", "end", values=(
                r["receipt_no"], f"{r['student_code']} - {r['full_name']}",
                f"{r['amount_paid']:,.0f}", r["payment_method"], r["external_ref"],
                r["payment_date"], "VOIDED" if r["is_voided"] else "VALID"
            ))

    # ================= 4. GATE & EXAM CLEARANCE =================
    def show_clearance(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="🪪 Gate & Examination Clearance Check", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        row = ctk.CTkFrame(self.content)
        row.pack(fill="x", padx=20, pady=8)
        code_e = ctk.CTkEntry(row, placeholder_text="Enter Student ID (e.g. GHS-001)", width=240)
        code_e.pack(side="left", padx=10, pady=10)

        result_lbl = ctk.CTkLabel(self.content, text="", font=("Arial", 15, "bold"))
        result_lbl.pack(pady=20)

        def check_status():
            conn = get_connection()
            st = conn.execute("SELECT id FROM students WHERE student_code = ?", (code_e.get().strip().upper(),)).fetchone()
            conn.close()
            if not st:
                messagebox.showerror("Not Found", "Student ID does not exist.")
                return
            s = get_student_financial_summary(st["id"])
            pdf = generate_clearance_pass_pdf(st["id"])
            status = "✅ CLEARED FOR EXAMS & GATE" if s["is_cleared"] else f"❌ HOLD — ONLY {s['percent_paid']}% PAID (Need {s['clearance_threshold']}%)"
            result_lbl.configure(
                text=f"{s['student']['full_name']} ({s['student']['class_level']})\nPaid: {s['total_paid']:,.0f} / {s['net_payable']:,.0f} ({s['percent_paid']}%)\n\n{status}\n\n📄 Pass saved: {pdf}",
                text_color="#2E8B57" if s["is_cleared"] else "#B22222"
            )

        ctk.CTkButton(row, text="🔍 Verify & Print Pass", command=check_status).pack(side="left", padx=8)

    # ================= 5. FEE STRUCTURES =================
    def show_fee_structures(self):
        self.clear_content()
        cfg = get_all_settings()
        ctk.CTkLabel(self.content, text="📋 Term Fee Structure Setup", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        form = ctk.CTkFrame(self.content)
        form.pack(fill="x", padx=20, pady=6)
        cls_v = ctk.StringVar(value="S1")
        res_v = ctk.StringVar(value="BOARDING")
        trk_v = ctk.StringVar(value="GENERAL")
        item_e = ctk.CTkEntry(form, placeholder_text="Fee Item (e.g. Tuition, Lab)", width=180)
        amt_e = ctk.CTkEntry(form, placeholder_text="Amount", width=130)

        ctk.CTkOptionMenu(form, values=["S1", "S2", "S3", "S4", "S5", "S6"], variable=cls_v, width=95).pack(side="left", padx=5, pady=8)
        ctk.CTkOptionMenu(form, values=["BOARDING", "DAY"], variable=res_v, width=115).pack(side="left", padx=5, pady=8)
        ctk.CTkOptionMenu(form, values=["GENERAL", "SCIENCE", "ARTS"], variable=trk_v, width=115).pack(side="left", padx=5, pady=8)
        item_e.pack(side="left", padx=5, pady=8)
        amt_e.pack(side="left", padx=5, pady=8)

        def save_fee():
            try:
                add_fee_item(cfg["current_year"], cfg["current_term"], cls_v.get(), res_v.get(), trk_v.get(), item_e.get(), float(amt_e.get()), self.current_user["username"])
                self.show_fee_structures()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        ctk.CTkButton(form, text="➕ Add Fee", command=save_fee).pack(side="left", padx=6)

        tree = ttk.Treeview(self.content, columns=("yr", "trm", "cls", "res", "trk", "itm", "amt"), show="headings", height=14)
        for c, h in [("yr", "Year"), ("trm", "Term"), ("cls", "Class"), ("res", "Residence"), ("trk", "Track"), ("itm", "Item"), ("amt", "Amount")]:
            tree.heading(c, text=h)
            tree.column(c, width=110)
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = get_connection()
        for r in conn.execute("SELECT * FROM fee_structures ORDER BY id DESC").fetchall():
            tree.insert("", "end", values=(r["academic_year"], r["term"], r["class_level"], r["residence"], r["track"], r["fee_item"], f"{r['amount']:,.0f}"))
        conn.close()
          # ================= 6. DEFAULTERS =================
    def show_defaulters(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="⚠️ Fee Defaulters Report", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        tree = ttk.Treeview(self.content, columns=("code", "name", "cls", "billed", "paid", "bal", "phone"), show="headings", height=16)
        for c, h in [("code", "ID"), ("name", "Student"), ("cls", "Class"), ("billed", "Net Billed"), ("paid", "Paid"), ("bal", "Balance Due"), ("phone", "Guardian Tel")]:
            tree.heading(c, text=h)
            tree.column(c, width=120)
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        for d in get_defaulters_list("ALL"):
            st = d["student"]
            tree.insert("", "end", values=(
                st["student_code"], st["full_name"], f"{st['class_level']} {st['stream']}",
                f"{d['net_payable']:,.0f}", f"{d['total_paid']:,.0f}", f"{d['balance']:,.0f}", st["guardian_phone"]
            ))

    # ================= 7. TERM / YEAR ROLLOVER =================
    def show_rollover(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="🔄 End-of-Term / End-of-Year Rollover", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)
        if self.current_user["role"] != "ADMIN":
            ctk.CTkLabel(self.content, text="🔒 Only an ADMIN can perform term or year rollovers.", text_color="red").pack(padx=20, pady=20)
            return

        frm = ctk.CTkFrame(self.content)
        frm.pack(padx=20, pady=15, anchor="w")
        yr_e = ctk.CTkEntry(frm, placeholder_text="Next Academic Year (e.g. 2026)", width=220)
        yr_e.pack(padx=15, pady=8)
        trm_v = ctk.StringVar(value="Term 2")
        ctk.CTkOptionMenu(frm, values=["Term 1", "Term 2", "Term 3"], variable=trm_v, width=220).pack(padx=15, pady=8)
        promote_v = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frm, text="🎓 End of Year: Promote Classes (S1→S6→Alumni)", variable=promote_v).pack(padx=15, pady=10)

        def run_roll():
            if not yr_e.get().strip():
                messagebox.showerror("Required", "Enter the next academic year.")
                return
            if messagebox.askyesno("Confirm Rollover", "Carry forward unpaid balances and switch active term now?"):
                rollover_term_or_year(promote_v.get(), yr_e.get().strip(), trm_v.get(), self.current_user["username"])
                messagebox.showinfo("Done", "✅ Term rollover completed!")
                self.build_main_shell()

        ctk.CTkButton(frm, text="🚀 Execute Rollover", fg_color="#D2691E", command=run_roll).pack(padx=15, pady=14)

    # ================= 8. AUDIT LOGS & VOID RECEIPT =================
    def show_audit_logs(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="🛡️ Tamper-Proof Audit Trail & Receipt Voiding", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        if self.current_user["role"] == "ADMIN":
            v_bar = ctk.CTkFrame(self.content)
            v_bar.pack(fill="x", padx=20, pady=6)
            rcp_e = ctk.CTkEntry(v_bar, placeholder_text="Receipt No (e.g. RCP-...)", width=210)
            rcp_e.pack(side="left", padx=6, pady=8)
            rsn_e = ctk.CTkEntry(v_bar, placeholder_text="Mandatory Void Reason", width=280)
            rsn_e.pack(side="left", padx=6, pady=8)

            def do_void():
                try:
                    void_payment(rcp_e.get().strip(), rsn_e.get(), self.current_user["username"])
                    messagebox.showinfo("Voided", "✅ Receipt marked VOIDED and logged.")
                    self.show_audit_logs()
                except Exception as ex:
                    messagebox.showerror("Error", str(ex))

            ctk.CTkButton(v_bar, text="🚫 Void Receipt", fg_color="#B22222", command=do_void).pack(side="left", padx=6)

        tree = ttk.Treeview(self.content, columns=("ts", "usr", "act", "det"), show="headings", height=15)
        for c, h in [("ts", "Timestamp"), ("usr", "User"), ("act", "Action"), ("det", "Details")]:
            tree.heading(c, text=h)
            tree.column(c, width=180)
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = get_connection()
        for r in conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100").fetchall():
            tree.insert("", "end", values=(r["timestamp"], r["username"], r["action"], r["details"]))
        conn.close()

    # ================= 9. BACKUP & RESTORE =================
    def show_backups(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="💾 Database Backup & Restore (USB Flash Drive)", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)

        def do_backup():
            folder = filedialog.askdirectory(title="Select Backup Folder or USB Drive")
            if folder:
                path = create_backup(folder, self.current_user["username"])
                messagebox.showinfo("Backup Saved", f"✅ Encrypted copy saved at:\n{path}")

        def do_restore():
            if self.current_user["role"] != "ADMIN":
                messagebox.showerror("Denied", "Only ADMIN can restore a database.")
                return
            fp = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")])
            if fp and messagebox.askyesno("Confirm Restore", "Overwrite current database with selected backup?"):
                restore_backup(fp, self.current_user["username"])
                messagebox.showinfo("Restored", "✅ Database restored successfully!")

        ctk.CTkButton(self.content, text="📤 Create Backup Now", width=250, height=42, command=do_backup).pack(anchor="w", padx=20, pady=12)
        ctk.CTkButton(self.content, text="📥 Restore From Backup File", width=250, height=42, fg_color="#D2691E", command=do_restore).pack(anchor="w", padx=20, pady=8)

    # ================= 10. ADMIN SETTINGS =================
    def show_settings(self):
        self.clear_content()
        ctk.CTkLabel(self.content, text="⚙️ School & System Settings", font=("Arial", 19, "bold")).pack(anchor="w", padx=20, pady=12)
        if self.current_user["role"] != "ADMIN":
            ctk.CTkLabel(self.content, text="🔒 Only ADMIN users can modify school settings.", text_color="red").pack(padx=20, pady=20)
            return

        cfg = get_all_settings()
        frm = ctk.CTkScrollableFrame(self.content, width=650, height=460)
        frm.pack(fill="both", expand=True, padx=20, pady=8)

        labels = [
            ("school_name", "🏫 School Name"),
            ("school_motto", "📜 School Motto"),
            ("school_address", "📍 Address"),
            ("school_phone", "📞 Telephone"),
            ("currency", "💱 Currency Symbol (e.g. UGX)"),
            ("current_year", "📅 Current Academic Year"),
            ("current_term", "🗓️ Current Term (Term 1 / Term 2 / Term 3)"),
            ("clearance_threshold_percent", "🪪 Exam/Gate Clearance Minimum (%)"),
            ("receipt_footer", "🧾 Receipt Footer Note"),
        ]
        inputs = {}
        for key, lbl in labels:
            ctk.CTkLabel(frm, text=lbl, font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
            ent = ctk.CTkEntry(frm, width=480)
            ent.insert(0, cfg.get(key, ""))
            ent.pack(anchor="w", padx=12, pady=(0, 6))
            inputs[key] = ent

        def save_cfg():
            update_settings({k: e.get() for k, e in inputs.items()}, self.current_user["username"])
            messagebox.showinfo("Settings Saved", "✅ School settings updated!")
            self.build_main_shell()

        ctk.CTkButton(frm, text="💾 Save All School Settings", fg_color="#2E8B57", height=38, command=save_cfg).pack(anchor="w", padx=12, pady=14)

        # Password Change Section
        ctk.CTkLabel(frm, text="🔑 Reset User Password (admin / bursar)", font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(14, 4))
        p_row = ctk.CTkFrame(frm, fg_color="transparent")
        p_row.pack(anchor="w", padx=12, pady=4)
        u_sel = ctk.StringVar(value="bursar")
        ctk.CTkOptionMenu(p_row, values=["admin", "bursar"], variable=u_sel, width=130).pack(side="left", padx=(0, 8))
        new_p = ctk.CTkEntry(p_row, placeholder_text="New Password", show="*", width=200)
        new_p.pack(side="left", padx=6)

        def upd_pass():
            if len(new_p.get()) < 4:
                messagebox.showerror("Weak Password", "Use at least 4 characters.")
                return
            change_user_password(u_sel.get(), new_p.get(), self.current_user["username"])
            messagebox.showinfo("Updated", f"✅ Password updated for {u_sel.get()}!")

        ctk.CTkButton(p_row, text="Update Password", command=upd_pass).pack(side="left", padx=6)


if __name__ == "__main__":
    app = SchoolFeesApp()
    app.mainloop()
      
