import os
import pytest
import database
from settings import update_settings, get_setting
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
from backup import create_backup


@pytest.fixture(autouse=True)
def clean_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_school.db")
    monkeypatch.setattr(database, "DB_NAME", test_db)
    database.init_db()
    yield
    def test_full_secondary_school_workflow(tmp_path):
    admin = authenticate_user("admin", "admin123")
    assert admin is not None and admin["role"] == "ADMIN"

    update_settings(
        {"school_name": "GOMA HIGH SCHOOL", "clearance_threshold_percent": "70"},
        "admin",
    )
    assert get_setting("school_name") == "GOMA HIGH SCHOOL"

    add_fee_item("2026", "Term 1", "S3", "BOARDING", "GENERAL", "Tuition", 800000, "admin")
    add_fee_item("2026", "Term 1", "S3", "BOARDING", "SCIENCE", "Lab Fee", 100000, "admin")

    add_student(
        "GHS-001", "Mukasa Brian", "S3", "A", "BOARDING",
        "SCIENCE", "Mr. Mukasa", "0770000001", 100000, 0, "bursar"
    )

    conn = database.get_connection()
    row = conn.execute("SELECT id FROM students WHERE student_code = 'GHS-001'").fetchone()
    st_id = row["id"]
    conn.close()

    summary = get_student_financial_summary(st_id)
    assert summary["net_payable"] == 800000
    assert summary["is_cleared"] is False

    rcp = record_payment(st_id, 600000, "MOBILE_MONEY", "MOMO-998877", "bursar")
    summary_after = get_student_financial_summary(st_id)
    assert summary_after["balance"] == 200000
    assert summary_after["is_cleared"] is True

    rcp_pdf = generate_receipt_pdf(rcp)
    pass_pdf = generate_clearance_pass_pdf(st_id)
    assert os.path.exists(rcp_pdf)
    assert os.path.exists(pass_pdf)

    csv_file = tmp_path / "momo_statement.csv"
    csv_file.write_text("student_code,amount,payment_method,reference\nGHS-001,200000,BANK_AGENT,BNK-1122\n")
    res = reconcile_csv_statements(str(csv_file), "bursar")
    assert res["matched"] == 1
    assert get_student_financial_summary(st_id)["balance"] == 0

    void_payment(rcp, "Duplicate entry test", "admin")
    assert len(get_defaulters_list("S3")) == 1

    rollover_term_or_year(False, "2026", "Term 2", "admin")
    assert get_setting("current_term") == "Term 2"

    bkp = create_backup(str(tmp_path / "backups"), "admin")
    assert os.path.exists(bkp)
    
