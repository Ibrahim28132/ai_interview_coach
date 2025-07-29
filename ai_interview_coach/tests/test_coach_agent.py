import pytest
from agents.coach_agent import InterviewCoachAgent
from models.interview_state import InterviewState
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_state():
    return {
        "interview_type": "software_engineer",
        "level": "mid",
        "current_phase": "intro",
        "question_history": [],
        "user_responses": []
    }


@pytest.mark.asyncio
async def test_initialization(mock_state):
    with patch('langchain_openai.ChatOpenAI') as mock_llm:
        mock_llm.return_value = AsyncMock()
        coach = InterviewCoachAgent()
        result = await coach.initialize_interview(mock_state)

        assert "messages" in result
        assert len(result["messages"]) > 0


@pytest.mark.asyncio
async def test_question_flow(mock_state):
    with patch('langchain_openai.ChatOpenAI') as mock_llm, \
            patch('utils.voice.VoiceInterface') as mock_voice:
        mock_llm.return_value = AsyncMock()
        mock_voice.return_value = AsyncMock()

        coach = InterviewCoachAgent()

        # Test intro question
        result = await coach.ask_intro_question(mock_state)
        assert "messages" in result
        assert "current_question" in mock_state

        # Test technical question
        mock_state["current_phase"] = "technical"
        result = await coach.ask_technical_question(mock_state)
        assert "messages" in result
        assert "technical" in mock_state["current_question"].lower()