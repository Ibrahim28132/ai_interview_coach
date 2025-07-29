import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import uuid
from config import Config


class FileStorage:
    def __init__(self):
        self.storage_path = Path(Config.STORAGE_DIR) / "interviews"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, interview_id: str) -> Path:
        return self.storage_path / f"{interview_id}.json"

    def save_interview(self, interview_data: Dict) -> bool:
        try:
            file_path = self._get_file_path(interview_data['interview_id'])
            with open(file_path, 'w') as f:
                json.dump(interview_data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving interview: {e}")
            return False

    def load_interview(self, interview_id: str) -> Dict:
        try:
            file_path = self._get_file_path(interview_id)
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading interview: {e}")
            return None

    def get_user_interviews(self, user_id: str) -> List[Dict]:
        interviews = []
        for file in self.storage_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('user_id') == user_id:
                        interviews.append({
                            'interview_id': data['interview_id'],
                            'interview_type': data['interview_type'],
                            'level': data['level'],
                            'start_time': data['start_time'],
                            'score': data.get('overall_score', 0)
                        })
            except Exception as e:
                print(f"Error reading file {file}: {e}")
        return sorted(interviews, key=lambda x: x['start_time'], reverse=True)