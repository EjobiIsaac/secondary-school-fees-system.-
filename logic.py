import csv
import uuid
from datetime import datetime
from database import get_connection, hash_password, log_audit
from settings import get_setting


def authenticate_user(username: str, password: str):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
        (username.strip(), hash_password(password)),
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def add_student(
    student_code: str,
    full_name: str,
    class_level: str,
    stream: str,
    residence: str,
    track: str,
    guardian_name: str,
    guardian_phone: str,
    bursary_discount: float,
    carried_forward_balance: float,
    username: str,
):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO students (
            student_code, full_name, class_level, stream, residence, track,
            guardian_name, guardian_phone, bursary_discount, carried_forward_balance
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_code.strip().upper(),
            full_name.strip(),
            class_level.upper(),
            stream.strip().upper(),
            residence.upper(),
            track.upper(),
            guardian_name.strip(),
            guardian_phone.strip(),
            float(bursary_discount or 0),
            float(carried_forward_balance or 0),
        ),
    )
    conn.commit()
    conn.close()
    log_audit(username, "ADD_STUDENT", f"Registered {student_code.upper()} - {full_name}")


def add_fee_item(
    academic_year: str,
    term: str,
    class_level: str,
    residence: str,
    track: str,
    fee_item: str,
    amount: float,
    username: str,
):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO fee_structures (academic_year, term, class_level, residence, track, fee_item, amount)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (academic_year, term, class_level.upper(), residence.upper(), track.upper(), fee_item.strip(), float(amount)),
    )
    conn.commit()
    conn.close()
    log_audit(username, "ADD_FEE_ITEM", f"{class_level} {residence} ({track}) - {fee_item}: {amount}")


