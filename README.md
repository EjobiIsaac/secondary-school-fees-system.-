# 🏫 Secondary School Fees Payment & Management System

An offline-first Windows desktop application (`.exe`) built specifically for **Secondary Schools (S1–S6)** to manage tuition, boarding, lab fees, mobile money/bank reconciliation, receipts, and exam clearance.

## ✨ Key Features
* **🎓 Secondary School Fee Categories:** Supports O-Level (`S1–S4`) & A-Level (`S5–S6`), `Day` vs. `Boarding`, `Science` vs. `Arts` combinations, bursaries, and carried-forward arrears.
* **💳 Multi-Channel Payments & CSV Reconciliation:** Record Cash, Mobile Money, or Bank Agent payments, or import bank/mobile money CSV statements to auto-match transactions by Student Code.
* **🧾 Instant PDF Receipts & Gate/Exam Clearance:** Print official A5 receipts and verify student clearance status against an admin-configured minimum payment percentage.
* **🔄 Term & Year Rollover:** Automatically carries unpaid balances forward to the next term and promotes classes (`S1 -> S6 -> Alumni`) at year-end.
* **🛡️ Tamper-Proof Audit Trail & Role Security:** Separate `ADMIN` and `BURSAR` logins. Receipts cannot be deleted—only voided with a mandatory audit reason.
* **⚙️ Customizable School Settings:** Admins can update school name, motto, contact details, currency (`UGX`), active term/year, and clearance thresholds anytime.
* **💾 One-Click USB Backup & Restore:** Safeguard financial records to a flash drive or local folder.

---

## 🔐 Default Login Credentials
*(Change these immediately inside the **Settings** tab after first login)*
* **Administrator:** Username `admin` | Password `admin123`
* **School Bursar:** Username `bursar` | Password `bursar123`

---

## 📥 How to Download the Windows `.exe`
1. Open the **Releases** section on the right side (or bottom on mobile) of this GitHub repository.
2. Download **`SchoolFeesManager.exe`** from the latest release.
3. Double-click to run on any Windows 10/11 PC—no internet or extra database installation required.

---

## 📄 CSV Statement Import Format
To bulk-import bank or mobile money statements, upload a `.csv` file with these exact column headers:
```csv
student_code,amount,payment_method,reference
GHS-001,500000,MOBILE_MONEY,MOMO-8849201
GHS-002,750000,BANK_AGENT,BNK-5541209
```
