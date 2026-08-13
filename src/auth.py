import os
import sqlite3
import hashlib
import hmac
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, List
import jwt

from src import config

def get_db_connection():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{hashed.hex()}"

def verify_password(password: str, hashed_str: str) -> bool:
    try:
        salt_hex, hash_hex = hashed_str.split(':')
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_quotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        usage_date TEXT NOT NULL,
        used_count INTEGER DEFAULT 0,
        daily_limit INTEGER DEFAULT 20,
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(user_id, usage_date)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS failed_logins (
        username TEXT PRIMARY KEY,
        failed_count INTEGER DEFAULT 0,
        locked_until TIMESTAMP
    )
    """)
    conn.commit()

    # 相容性資料庫欄位遷移 (Migration)
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if "status" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
        conn.commit()

    # 建立與升級預設管理員與測試帳號
    for admin_name, admin_pass in config.ADMIN_USERS_CONFIG.items():
        cursor.execute("SELECT id FROM users WHERE username = ?", (admin_name,))
        if not cursor.fetchone():
            default_pass = hash_password(admin_pass)
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, 'admin', 'approved')",
                (admin_name, default_pass)
            )
        else:
            cursor.execute("UPDATE users SET role = 'admin', status = 'approved' WHERE username = ?", (admin_name,))

    cursor.execute("SELECT id FROM users WHERE username = ?", ("demo",))
    if not cursor.fetchone():
        demo_pass = hash_password("demo123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, 'user', 'approved')",
            ("demo", demo_pass)
        )
    else:
        cursor.execute("UPDATE users SET status = 'approved' WHERE username = 'demo'")

    conn.commit()
    conn.close()

def record_failed_login(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT failed_count FROM failed_logins WHERE username = ?", (username,))
    row = cursor.fetchone()
    now = datetime.now()
    if not row:
        cursor.execute(
            "INSERT INTO failed_logins (username, failed_count, locked_until) VALUES (?, 1, NULL)",
            (username,)
        )
    else:
        new_count = row["failed_count"] + 1
        locked_until = None
        if new_count >= 5:
            locked_until = (now + timedelta(minutes=15)).isoformat()
        cursor.execute(
            "UPDATE failed_logins SET failed_count = ?, locked_until = ? WHERE username = ?",
            (new_count, locked_until, username)
        )
    conn.commit()
    conn.close()

def clear_failed_login(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM failed_logins WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def check_account_locked(username: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT failed_count, locked_until FROM failed_logins WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row["locked_until"]:
        return False
    try:
        locked_until = datetime.fromisoformat(row["locked_until"])
        if datetime.now() < locked_until:
            return True
        else:
            clear_failed_login(username)
            return False
    except Exception:
        return False

def register_user(username: str, password: str, role: str = 'user', status: str = 'pending') -> Tuple[bool, str]:
    if not username or not password:
        return False, "帳號與密碼不能為空"
    username = username.strip().lower()
    if len(password) < 4:
        return False, "密碼長度至少需 4 個字元"
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_pass = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, ?, ?)",
            (username, hashed_pass, role, status)
        )
        conn.commit()
        return True, "註冊成功！帳號現處於待審核狀態，請等待管理員核准開通。"
    except sqlite3.IntegrityError:
        return False, "使用者名稱已存在"
    except Exception as e:
        return False, f"註冊失敗: {str(e)}"
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Tuple[Optional[Dict[str, Any]], str]:
    username = username.strip().lower()
    
    if check_account_locked(username):
        return None, "登入失敗次數過多，該帳號已被暫時鎖定 15 分鐘，請稍後再試。"
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, role, status FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not verify_password(password, row["password_hash"]):
        record_failed_login(username)
        return None, "帳號或密碼錯誤"
        
    clear_failed_login(username)
    status = row["status"] if "status" in row.keys() and row["status"] else "approved"
    
    if status == "pending":
        return None, "帳號已被建立，但目前尚在等待管理員審核中，開通後方可使用。"
    elif status == "rejected":
        return None, "帳號已被管理員停用或拒絕存取。"
        
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "status": status
    }, "登入成功"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload
    except Exception:
        return None

def get_today_str() -> str:
    return date.today().isoformat()

def get_user_quota_info(user_id: int, username: str, role: str) -> Dict[str, Any]:
    today = get_today_str()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    limit = 99999 if role == "admin" else config.DEFAULT_DAILY_LIMIT
    
    cursor.execute(
        "SELECT used_count, daily_limit FROM daily_quotas WHERE user_id = ? AND usage_date = ?",
        (user_id, today)
    )
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO daily_quotas (user_id, usage_date, used_count, daily_limit) VALUES (?, ?, ?, ?)",
            (user_id, today, 0, limit)
        )
        conn.commit()
        used = 0
    else:
        used = row["used_count"]
        limit = row["daily_limit"]
        
    conn.close()
    
    remaining = max(0, limit - used) if role != "admin" else 99999
    return {
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "is_unlimited": (role == "admin")
    }

def check_and_consume_quota(user_id: int, username: str, role: str) -> Tuple[bool, Dict[str, Any]]:
    today = get_today_str()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    limit = 99999 if role == "admin" else config.DEFAULT_DAILY_LIMIT
    
    cursor.execute(
        "SELECT used_count, daily_limit FROM daily_quotas WHERE user_id = ? AND usage_date = ?",
        (user_id, today)
    )
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO daily_quotas (user_id, usage_date, used_count, daily_limit) VALUES (?, ?, ?, ?)",
            (user_id, today, 1, limit)
        )
        conn.commit()
        conn.close()
        return True, {
            "used": 1,
            "limit": limit,
            "remaining": max(0, limit - 1) if role != "admin" else 99999,
            "is_unlimited": (role == "admin")
        }
    
    used = row["used_count"]
    limit = row["daily_limit"]
    
    if role != "admin" and used >= limit:
        conn.close()
        return False, {
            "used": used,
            "limit": limit,
            "remaining": 0,
            "is_unlimited": False
        }
        
    cursor.execute(
        "UPDATE daily_quotas SET used_count = used_count + 1 WHERE user_id = ? AND usage_date = ?",
        (user_id, today)
    )
    conn.commit()
    conn.close()
    
    new_used = used + 1
    return True, {
        "used": new_used,
        "limit": limit,
        "remaining": max(0, limit - new_used) if role != "admin" else 99999,
        "is_unlimited": (role == "admin")
    }

def get_pending_users() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, status, created_at FROM users WHERE status = 'pending' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "status": row["status"],
            "created_at": str(row["created_at"])
        }
        for row in rows
    ]

def update_user_status(username: str, status: str) -> Tuple[bool, str]:
    username = username.strip().lower()
    status = status.strip().lower()
    if status not in ["approved", "rejected", "pending"]:
        return False, "無效的狀態值"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    if count > 0:
        return True, f"已成功更新使用者 '{username}' 狀態為 '{status}'"
    return False, f"找不到使用者 '{username}'"

def delete_user(username: str) -> Tuple[bool, str]:
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, f"找不到使用者 '{username}'"
    user_id = row["id"]
    cursor.execute("DELETE FROM daily_quotas WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM failed_logins WHERE username = ?", (username,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True, f"已成功刪除使用者 '{username}'"

def get_all_users() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, role, status, created_at 
        FROM users 
        ORDER BY 
            CASE 
                WHEN role = 'admin' THEN 1
                WHEN status = 'pending' THEN 2
                ELSE 3
            END ASC,
            id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "status": row["status"] if "status" in row.keys() and row["status"] else "approved",
            "created_at": str(row["created_at"])[:19]
        }
        for row in rows
    ]

def change_user_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    username = username.strip().lower()
    if not new_password or len(new_password) < 4:
        return False, "新密碼長度至少需 4 個字元"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, f"找不到使用者 '{username}'"
    if not verify_password(old_password, row["password_hash"]):
        conn.close()
        return False, "舊密碼不正確"
    new_hashed = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hashed, username))
    conn.commit()
    conn.close()
    return True, "密碼更新成功！"

def reset_user_password_by_admin(username: str, new_password: str) -> Tuple[bool, str]:
    username = username.strip().lower()
    if not new_password or len(new_password) < 4:
        return False, "新密碼長度至少需 4 個字元"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, f"找不到使用者 '{username}'"
    new_hashed = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hashed, username))
    conn.commit()
    conn.close()
    return True, f"已成功重置使用者 '{username}' 的密碼"

def update_user_role(username: str, role: str) -> Tuple[bool, str]:
    username = username.strip().lower()
    role = role.strip().lower()
    if role not in ["admin", "user"]:
        return False, "無效的角色 (只能是 admin 或 user)"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    if count > 0:
        return True, f"已成功將使用者 '{username}' 權限變更為 '{role}'"
    return False, f"找不到使用者 '{username}'"
