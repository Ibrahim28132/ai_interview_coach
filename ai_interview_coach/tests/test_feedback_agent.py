import pytest
from agents.feedback_agent import FeedbackAgent
from unittest.mock import AsyncMock, patch


@pytest.fixture
def feedback_agent():
    return FeedbackAgent()


@pytest.mark.asyncio
async def test_analyze_response(feedback_agent):
    with patch('langchain_openai.ChatOpenAI') as mock_llm:
        mock_llm.return_value = AsyncMock()
        mock_llm.return_value.agenerate.return_value.generations = [
            [AsyncMock(text='{"feedback":"Good","metrics":{"clarity":8}}')]]

        result = await feedback_agent.analyze_response(
            "What is polymorphism?",
            "Polymorphism is a OOP concept that allows...",
            {}
        )

        assert "feedback" in result
        assert "metrics" in result
        assert result["metrics"]["clarity"] == 8


@pytest.mark.asyncio
async def test_generate_summary_report(feedback_agent):
    with patch('langchain_openai.ChatOpenAI') as mock_llm:
        mock_llm.return_value = AsyncMock()
        mock_llm.return_value.agenerate.return_value.generations = [[AsyncMock(text='{"overview":"Good","score":85}')]]

        result = await feedback_agent.generate_summary_report({
            "interview_type": "technical",
            "level": "mid",
            "feedback": []
        })

        assert "overview" in result
        assert "score" in result