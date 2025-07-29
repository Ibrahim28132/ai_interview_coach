from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, List, Any


def get_system_prompt(interview_type: str, level: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", f"""
        You are Athena, an advanced AI Interview Coach specializing in {interview_type} interviews at the {level} level.
        Your role is to conduct realistic mock interviews and provide detailed, constructive feedback.

        Guidelines:
        1. Adapt questions to the {level} level
        2. Focus on {interview_type}-specific skills
        3. Provide balanced feedback
        4. Maintain a professional tone
        5. Ask one question at a time
        6. Probe technical depth
        7. Expect STAR method for behavioral questions
        """),
        MessagesPlaceholder(variable_name="messages")
    ])

def get_feedback_prompts() -> Dict[str, ChatPromptTemplate]:
    return {
        "content_feedback": ChatPromptTemplate.from_template("""
        Analyze this interview response:

        Question: {question}
        Response: {response}

        Consider:
        1. Relevance
        2. Technical accuracy
        3. Clarity
        4. Depth
        5. Examples
        6. Improvements

        Return JSON:
        {{
            "feedback": "Detailed feedback",
            "metrics": {{
                "clarity": 0-10,
                "technical_accuracy": 0-10,
                "communication": 0-10
            }},
            "suggestions": ["suggestion1", "suggestion2"]
        }}
        """),
        "vocal_feedback": ChatPromptTemplate.from_template("""
        Analyze vocal characteristics:

        Features: {features}

        Provide feedback on:
        1. Pace
        2. Tone
        3. Filler words
        4. Flow

        Return JSON:
        {{
            "vocal_feedback": "Feedback",
            "vocal_metrics": {{
                "pace": 0-10,
                "confidence": 0-10,
                "filler_words": 0-10
            }},
            "vocal_suggestions": ["suggestion1"]
        }}
        """),
        "summary_feedback": ChatPromptTemplate.from_template("""
        Generate an interview report:

        Interview Type: {interview_type}
        Level: {level}
        Questions: {question_count}
        Feedback: {feedback}

        Include:
        1. Assessment
        2. Strengths
        3. Improvements
        4. Technical feedback
        5. Behavioral feedback
        6. Resources
        7. Score

        Return JSON:
        {{
            "overview": "...",
            "strengths": ["..."],
            "improvements": ["..."],
            "technical_feedback": "...",
            "behavioral_feedback": "...",
            "resources": ["..."],
            "score": 0-100
        }}
        """)
    }

def get_question_prompts() -> Dict[str, ChatPromptTemplate]:
    return {
        "intro": ChatPromptTemplate.from_template("""
        Generate an introductory question for a {level} {interview_type} interview.
        """),
        "technical": ChatPromptTemplate.from_template("""
        Generate a technical question for a {level} {interview_type} interview on {topic}.
        """),
        "behavioral": ChatPromptTemplate.from_template("""
        Generate a behavioral question for a {interview_type} interview assessing {competency}.
        """),
        "followup": ChatPromptTemplate.from_template("""
        Based on response to '{question}':
        {response}

        Generate a follow-up question.
        """)
    }

def get_resume_prompts() -> Dict[str, ChatPromptTemplate]:
    return {
        "extract_skills": ChatPromptTemplate.from_template("""
        Analyze resume:

        {resume_text}

        Extract:
        - Technical skills
        - Experience years
        - Education
        - Projects
        - Work highlights

        Return JSON.
        """),
        "tailor_questions": ChatPromptTemplate.from_template("""
        Based on resume for {interview_type} at {level}:

        {resume_data}

        Generate 5 tailored questions.
        Return JSON list.
        """)
    }

def get_all_prompts() -> Dict[str, Dict[str, Any]]:
    return {
        "system": {"interview": get_system_prompt},
        "feedback": get_feedback_prompts(),
        "questions": get_question_prompts(),
        "resume": get_resume_prompts()
    }