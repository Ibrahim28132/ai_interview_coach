from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import logging

class InterviewDashboard:
    def __init__(self):
        self.console = Console()

    def display_question(self, question: str):
        self.console.print(f"\n[bold]Question:[/bold] {question}")

    def display_feedback(self, feedback: dict):
        table = Table(title="Feedback")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="magenta")
        table.add_column("Comments", style="green")

        metrics = feedback.get("metrics", {})
        for metric, score in metrics.items():
            comments = feedback.get("suggestions", {}).get(metric, "")
            table.add_row(metric.capitalize(), f"{score:.1f}", comments)

        vocal_metrics = feedback.get("vocal_metrics", {})
        for metric, score in vocal_metrics.items():
            comments = feedback.get("suggestions", {}).get(metric, "")
            table.add_row(metric.capitalize(), f"{score:.1f}", comments)

        self.console.print(table)

    def display_summary(self, summary: dict):
        logging.debug(f"Summary data received: {summary}")
        table = Table(title="Interview Summary Report")
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="green")

        # Extract numerical score and ensure it's a float or int
        score = summary.get("score", 0)
        try:
            score = float(score)
        except (TypeError, ValueError):
            logging.error(f"Invalid score format: {score}, defaulting to 0")
            score = 0.0

        # Render score as percentage
        table.add_row("Overall Score", f"{score:.0f}%")

        strengths = summary.get("strengths", [])
        strengths_text = "\n".join(f"- {s}" for s in strengths)
        table.add_row("Strengths", strengths_text or "None identified")

        areas = summary.get("areas_for_improvement", [])
        areas_text = "\n".join(f"- {a}" for a in areas)
        table.add_row("Areas for Improvement", areas_text or "None identified")

        resources = summary.get("recommended_resources", [])
        resources_text = "\n".join(f"- {r}" for r in resources)
        table.add_row("Recommended Resources", resources_text or "None provided")

        self.console.print(table)