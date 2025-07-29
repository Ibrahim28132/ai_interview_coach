from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

class InterviewHistory(BaseModel):
    interview_id: str
    date: datetime
    interview_type: str
    score: float
    feedback_summary: str

class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    target_roles: List[str]
    current_level: str
    skills: List[str]
    interview_history: List[InterviewHistory] = []
    preferences: Dict[str, str] = {}
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def update_after_interview(self, interview_result: Dict):
        self.interview_history.append(
            InterviewHistory(
                interview_id=interview_result["interview_id"],
                date=datetime.now(),
                interview_type=interview_result["interview_type"],
                score=interview_result.get("score", 0),
                feedback_summary=interview_result.get("overview", "")
            )
        )
        self.updated_at = datetime.now()
        new_skills = set(interview_result.get("new_skills", []))
        self.skills = list(set(self.skills).union(new_skills))