def get_student_financial_summary(student_id: int, academic_year: str = None, term: str = None) -> dict:
    academic_year = academic_year or get_setting("current_year", "2026")
    term = term or get_setting("current_term", "Term 1")
    threshold_pct = float(get_setting("clearance_threshold_percent", "75"))

    conn = get_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        raise ValueError("Student not found")

    # Match applicable fees (specific track OR GENERAL track for that class & residence)
    fee_rows = conn.execute(
        """
        SELECT fee_item, amount FROM fee_structures
        WHERE academic_year = ? AND term = ? AND class_level = ? AND residence = ?
        AND (track = ? OR track = 'GENERAL')
        """,
        (academic_year, term, student["class_level"], student["residence"], student["track"]),
    ).fetchall()

    term_billed = sum(r["amount"] for r in fee_rows)
    bursary = float(student["bursary_discount"] or 0)
    arrears = float(student["carried_forward_balance"] or 0)
    net_payable = max(0.0, (term_billed - bursary) + arrears)

    pay_row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_paid), 0) AS total_paid FROM payments
        WHERE student_id = ? AND academic_year = ? AND term = ? AND is_voided = 0
        """,
        (student_id, academic_year, term),
    ).fetchone()
    total_paid = float(pay_row["total_paid"])
    balance = net_payable - total_paid

    pct_paid = (total_paid / net_payable * 100.0) if net_payable > 0 else 100.0
    is_cleared = pct_paid >= threshold_pct

    conn.close()
    return {
        "student": dict(student),
        "academic_year": academic_year,
        "term": term,
        "fee_breakdown": [dict(r) for r in fee_rows],
        "term_billed": term_billed,
        "bursary_discount": bursary,
        "carried_forward": arrears,
        "net_payable": net_payable,
        "total_paid": total_paid,
        "balance": balance,
        "percent_paid": round(pct_paid, 1),
        "clearance_threshold": threshold_pct,
        "is_cleared": is_cleared,
    }


def record_payment(
    student_id: int,
    amount_paid: float,
    payment_method: str,
    external_ref: str,
    username: str,
    academic_year: str = None,
    term: str = None,
) -> str:
    if amount_paid <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    academic_year = academic_year or get_setting("current_year", "2026")
    term = term or get_setting("current_term", "Term 1")
    receipt_no = f"RCP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    pay_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO payments (
            receipt_no, student_id, academic_year, term, amount_paid,
            payment_method, external_ref, payment_date, recorded_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (receipt_no, student_id, academic_year, term, float(amount_paid), payment_method, external_ref.strip(), pay_date, username),
    )
    conn.commit()
    conn.close()
    log_audit(username, "RECORD_PAYMENT", f"Receipt {receipt_no}: StudentID={student_id}, Amount={amount_paid}")
    return receipt_no


def void_payment(receipt_no: str, reason: str, admin_username: str):
    if not reason.strip():
        raise ValueError("A void reason is mandatory for audit compliance.")
    conn = get_connection()
    conn.execute(
        "UPDATE payments SET is_voided = 1, void_reason = ? WHERE receipt_no = ?",
        (reason.strip(), receipt_no),
    )
    conn.commit()
    conn.close()
    log_audit(admin_username, "VOID_PAYMENT", f"Voided {receipt_no}. Reason: {reason}")


def reconcile_csv_statements(csv_filepath: str, username: str) -> dict:
    """
    Imports Bank/Mobile Money CSV with columns: student_code, amount, payment_method, reference
    Matches against student_code and records un-imported transactions safely.
    """
    matched, skipped, errors = 0, 0, []
    conn = get_connection()

    with open(csv_filepath, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            code = (row.get("student_code") or "").strip().upper()
            ref = (row.get("reference") or "").strip()
            method = (row.get("payment_method") or "MOBILE_MONEY").strip().upper()
            try:
                amount = float(row.get("amount") or 0)
            except ValueError:
                errors.append(f"Row {idx}: Invalid amount")
                continue

            if not code or amount <= 0:
                errors.append(f"Row {idx}: Missing student_code or non-positive amount")
                continue

            # Prevent duplicate reference import
            if ref:
                existing = conn.execute(
                    "SELECT id FROM payments WHERE external_ref = ? AND is_voided = 0", (ref,)
                ).fetchone()
                if existing:
                    skipped += 1
                    continue

            student = conn.execute("SELECT id FROM students WHERE student_code = ?", (code,)).fetchone()
            if not student:
                errors.append(f"Row {idx}: Unknown student_code '{code}'")
                continue

            record_payment(student["id"], amount, method, ref, username)
            matched += 1

    conn.close()
    log_audit(username, "CSV_RECONCILE", f"Imported {matched}, Skipped {skipped}, Errors {len(errors)}")
    return {"matched": matched, "skipped": skipped, "errors": errors}


def get_defaulters_list(class_filter: str = "ALL") -> list:
    conn = get_connection()
    if class_filter == "ALL":
        students = conn.execute("SELECT id FROM students WHERE status = 'ACTIVE'").fetchall()
    else:
        students = conn.execute(
            "SELECT id FROM students WHERE status = 'ACTIVE' AND class_level = ?", (class_filter,)
        ).fetchall()
    conn.close()

    defaulters = []
    for s in students:
        summary = get_student_financial_summary(s["id"])
        if summary["balance"] > 0:
            defaulters.append(summary)
    return sorted(defaulters, key=lambda x: x["balance"], reverse=True)


def rollover_term_or_year(promote_classes: bool, next_year: str, next_term: str, admin_username: str):
    """
    Carries forward unpaid balances to the new term.
    If promote_classes=True (end of year), moves S1->S2..S5->S6, and archives S4/S6 leavers if desired or S6->ALUMNI.
    """
    promotion_map = {"S1": "S2", "S2": "S3", "S3": "S4", "S4": "S5", "S5": "S6", "S6": "ALUMNI"}
    conn = get_connection()
    active_students = conn.execute("SELECT * FROM students WHERE status = 'ACTIVE'").fetchall()

    for st in active_students:
        summary = get_student_financial_summary(st["id"])
        new_arrears = max(0.0, summary["balance"])
        new_class = st["class_level"]
        new_status = st["status"]

        if promote_classes:
            new_class = promotion_map.get(st["class_level"], st["class_level"])
            if new_class == "ALUMNI":
                new_status = "ALUMNI"

        conn.execute(
            "UPDATE students SET carried_forward_balance = ?, class_level = ?, status = ? WHERE id = ?",
            (new_arrears, new_class, new_status, st["id"]),
        )

    conn.execute("UPDATE settings SET value = ? WHERE key = 'current_year'", (next_year,))
    conn.execute("UPDATE settings SET value = ? WHERE key = 'current_term'", (next_term,))
    conn.commit()
    conn.close()
    log_audit(
        admin_username,
        "TERM_ROLLOVER",
  
