from database import get_connection, log_audit, hash_password


def get_all_settings() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def update_settings(updates: dict, admin_username: str):
    conn = get_connection()
    for key, value in updates.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value).strip()),
        )
    conn.commit()
    conn.close()
    log_audit(admin_username, "UPDATE_SETTINGS", f"Updated keys: {', '.join(updates.keys())}")


def change_user_password(target_username: str, new_password: str, admin_username: str):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (hash_password(new_password), target_username),
    )
    conn.commit()
    conn.close()
    log_audit(admin_username, "PASSWORD_CHANGE", f"Changed password for user '{target_username}'")
  
