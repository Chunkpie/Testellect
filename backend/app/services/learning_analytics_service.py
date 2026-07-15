import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.db.models.assessments import StudentResult, CompetencyResult, Assessment, Student
from app.db.models.curriculum import Competency
from app.db.models.omr import OMRResult
from app.services.ai_pipeline.ollama_client import OllamaClient
from app.services.ai_pipeline.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

LEARNING_ANALYTICS_SYSTEM = """You are an expert educator providing actionable feedback for a student based on their assessment performance.
Analyze the provided competency and question-by-question performance data.

REQUIREMENTS:
- Provide a summary of strengths (competencies where mastery is high, or specific questions they did well on).
- Provide a summary of areas for improvement (competencies where mastery is low, or specific concepts they missed).
- Provide 2-3 specific, actionable recommendations for the student to improve.
- Keep the tone encouraging and constructive.

CRITICAL INSTRUCTION: Respond ONLY with a valid JSON object. No markdown, no extra text.
DO NOT COPY THE EXAMPLE TEXT EXACTLY. Use the actual concepts and topics from the provided COMPETENCY SCORES and QUESTION RESULTS.

VALID JSON EXAMPLE:
{
  "strengths": ["Strong grasp of [Concept A]", "Correctly answered most questions on [Topic B]"],
  "areas_for_improvement": ["Needs review on [Concept C]", "Missed several questions related to [Topic D]"],
  "recommendations": ["Review chapter X focusing on [Concept C]", "Practice more questions on [Topic D]"],
  "narrative": "You showed great understanding of [Concept A], but let's work more on [Concept C]..."
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

        # Aggregate competency data and question-by-question data
        competency_data = {}
        question_summary = []
        
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

            # If OMR result is linked, get question-by-question data
            if sr.omr_result_id:
                omr_stmt = select(OMRResult).where(OMRResult.id == sr.omr_result_id)
                omr_res = await db.execute(omr_stmt)
                omr_result = omr_res.scalar_one_or_none()
                if omr_result and omr_result.detected_answers:
                    try:
                        answers = json.loads(omr_result.detected_answers)
                        for ans in answers:
                            q_num = ans.get("sequence", ans.get("question_id", ""))
                            status = "Correct" if ans.get("is_correct") else "Incorrect"
                            question_summary.append(f"Question {q_num}: {status}")
                    except Exception as e:
                        logger.error(f"Error parsing detected_answers: {e}")

        # Calculate percentages
        performance_summary = []
        for cid, data in competency_data.items():
            perc = (data["correct"] / data["attempted"] * 100) if data["attempted"] > 0 else 0
            performance_summary.append(f"Competency: {data['name']}, Score: {data['correct']}/{data['attempted']} ({perc:.1f}%)")

        context_parts = ["COMPETENCY SCORES:"]
        context_parts.extend(performance_summary)
        
        if question_summary:
            context_parts.append("\nQUESTION RESULTS:")
            context_parts.extend(question_summary)
            
        context = "\n".join(context_parts)
        
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
