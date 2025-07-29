import asyncio
import logging
import sys
import uuid
from dotenv import load_dotenv
from models.interview_state import InterviewState, InterviewMetrics
from models.user_profile import UserProfile
from agents.coach_agent import InterviewCoachAgent
from utils.storage import InterviewStorage
from config import Config

load_dotenv()
Config.validate()


async def run_interview(coach, initial_state):
    try:
        async for output in coach.run_interview(initial_state):
            for msg in output.get("messages", []):
                print(f"{msg.__class__.__name__}: {msg.content}")
    except Exception as e:
        logging.error(f"Failed to run interview: {e}")
        print(f"Error: Failed to run interview: {e}")
        raise


async def main():
    # Configure logging with both file and console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('interview.log'),
            logging.StreamHandler()
        ]
    )

    print("=== AI Interview Coach Setup ===")
    interview_type = input("Enter interview type (e.g., software_engineer): ").strip().replace(" ",
                                                                                               "_") or "software_engineer"
    level = input("Enter level (e.g., junior/mid/senior): ").strip().lower() or "mid"
    resume_choice = input("Would you like to upload a resume? (y/n): ").strip().lower()

    resume_text = ""
    if resume_choice == "y":
        print("Paste your resume text (max 4000 characters). Type 'END' on a new line and press Enter to finish:")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        resume_text = "\n".join(lines).strip()

        # Validate resume text
        if not resume_text:
            logging.error("Resume text is empty")
            print("Error: Resume text cannot be empty. Proceeding without resume.")
            resume_text = ""
        elif len(resume_text) > 4000:
            logging.warning(f"Resume text too long ({len(resume_text)} chars), truncating to 4000 chars")
            resume_text = resume_text[:4000]
            print("Warning: Resume truncated to 4000 characters.")
        logging.debug(f"Resume text input (first 200 chars): {resume_text[:300]}...")

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    storage = InterviewStorage()
    user_profile = UserProfile(
        user_id=user_id,
        name="Console User",
        email="console@example.com",
        target_roles=[interview_type],
        current_level=level,
        skills=[]
    )
    storage.save_user_profile(user_profile)

    initial_state = InterviewState(
        interview_id=f"mock_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        interview_type=interview_type,
        level=level,
        current_phase="intro",
        current_question="",
        question_history=[],
        user_responses=[],
        feedback=[],
        metrics=InterviewMetrics(),
        conversation_context="",
        start_time=None,
        end_time=None,
        resume_text=resume_text,
        resume_data=None
    )

    coach = InterviewCoachAgent()
    print("\n=== Starting Interview ===")
    await run_interview(coach, initial_state)


if __name__ == "__main__":
    try:
        # Windows-specific event loop policy to prevent resource warnings
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterview session cancelled by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"\nA fatal error occurred: {e}")
        sys.exit(1)
if __name__ == "__main__":
    asyncio.run(main())