import os
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from database import get_connection
from settings import get_all_settings
from logic import get_student_financial_summary

OUTPUT_DIR = "generated_docs"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_receipt_pdf(receipt_no: str) -> str:
    ensure_output_dir()
    cfg = get_all_settings()
    currency = cfg.get("currency", "UGX")

    conn = get_connection()
    pay = conn.execute("SELECT * FROM payments WHERE receipt_no = ?", (receipt_no,)).fetchone()
    if not pay:
        conn.close()
        raise ValueError(f"Receipt {receipt_no} not found.")
    conn.close()

    summary = get_student_financial_summary(pay["student_id"], pay["academic_year"], pay["term"])
    st = summary["student"]

    filepath = os.path.join(OUTPUT_DIR, f"{receipt_no}.pdf")
    c = canvas.Canvas(filepath, pagesize=A5)
    width, height = A5
    y = height - 35

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, cfg.get("school_name", "SECONDARY SCHOOL"))
    y -= 15
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width / 2, y, cfg.get("school_motto", ""))
    y -= 13
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, f"{cfg.get('school_address', '')} | Tel: {cfg.get('school_phone', '')}")
    y -= 18

    c.line(25, y, width - 25, y)
    y -= 18
    c.setFont("Helvetica-Bold", 11)
    status_label = "OFFICIAL FEES RECEIPT (VOIDED)" if pay["is_voided"] else "OFFICIAL FEES RECEIPT"
    c.drawCentredString(width / 2, y, status_label)
    y -= 20
          details = [
        ("Receipt No:", pay["receipt_no"]),
        ("Date:", pay["payment_date"]),
        ("Student Name:", f"{st['full_name']} ({st['student_code']})"),
        ("Class / Category:", f"{st['class_level']} {st['stream']} - {st['residence']} ({st['track']})"),
        ("Academic Term:", f"{pay['academic_year']} - {pay['term']}"),
        ("Payment Method:", f"{pay['payment_method']} {('[' + pay['external_ref'] + ']') if pay['external_ref'] else ''}"),
    ]
    for label, val in details:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(135, y, str(val))
        y -= 16

    y -= 6
    c.line(25, y, width - 25, y)
    y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, y, f"AMOUNT PAID NOW: {currency} {pay['amount_paid']:,.0f}")
    y -= 18
    c.setFont("Helvetica", 9)
    c.drawString(30, y, f"Total Term Payable: {currency} {summary['net_payable']:,.0f}")
    y -= 15
    c.drawString(30, y, f"Total Paid to Date: {currency} {summary['total_paid']:,.0f}")
    y -= 15
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, y, f"OUTSTANDING BALANCE: {currency} {summary['balance']:,.0f}")
    y -= 18

    clearance_text = "CLEARED FOR EXAMS & GATE" if summary["is_cleared"] else f"NOT CLEARED (Min {summary['clearance_threshold']}%)"
    c.drawString(30, y, f"Clearance Status: {clearance_text}")
    y -= 28

    c.setFont("Helvetica", 8)
    c.drawString(30, y, f"Issued By: {pay['recorded_by']}    Signature: ______________________")
    y -= 20
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, y, cfg.get("receipt_footer", ""))

    c.save()
    return filepath


def generate_clearance_pass_pdf(student_id: int) -> str:
    ensure_output_dir()
    cfg = get_all_settings()
    currency = cfg.get("currency", "UGX")
    summary = get_student_financial_summary(student_id)
    st = summary["student"]

    filepath = os.path.join(OUTPUT_DIR, f"CLEARANCE_{st['student_code']}.pdf")
    c = canvas.Canvas(filepath, pagesize=A5)
    width, height = A5
    y = height - 40

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, cfg.get("school_name", "SECONDARY SCHOOL"))
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, y, "EXAMINATION & GATE CLEARANCE PASS")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(35, y, f"Student: {st['full_name']} ({st['student_code']})")
    y -= 18
    c.drawString(35, y, f"Class: {st['class_level']} {st['stream']} | {st['residence']} | {st['track']}")
    y -= 18
    c.drawString(35, y, f"Term: {summary['academic_year']} - {summary['term']}")
    y -= 18
    c.drawString(35, y, f"Paid: {currency} {summary['total_paid']:,.0f} / {currency} {summary['net_payable']:,.0f} ({summary['percent_paid']}%)")
    y -= 28

    c.setFont("Helvetica-Bold", 14)
    verdict = "STATUS: CLEARED TO ENTER" if summary["is_cleared"] else "STATUS: HOLD - REFER TO BURSAR"
    c.drawCentredString(width / 2, y, verdict)

    c.save()
    return filepath
  
