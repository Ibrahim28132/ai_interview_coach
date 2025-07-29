import speech_recognition as sr
import pyttsx3
import pyaudio
import wave
import tempfile
import logging
import os
import asyncio
from typing import Optional
from config import Config
import openai
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from typing import Dict, List, TypedDict, Any, Union
from datetime import datetime
from models.interview_state import InterviewState
from models.user_profile import UserProfile
from utils.file_storage import FileStorage
from utils.dashboard import InterviewDashboard
import random
import json
from agents.feedback_agent import FeedbackAgent
from agents.resume_agent import ResumeAgent


class InterviewStateDict(TypedDict):
    state: InterviewState
    messages: List[Any]


class VoiceInterface:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        self._last_response = None
        self._response_event = asyncio.Event()

        # Improved recognizer settings
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0  # Seconds of silence before considering speech ended
        self.recognizer.energy_threshold = 4000  # Adjust based on your microphone
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def speak(self, text: str):
        """Output text as speech if voice is enabled"""
        if not Config.VOICE_ENABLED:
            logging.debug(f"Text-to-speech: {text}")
            return

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logging.error(f"Speech synthesis error: {e}")

    def set_response(self, response: str):
        """Set the response received from the UI"""
        self._last_response = response
        self._response_event.set()
        logging.debug(f"Response received from UI: {response}")

    async def wait_for_response(self, timeout: int = 60) -> Optional[str]:
        """Wait for a response with timeout, checking both UI and voice input"""
        self._response_event.clear()
        self._last_response = None

        try:
            # Create tasks with proper timeout handling
            voice_task = asyncio.create_task(self._listen_for_voice(timeout))
            ui_task = asyncio.create_task(self._response_event.wait())

            done, pending = await asyncio.wait(
                {voice_task, ui_task},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()

            # Check which task completed
            if voice_task in done and not voice_task.exception():
                return voice_task.result()
            elif ui_task in done:
                return self._last_response

            return None

        except Exception as e:
            logging.error(f"Error waiting for response: {e}")
            return None

    async def _listen_for_voice(self, timeout: int) -> Optional[str]:
        """Listen for voice input with timeout"""
        if not Config.VOICE_ENABLED:
            return None

        with sr.Microphone() as source:
            logging.debug("Adjusting for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.debug(f"Listening for speech (timeout: {timeout}s)...")

            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=timeout
                )
                logging.debug("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                logging.debug(f"Recognized speech: {text}")
                self._last_response = text
                self._response_event.set()
                return text
            except sr.WaitTimeoutError:
                logging.debug("No speech detected within timeout period")
                return None
            except sr.UnknownValueError:
                logging.debug("Could not understand audio")
                return None
            except Exception as e:
                logging.error(f"Voice recognition error: {e}")
                return None

    def clear_response(self):
        """Clear the stored response"""
        self._last_response = None
        self._response_event.clear()


class InterviewCoachAgent:
    def __init__(self):
        self.llm = ChatOpenAI(api_key=Config.OPENAI_API_KEY, model="gpt-4-turbo")
        self.voice = VoiceInterface()
        self.storage = FileStorage()
        self.dashboard = InterviewDashboard()
        self.question_banks = self._load_question_banks()
        self.workflow = self._create_workflow()
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def _load_question_banks(self) -> Dict:
        banks = {
            "software_engineer": {
                "intro": ["Tell me about yourself.", "Why do you want to work in software engineering?"],
                "technical": {
                    "junior": ["What is a list in Python?", "Explain APIs."],
                    "mid": ["Explain the difference between a list and a tuple in Python.",
                            "How would you optimize a slow SQL query?"],
                    "senior": ["Design a scalable microservices architecture.", "Explain the CAP theorem."]
                },
                "behavioral": ["Describe a time you faced a challenging bug.", "Tell me about a team project."]
            }
        }
        for bank_file in Config.QUESTION_BANKS_DIR.glob("*.json"):
            try:
                with open(bank_file, 'r') as f:
                    bank_data = json.load(f)
                    banks[bank_file.stem] = bank_data
                    logging.debug(f"Loaded question bank: {bank_file.stem}")
            except Exception as e:
                logging.warning(f"Failed to load question bank {bank_file}: {e}")
        return banks

    def _create_workflow(self):
        workflow = StateGraph(InterviewStateDict)
        workflow.add_node("initialize", self.initialize_interview)
        workflow.add_node("analyze_resume", self.analyze_resume)
        workflow.add_node("ask_intro", self.ask_intro_question)
        workflow.add_node("ask_technical", self.ask_technical_question)
        workflow.add_node("ask_behavioral", self.ask_behavioral_question)
        workflow.add_node("evaluate", self.evaluate_response)
        workflow.add_node("closing", self.handle_closing)

        workflow.add_edge("initialize", "analyze_resume")
        workflow.add_edge("analyze_resume", "ask_intro")
        workflow.add_edge("ask_intro", "evaluate")
        workflow.add_edge("ask_technical", "evaluate")
        workflow.add_edge("ask_behavioral", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            self.decide_next_phase,
            {
                "intro": "ask_intro",
                "technical": "ask_technical",
                "behavioral": "ask_behavioral",
                "closing": "closing"
            }
        )
        workflow.add_edge("closing", END)
        workflow.set_entry_point("initialize")
        return workflow.compile()

    async def initialize_interview(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        state.start_time = datetime.now()
        state.question_history = []
        state.user_responses = []
        state.feedback = []

        welcome_msg = AIMessage(content=f"Welcome to your {state.interview_type.replace('_', ' ')} mock interview. "
                                        f"I'll be your AI coach today. This session is for {state.level} level. "
                                        "Let's begin with some introductory questions.")
        self.voice.speak(welcome_msg.content)
        return {"state": state, "messages": [welcome_msg]}

    async def analyze_resume(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        messages = []
        if state.resume_text:
            analyzer = ResumeAgent()
            try:
                resume_data = await analyzer.extract_skills(state.resume_text)
                tailored_questions = await analyzer.tailor_questions(resume_data, state.interview_type, state.level)

                if state.interview_type in self.question_banks:
                    if "technical" not in self.question_banks[state.interview_type]:
                        self.question_banks[state.interview_type]["technical"] = {}
                    if state.level not in self.question_banks[state.interview_type]["technical"]:
                        self.question_banks[state.interview_type]["technical"][state.level] = []
                    self.question_banks[state.interview_type]["technical"][state.level].extend(tailored_questions)
                else:
                    self.question_banks[state.interview_type] = {
                        "intro": ["Tell me about yourself."],
                        "technical": {state.level: tailored_questions},
                        "behavioral": ["Describe a challenging situation you faced at work."]
                    }

                state.resume_data = resume_data
            except Exception as e:
                logging.error(f"Failed to process resume: {e}")
                state.resume_data = {"skills": [], "tools": [], "technologies": []}
                messages.append(AIMessage(content="Unable to process resume, proceeding with default questions."))

        return {"state": state, "messages": messages}

    async def ask_intro_question(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        question = random.choice(self.question_banks[state.interview_type][
                                     "intro"]) if state.interview_type in self.question_banks else "Tell me about yourself."
        question_msg = AIMessage(content=question)
        self.voice.speak(question)

        state.current_question = question
        state.current_phase = "intro"
        state.question_history.append({
            "phase": "intro",
            "question": question,
            "time": datetime.now().isoformat()
        })

        return {"state": state, "messages": [question_msg]}

    async def ask_technical_question(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        question = random.choice(self.question_banks[state.interview_type]["technical"][
                                     state.level]) if state.interview_type in self.question_banks else "Explain a technical concept."
        question_msg = AIMessage(content=question)
        self.voice.speak(question)

        state.current_question = question
        state.current_phase = "technical"
        state.question_history.append({
            "phase": "technical",
            "question": question,
            "time": datetime.now().isoformat()
        })

        return {"state": state, "messages": [question_msg]}

    async def ask_behavioral_question(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        question = random.choice(self.question_banks[state.interview_type][
                                     "behavioral"]) if state.interview_type in self.question_banks else "Describe a challenging situation."
        question_msg = AIMessage(content=question)
        self.voice.speak(question)

        state.current_question = question
        state.current_phase = "behavioral"
        state.question_history.append({
            "phase": "behavioral",
            "question": question,
            "time": datetime.now().isoformat()
        })

        return {"state": state, "messages": [question_msg]}

    async def evaluate_response(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        start_time = datetime.now()

        # Wait for response with 30-second timeout using the updated VoiceInterface
        response_text = await self.voice.wait_for_response(timeout=60)

        if response_text is None:
            response_text = "No response provided within time limit"
            logging.warning("Response timeout reached")
            # Add gentle timeout notice
            timeout_msg = AIMessage(content="I didn't hear your response. Let's move to the next question.")
            self.voice.speak(timeout_msg.content)

        processing_time = (datetime.now() - start_time).seconds
        logging.debug(f"Response processing time: {processing_time} seconds")

        user_response = {
            "text": response_text,
            "audio_features": {},
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        state.user_responses.append(user_response)

        feedback_agent = FeedbackAgent()
        feedback = await feedback_agent.analyze_response(
            state.current_question,
            response_text,
            {}
        )
        feedback = self._validate_feedback(feedback, {})
        state.feedback.append(feedback)

        self._update_metrics(state, feedback)

        if "No response provided within time limit" in response_text:
            return {
                "state": state,
                "messages": [timeout_msg, AIMessage(content=f"Feedback: {feedback.get('feedback', 'No feedback')}")]
            }

        return {
            "state": state,
            "messages": [HumanMessage(content=response_text),
                         AIMessage(content=f"Feedback: {feedback.get('feedback', 'No feedback')}")]
        }

    def _validate_feedback(self, feedback: Any, audio_features: dict) -> dict:
        default_feedback = {
            "feedback": "No detailed feedback available",
            "metrics": {"clarity": 5.0, "technical_accuracy": 5.0, "communication": 5.0},
            "vocal_feedback": {
                "vocal_feedback": "No vocal feedback",
                "vocal_metrics": {"pace": 5.0, "confidence": 5.0, "filler_words": 0},
                "vocal_suggestions": ["Speak clearly and confidently."]
            }
        }

        if not isinstance(feedback, dict):
            return default_feedback

        validated = {
            "feedback": str(feedback.get("feedback", default_feedback["feedback"])),
            "metrics": {k: float(feedback.get("metrics", {}).get(k, v)) for k, v in
                        default_feedback["metrics"].items()},
            "vocal_feedback": {
                "vocal_feedback": str(feedback.get("vocal_feedback", {}).get("vocal_feedback",
                                                                             default_feedback["vocal_feedback"][
                                                                                 "vocal_feedback"])),
                "vocal_metrics": {k: float(feedback.get("vocal_feedback", {}).get("vocal_metrics", {}).get(k, v))
                                  for k, v in default_feedback["vocal_feedback"]["vocal_metrics"].items()},
                "vocal_suggestions": list(feedback.get("vocal_feedback", {}).get("vocal_suggestions",
                                                                                 default_feedback["vocal_feedback"][
                                                                                     "vocal_suggestions"]))
            }
        }
        return validated

    def _update_metrics(self, state: InterviewState, feedback: Dict):
        for metric in ["clarity", "technical_accuracy", "communication"]:
            getattr(state.metrics, metric).append(float(feedback["metrics"][metric]))
        for metric in ["pace", "confidence", "filler_words"]:
            getattr(state.metrics, metric).append(float(feedback["vocal_feedback"]["vocal_metrics"][metric]))

    async def handle_closing(self, input: InterviewStateDict) -> InterviewStateDict:
        state = input["state"]
        state.end_time = datetime.now()

        closing_msg = AIMessage(content="We've reached the end of our session. Thank you for your time!")
        self.voice.speak(closing_msg.content)

        feedback_agent = FeedbackAgent()
        summary = await feedback_agent.generate_summary_report(state)

        interview_data = {
            'interview_id': state.interview_id,
            'user_id': state.user_id,
            'interview_type': state.interview_type,
            'level': state.level,
            'start_time': state.start_time.isoformat(),
            'end_time': state.end_time.isoformat(),
            'questions': [{
                'question': q['question'],
                'phase': q['phase'],
                'response': r['text'],
                'feedback': f
            } for q, r, f in zip(state.question_history, state.user_responses, state.feedback)],
            'summary': summary
        }
        self.storage.save_interview(interview_data)

        return {
            "state": state,
            "messages": [closing_msg, AIMessage(content=f"Summary: {summary.get('overview', 'No summary')}")],
            "summary": summary
        }

    def decide_next_phase(self, input: InterviewStateDict) -> str:
        state = input["state"]
        phase_counts = {"intro": 0, "technical": 0, "behavioral": 0}
        for q in state.question_history:
            phase_counts[q["phase"]] += 1

        if phase_counts["intro"] < 2:
            return "intro"
        elif phase_counts["technical"] < 3:
            return "technical"
        elif phase_counts["behavioral"] < 2:
            return "behavioral"
        return "closing"

    async def run_interview(self, initial_state: InterviewState):
        try:
            inputs = {"state": initial_state, "messages": []}
            async for output in self.workflow.astream(inputs):
                yield {
                    "messages": output.get("messages", []),
                    "state": output.get("state", initial_state),
                    "feedback": output.get("state", initial_state).feedback[-1] if output.get("state",
                                                                                              initial_state).feedback else {},
                    "summary": output.get("summary", None)
                }
        except Exception as e:
            logging.error(f"Interview error: {e}")
            yield {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                "state": initial_state,
                "feedback": {},
                "summary": None
            }