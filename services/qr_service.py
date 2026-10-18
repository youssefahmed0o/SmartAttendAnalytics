import sqlite3
import secrets
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database.db"

import random
import string
# ... باقي الاستيرادات الموجودة لديك

def generate_qr_token(lecture_id, valid_seconds=30):
    """توليد مدة 30 ثانية للمحاضرة QR توليد رمز"""
    # توليد 6 حروف وأرقام عشوائية بدلاً من التوكن الطويل
    characters = string.ascii_letters + string.digits
    token = ''.join(random.choices(characters, k=6))
    
    expires_at = (datetime.now() + timedelta(seconds=valid_seconds)).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO qr_tokens (lecture_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (lecture_id, token, expires_at)
        )
    return token


def verify_qr_token(lecture_id, token):
    """التحقق من صلاحية رمز الـ QR الجماعي للطلاب في المدرج خلال فترته الزمنية."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        # البحث عن أحدث رمز تم توليده لهذه المحاضرة ويطابق القيمة المدخلة
        record = conn.execute(
            """
            SELECT * FROM qr_tokens
            WHERE lecture_id = ? AND token_hash = ?
            ORDER BY id DESC LIMIT 1
            """,
            (lecture_id, token)
        ).fetchone()

        if not record:
            return False, "رمز الـ QR غير صحيح."

        # التحقق من توقيت الصلاحية (هل الكود ضمن نافذة الـ 30 ثانية الحالية؟)
        now = datetime.now().isoformat()
        if record["expires_at"] < now:
            return False, "انتهت صلاحية هذا الرمز، يرجى إدخال الرمز الجديد الظاهر على الشاشة."

        return True, "الرمز صالح."
