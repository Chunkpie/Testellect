import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.db.models.assessments import StudentResult, CompetencyResult, Assessment, Student
from app.db.models.curriculum import Competency
from app.services.ai_pipeline.gemini_client import GeminiClient as OllamaClient
from app.services.ai_pipeline.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

LEARNING_ANALYTICS_SYSTEM = """You are an expert educator providing actionable feedback for a student based on their assessment performance.
Analyze the provided competency performance data.

REQUIREMENTS:
- Provide a summary of strengths (competencies where mastery is high).
- Provide a summary of areas for improvement (competencies where mastery is low or questions missed).
- Provide 2-3 specific, actionable recommendations for the student to improve.
- Keep the tone encouraging and constructive.

CRITICAL: Respond ONLY with a valid JSON object. No markdown, no code fences, no extra text.
VALID JSON EXAMPLE:
{
  "strengths": ["Excellent understanding of basic addition", "Good reading comprehension"],
  "areas_for_improvement": ["Struggling with multi-digit multiplication", "Needs work on vocabulary"],
  "recommendations": ["Practice 10 multiplication problems daily", "Read a new book each week and note down new words"],
  "narrative": "You're doing a great job with your basic math and reading! To get even better, let's focus on practicing those larger multiplication problems..."
}
"""

class LearningAnalyticsService:
    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()

    async def generate_student_insights(
        self,
        db: AsyncSession,
        student_id: int,
        assessment_id: int | None = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights for a student based on their results.
        If assessment_id is provided, focus on that assessment. Otherwise, use all available results.
        """
        student = await db.get(Student, student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found")

        stmt = select(StudentResult).where(StudentResult.student_id == student_id)
        if assessment_id:
            stmt = stmt.where(StudentResult.assessment_id == assessment_id)
            
        result = await db.execute(stmt)
        student_results = result.scalars().all()

        if not student_results:
            return {
                "strengths": [],
                "areas_for_improvement": [],
                "recommendations": [],
                "narrative": "Not enough data to generate insights yet."
            }

        # Aggregate competency data
        competency_data = {}
        for sr in student_results:
            comp_stmt = select(CompetencyResult).where(CompetencyResult.student_result_id == sr.id)
            comp_res = await db.execute(comp_stmt)
            for cr in comp_res.scalars().all():
                if cr.competency_id not in competency_data:
                    comp = await db.get(Competency, cr.competency_id)
                    competency_data[cr.competency_id] = {
                        "name": comp.name_en if comp else f"Competency {cr.competency_id}",
                        "attempted": 0,
                        "correct": 0
                    }
                
                competency_data[cr.competency_id]["attempted"] += cr.questions_attempted or 0
                competency_data[cr.competency_id]["correct"] += cr.questions_correct or 0

        # Calculate percentages
        performance_summary = []
        for cid, data in competency_data.items():
            perc = (data["correct"] / data["attempted"] * 100) if data["attempted"] > 0 else 0
            performance_summary.append(f"Competency: {data['name']}, Score: {data['correct']}/{data['attempted']} ({perc:.1f}%)")

        context = "\n".join(performance_summary)
        
        system, prompt = build_prompt(
            LEARNING_ANALYTICS_SYSTEM, 
            [{"text": context, "chapter_title": "", "topic_title": ""}], 
            "Generate actionable insights based on this student's performance."
        )

        try:
            ai_result = await self.ollama.generate_structured(prompt=prompt, system=system)
            return {
                "strengths": ai_result.get("strengths", []),
                "areas_for_improvement": ai_result.get("areas_for_improvement", []),
                "recommendations": ai_result.get("recommendations", []),
                "narrative": ai_result.get("narrative", "")
            }
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {
                "strengths": [],
                "areas_for_improvement": [],
                "recommendations": [],
                "narrative": "Could not generate insights at this time."
            }
