from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import Config
import logging
import json
import re
import asyncio
from typing import Dict, Any, Union
from models.interview_state import InterviewState


class FeedbackAgent:
    def __init__(self):
        self.llm = ChatOpenAI(api_key=Config.OPENAI_API_KEY, model="gpt-4-turbo", max_tokens=1000)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def _process_metric(self, value: Union[int, float, str]) -> float:
        """Convert any metric value to float with error handling."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 5.0  # Default neutral score

    async def analyze_response(self, question: str, response_text: str, audio_features: dict) -> dict:
        prompt = ChatPromptTemplate.from_template("""
            Analyze the user's response to the interview question and provide feedback in valid JSON format.
            Question: {question}
            Response: {response_text}
            Audio Features: {audio_features}

            Return a single JSON object with the following structure:
            {{
                "feedback": "Detailed feedback on the response content and quality",
                "metrics": {{
                    "clarity": 7,  // Numeric value between 0-10
                    "technical_accuracy": 8,  // Numeric value between 0-10
                    "communication": 6  // Numeric value between 0-10
                }},
                "vocal_feedback": {{
                    "vocal_feedback": "Feedback on vocal delivery based on audio features",
                    "vocal_metrics": {{
                        "pace": 6,  // Numeric value between 0-10
                        "confidence": 7,  // Numeric value between 0-10
                        "filler_words": 3  // Count of filler words
                    }},
                    "vocal_suggestions": ["Speak more slowly", "Reduce filler words"]
                }}
            }}

            Important:
            - All metric values must be numbers, not strings
            - Return only the raw JSON without Markdown formatting
            - If audio features are empty, use default scores of 5
        """)

        for attempt in range(3):
            try:
                chain = prompt | self.llm
                result = await chain.ainvoke({
                    "question": question,
                    "response_text": response_text,
                    "audio_features": json.dumps(audio_features)
                })
                response_text = result.content.strip()
                logging.debug(f"Attempt {attempt + 1} - Raw LLM response: {response_text[:500]}...")

                # Clean and validate JSON
                response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()
                response_text = re.sub(r'//.*?\n|/\*.*?\*/', '', response_text, flags=re.DOTALL).strip()

                feedback = json.loads(response_text)

                # Process metrics
                feedback["metrics"] = {
                    "clarity": self._process_metric(feedback.get("metrics", {}).get("clarity", 5)),
                    "technical_accuracy": self._process_metric(
                        feedback.get("metrics", {}).get("technical_accuracy", 5)),
                    "communication": self._process_metric(feedback.get("metrics", {}).get("communication", 5))
                }

                # Process vocal feedback
                if not isinstance(feedback.get("vocal_feedback"), dict):
                    feedback["vocal_feedback"] = {
                        "vocal_feedback": str(feedback.get("vocal_feedback", "No vocal feedback")),
                        "vocal_metrics": {},
                        "vocal_suggestions": []
                    }

                feedback["vocal_feedback"]["vocal_metrics"] = {
                    "pace": self._process_metric(feedback["vocal_feedback"].get("vocal_metrics", {}).get("pace", 5)),
                    "confidence": self._process_metric(
                        feedback["vocal_feedback"].get("vocal_metrics", {}).get("confidence", 5)),
                    "filler_words": self._process_metric(
                        feedback["vocal_feedback"].get("vocal_metrics", {}).get("filler_words", 0))
                }

                if not isinstance(feedback["vocal_feedback"].get("vocal_suggestions"), list):
                    feedback["vocal_feedback"]["vocal_suggestions"] = [
                        "Ensure clear and structured responses."
                    ]

                logging.debug(f"Processed feedback: {json.dumps(feedback, indent=2)}")
                return feedback

            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == 2:
                    return self._get_default_feedback(audio_features)
                await asyncio.sleep(1)

    def _get_default_feedback(self, audio_features: dict) -> dict:
        """Return default feedback structure when processing fails."""
        return {
            "feedback": "Unable to generate detailed feedback due to processing error",
            "metrics": {
                "clarity": 5,
                "technical_accuracy": 5,
                "communication": 5
            },
            "vocal_feedback": {
                "vocal_feedback": "No vocal feedback available",
                "vocal_metrics": {
                    "pace": audio_features.get("pace", 5),
                    "confidence": audio_features.get("confidence", 5),
                    "filler_words": audio_features.get("filler_words", 0)
                },
                "vocal_suggestions": ["Ensure clear and structured responses."]
            }
        }

    async def generate_summary_report(self, state: InterviewState) -> dict:
        prompt = ChatPromptTemplate.from_template("""
            Generate a summary report for the interview based on the state.
            State: {state}

            Return a JSON object:
            {{
                "score": 75,  // Numeric value 0-100
                "overview": "Summary of performance",
                "strengths": ["Strength 1", "Strength 2"],
                "recommendations": ["Recommendation 1", "Recommendation 2"]
            }}
        """)

        try:
            chain = prompt | self.llm
            result = await chain.ainvoke({"state": state.model_dump(mode='json')})
            response_text = result.content.strip()
            response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()

            summary = json.loads(response_text)
            summary["score"] = float(summary.get("score", 50))  # Ensure score is numeric

            logging.debug(f"Summary report generated: {summary}")
            return summary
        except Exception as e:
            logging.error(f"Error generating summary report: {str(e)}")
            return {
                "score": 50,
                "overview": "Good performance with room for improvement in technical details.",
                "strengths": ["Clear communication"],
                "recommendations": ["Provide more specific examples."]
            }