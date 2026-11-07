import os
import secrets

from shop.checkout import hash_password, verify_password


def clean_username(raw):
    text = str(raw or "").strip().lower()
    if not 2 <= len(text) <= 32 or any(ch.isspace() for ch in text):
        return ""
    return text


def save_staff(conn, username, password, role="staff"):
    conn.execute(
        """
        insert into staff (username, password_hash, role, enabled)
        values (?, ?, ?, 1)
        on conflict(username) do update set
            password_hash = excluded.password_hash,
            role = excluded.role,
            enabled = 1
        """,
        (username, hash_password(password), role if role in {"admin", "staff"} else "staff"),
    )


def set_staff_enabled(conn, username, enabled: bool) -> bool:
    name = clean_username(username)
    if not name:
        return False
    cur = conn.execute(
        "update staff set enabled = ? where username = ?",
        (1 if enabled else 0, name),
    )
    if not enabled:
        conn.execute("delete from staff_sessions where username = ?", (name,))
    return cur.rowcount > 0


def reset_staff_password(conn, username, password) -> bool:
    name = clean_username(username)
    if not name or len(str(password or "")) < 8:
        return False
    cur = conn.execute(
        "update staff set password_hash = ? where username = ?",
        (hash_password(password), name),
    )
    if cur.rowcount:
        conn.execute("delete from staff_sessions where username = ?", (name,))
        return True
    return False


def ensure_admin(conn):
    username = clean_username(os.environ.get("ADMIN_USER", "admin")) or "admin"
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        return
    found = conn.execute("select username from staff where username = ?", (username,)).fetchone()
    if found:
        return
    save_staff(conn, username, password, "admin")


def authenticate(conn, username, password):
    name = clean_username(username)
    if not name or not password:
        return None
    row = conn.execute("select * from staff where username = ?", (name,)).fetchone()
    if row is None or not row["enabled"] or not verify_password(password, row["password_hash"]):
        return None
    return row


def start_session(conn, username):
    token = secrets.token_urlsafe(32)
    conn.execute(
        "insert into staff_sessions (token, username) values (?, ?)",
        (token, username),
    )
    return token


def staff_from_token(conn, token):
    if not token:
        return None
    return conn.execute(
        """
        select staff.username, staff.role, staff.enabled
        from staff_sessions
        join staff on staff.username = staff_sessions.username
        where staff_sessions.token = ?
        """,
        (token,),
    ).fetchone()


def is_admin_role(staff_row) -> bool:
    return bool(staff_row) and str(staff_row["role"] or "") == "admin"
