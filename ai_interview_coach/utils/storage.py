import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from config import Config
from models.user_profile import UserProfile

class InterviewStorage:
    def __init__(self):
        self.db_path = Config.DB_PATH
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interviews (
                    interview_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    interview_data TEXT,
                    created_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            conn.commit()

    def save_user_profile(self, profile: UserProfile):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, profile_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                profile.user_id,
                profile.model_dump_json(),
                profile.created_at.isoformat(),
                profile.updated_at.isoformat()
            ))
            conn.commit()

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT profile_data FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                return UserProfile.model_validate_json(result[0])
        return None

    def save_interview(self, interview_id: str, user_id: str, data: Dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interviews 
                (interview_id, user_id, interview_data, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                interview_id,
                user_id,
                json.dumps(data),
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_user_interviews(self, user_id: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT interview_data FROM interviews 
                WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,))
            return [json.loads(row[0]) for row in cursor.fetchall()]