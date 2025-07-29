from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class InterviewMetrics(BaseModel):
    clarity: List[float] = Field(default_factory=list)
    technical_accuracy: List[float] = Field(default_factory=list)
    communication: List[float] = Field(default_factory=list)
    confidence: List[float] = Field(default_factory=list)
    pace: List[float] = Field(default_factory=list)
    filler_words: List[float] = Field(default_factory=list)

class InterviewState(BaseModel):
    interview_id: str
    user_id: str
    interview_type: str
    level: str
    current_phase: str = "intro"
    current_question: str = ""
    question_history: List[Dict] = Field(default_factory=list)
    user_responses: List[Dict] = Field(default_factory=list)
    feedback: List[Dict] = Field(default_factory=list)
    metrics: InterviewMetrics = Field(default_factory=InterviewMetrics)
    conversation_context: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    resume_text: Optional[str] = None
    resume_data: Optional[Dict] = None
