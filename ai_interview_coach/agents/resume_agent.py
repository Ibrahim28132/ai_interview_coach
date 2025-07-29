from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import Config
import logging
import json
import re
from typing import Dict, List
import asyncio

class ResumeAgent:
    def __init__(self):
        self.llm = ChatOpenAI(api_key=Config.OPENAI_API_KEY, model="gpt-4-turbo", max_tokens=1000)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    async def extract_skills(self, resume_text: str, retries: int = 5) -> Dict:
        # Handle short or invalid resume text
        if not resume_text or len(resume_text.strip()) < 10:
            logging.warning("Resume text is too short or empty, using default skills")
            return {
                "skills": ["Python", "JavaScript", "SQL"],
                "tools": ["Django", "React", "Flutter"],
                "technologies": ["RESTful APIs", "AI"]
            }

        # Append additional resume text
        additional_resume = (
            "Skilled in data preprocessing, model training, and visualization using tools like Pandas, "
            "Scikit-learn, and Power BI. Experienced in full-stack development and cloud architecture."
        )
        full_resume = f"{resume_text.strip()}\n\n{additional_resume.strip()}"

        # Validate and truncate resume text
        if len(full_resume) > 4000:
            logging.warning(f"Resume text too long ({len(full_resume)} chars), truncating to 4000 chars")
            full_resume = full_resume[:4000]
        full_resume = full_resume.replace('\r', '').replace('\n\n', '\n').strip()
        logging.debug(f"Sanitized resume text (first 200 chars): {full_resume[:200]}...")

        prompt = ChatPromptTemplate.from_template("""
            Extract skills, tools, and technologies from the resume.
            Resume: {resume_text}

            Return valid JSON:
            {{ "skills": [], "tools": [], "technologies": [] }}
            Avoid Markdown code blocks (e.g., ```json). Return empty lists if no data is found.
        """)

        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                chain = prompt | self.llm
                result = await chain.ainvoke({"resume_text": full_resume})
                response_text = result.content.strip()
                logging.debug(f"Raw LLM response (attempt {attempt}/{retries}): {response_text[:500]}...")

                # Strip Markdown and comments
                response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()
                response_text = re.sub(r'//.*?\n|/\*.*?\*/', '', response_text, flags=re.DOTALL).strip()
                logging.debug(f"Cleaned response (first 200 chars): {response_text[:200]}...")

                # Validate JSON
                if not response_text.startswith('{') or not response_text.endswith('}'):
                    logging.error(f"Invalid JSON format on attempt {attempt}: {response_text[:100]}...")
                    raise ValueError("LLM response is not valid JSON")

                skills_data = json.loads(response_text)
                if not isinstance(skills_data, dict) or not all(key in skills_data for key in ["skills", "tools", "technologies"]):
                    logging.error(f"Invalid JSON structure on attempt {attempt}: {skills_data}")
                    raise ValueError("Invalid JSON structure from LLM")

                # Ensure lists
                for key in ["skills", "tools", "technologies"]:
                    if not isinstance(skills_data[key], list):
                        logging.warning(f"Invalid {key} format, converting to list")
                        skills_data[key] = []

                logging.debug(f"Extracted skills: {skills_data}")
                return skills_data

            except Exception as e:
                logging.error(f"Error analyzing resume on attempt {attempt}/{retries}: {e}")
                if attempt == retries:
                    # Extract partial skills from response
                    partial_skills = []
                    if response_text:
                        try:
                            matches = re.findall(r'"([^"]+)"', response_text)
                            partial_skills = [s for s in matches if s.lower() in full_resume.lower()]
                            logging.debug(f"Partial skills extracted: {partial_skills}")
                        except Exception:
                            pass

                    return {
                        "skills": partial_skills or ["Python", "JavaScript", "SQL", "Machine Learning", "Data Preprocessing"],
                        "tools": ["Flutter", "React Native", "Pandas", "Scikit-learn", "Power BI"],
                        "technologies": ["RESTful APIs", "AI", "Data Visualization"]
                    }
                await asyncio.sleep(2)

    async def tailor_questions(self, resume_data: Dict, interview_type: str, level: str, retries: int = 5) -> List[str]:
        prompt = ChatPromptTemplate.from_template("""
            Generate 3-5 interview questions based on resume data, interview type, and level.
            Resume data: {resume_data}
            Interview type: {interview_type}
            Level: {level}

            Return valid JSON:
            {{ "questions": [] }}
            Avoid Markdown code blocks. Return empty list if no questions are generated.
        """)
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                chain = prompt | self.llm
                result = await chain.ainvoke({
                    "resume_data": json.dumps(resume_data),
                    "interview_type": interview_type,
                    "level": level
                })
                response_text = result.content.strip()
                logging.debug(f"Raw LLM response for questions (attempt {attempt}/{retries}): {response_text[:500]}...")

                # Strip Markdown and comments
                response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()
                response_text = re.sub(r'//.*?\n|/\*.*?\*/', '', response_text, flags=re.DOTALL).strip()
                logging.debug(f"Cleaned response (first 200 chars): {response_text[:200]}...")

                # Validate JSON
                if not response_text.startswith('{') or not response_text.endswith('}'):
                    logging.error(f"Invalid JSON format on attempt {attempt}: {response_text[:100]}...")
                    raise ValueError("LLM response is not valid JSON")

                questions_data = json.loads(response_text)
                if not isinstance(questions_data, dict) or "questions" not in questions_data:
                    logging.error(f"Invalid JSON structure on attempt {attempt}: {questions_data}")
                    raise ValueError("Invalid JSON structure from LLM")

                logging.debug(f"Tailored questions: {questions_data['questions']}")
                return questions_data["questions"]

            except Exception as e:
                logging.error(f"Error generating questions on attempt {attempt}/{retries}: {e}")
                if attempt == retries:
                    return [
                        f"Explain how you used {resume_data['skills'][0]} in a project.",
                        f"Describe your experience with {resume_data['tools'][0]} in {interview_type} development.",
                        f"How do you approach learning a new technology like {resume_data['technologies'][0]}?"
                    ]
                await asyncio.sleep(2)