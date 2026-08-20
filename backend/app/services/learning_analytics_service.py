import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.db.models.assessments import (
    StudentResult,
    CompetencyResult,
    Assessment,
    Student,
)
from app.db.models.curriculum import Competency
from app.db.models.omr import OMRResult
from app.services.ai_pipeline.ollama_client import OllamaClient
from app.services.ai_pipeline.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

LEARNING_ANALYTICS_SYSTEM = """You are an expert educator providing actionable feedback for a student based on their assessment performance.
Analyze the provided competency and question-by-question performance data. The question data includes the actual text and the concept tested.

REQUIREMENTS:
1. Provide a list of specific strengths, mentioning the exact concepts or topics they mastered.
2. Provide a list of specific areas for improvement, explicitly naming the concepts they struggled with.
3. Provide 2-3 specific, actionable recommendations for the student to improve.
4. For the `narrative` field, you MUST write a HIGHLY DETAILED, IN-DEPTH, MULTI-PARAGRAPH analysis.
   - You MUST discuss the specific questions they missed.
   - You MUST explain what underlying concept each missed question was testing.
   - You MUST write at least 3 to 4 paragraphs.
   - DO NOT be brief. Write a very long, comprehensive report.

TONE AND STYLE CRITICAL INSTRUCTIONS:
- Write like a strict, professional human teacher.
- DO NOT use generic AI phrases like "In conclusion," "Overall," "In summary," or "This assessment provides valuable insights."
- End the narrative abruptly after your final specific point or recommendation. DO NOT add a concluding paragraph wrapping up the text.
- Do not sound like ChatGPT. Be direct, analytical, and professional.

CRITICAL INSTRUCTION: Respond ONLY with a valid JSON object. No markdown outside the JSON structure. Use line breaks (\\n) in the narrative string for paragraphs.
WARNING: DO NOT COPY THE VALUES FROM THE EXAMPLE BELOW. YOU MUST EXTRACT THE REAL CONCEPTS FROM THE PROVIDED DATA.

VALID JSON EXAMPLE:
{
  "strengths": ["Excellent understanding of [Insert Actual Concept Here]", "Answered all questions on [Insert Actual Topic Here] correctly"],
  "areas_for_improvement": ["Needs review on [Insert Actual Concept Here]", "Struggled with questions regarding [Insert Actual Topic Here]"],
  "recommendations": ["Review chapter focusing on [Insert Actual Concept Here]", "Practice more questions for [Insert Actual Topic Here]"],
  "narrative": "Paragraph 1 detailing overall performance and specific strengths based on the real data provided...\\n\\nParagraph 2 detailing the specific questions missed, what real concepts they tested, and why the student might have been confused...\\n\\nParagraph 3 elaborating on further weaknesses and patterns in the missed questions..."
}
"""


class LearningAnalyticsService:
    def __init__(self, ollama: OllamaClient | None = None):
        if ollama is None:
            from app.services.ai_pipeline.client_factory import get_ai_client
            self.ollama = get_ai_client()
        else:
            self.ollama = ollama

    async def generate_student_insights(
        self, db: AsyncSession, student_id: int, assessment_id: int | None = None
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
                "narrative": "Not enough data to generate insights yet.",
            }

        # Aggregate competency data and question-by-question data
        competency_data = {}
        question_summary = []

        for sr in student_results:
            comp_stmt = select(CompetencyResult).where(
                CompetencyResult.student_result_id == sr.id
            )
            comp_res = await db.execute(comp_stmt)
            for cr in comp_res.scalars().all():
                if cr.competency_id not in competency_data:
                    comp = await db.get(Competency, cr.competency_id)
                    competency_data[cr.competency_id] = {
                        "name": (
                            comp.name_en if comp else f"Competency {cr.competency_id}"
                        ),
                        "attempted": 0,
                        "correct": 0,
                    }

                competency_data[cr.competency_id]["attempted"] += (
                    cr.questions_attempted or 0
                )
                competency_data[cr.competency_id]["correct"] += (
                    cr.questions_correct or 0
                )

            # If OMR result is linked, get question-by-question data with actual text
            if sr.omr_result_id:
                omr_stmt = select(OMRResult).where(OMRResult.id == sr.omr_result_id)
                omr_res = await db.execute(omr_stmt)
                omr_result = omr_res.scalar_one_or_none()
                if omr_result and omr_result.detected_answers:
                    try:
                        answers = json.loads(omr_result.detected_answers)

                        # Fetch the actual question text and concepts from the database
                        from app.db.models.questions import QuestionBank
                        from sqlalchemy.orm import selectinload

                        q_ids = [
                            ans.get("question_id")
                            for ans in answers
                            if ans.get("question_id")
                        ]
                        questions_dict = {}
                        if q_ids:
                            q_stmt = (
                                select(QuestionBank)
                                .options(selectinload(QuestionBank.concept))
                                .where(QuestionBank.id.in_(q_ids))
                            )
                            q_res = await db.execute(q_stmt)
                            questions_dict = {q.id: q for q in q_res.scalars().all()}

                        for ans in answers:
                            q_num = ans.get("sequence", ans.get("question_id", ""))
                            status = "Correct" if ans.get("is_correct") else "Incorrect"

                            q_id = ans.get("question_id")
                            q_obj = questions_dict.get(q_id)

                            if q_obj:
                                concept_name = (
                                    q_obj.concept.name_en
                                    if q_obj.concept
                                    else "General"
                                )
                                question_text = q_obj.question_text_en or ""
                                # Clean up formatting for the LLM
                                question_text = question_text.replace("\n", " ")
                                question_summary.append(
                                    f"Question {q_num} [{concept_name}]: {status} - Text: {question_text}"
                                )
                            else:
                                question_summary.append(f"Question {q_num}: {status}")
                    except Exception as e:
                        logger.error(f"Error parsing detected_answers: {e}")

        # Calculate percentages
        performance_summary = []
        for cid, data in competency_data.items():
            perc = (
                (data["correct"] / data["attempted"] * 100)
                if data["attempted"] > 0
                else 0
            )
            performance_summary.append(
                f"Competency: {data['name']}, Score: {data['correct']}/{data['attempted']} ({perc:.1f}%)"
            )

        context_parts = ["COMPETENCY SCORES:"]
        context_parts.extend(performance_summary)

        if question_summary:
            context_parts.append("\nQUESTION RESULTS:")
            context_parts.extend(question_summary)

        context = "\n".join(context_parts)

        task_instruction = (
            "You MUST generate a HIGHLY DETAILED, IN-DEPTH, MULTI-PARAGRAPH narrative analysis. "
            "Go through the specific questions they got incorrect. Explain exactly what concept "
            "each incorrect question tests and why they might have missed it based on the question text. "
            "Write a very long and detailed evaluation (at least 3-4 paragraphs) in the 'narrative' field. "
            "Also, be extremely specific in the 'strengths' and 'areas_for_improvement' arrays, "
            "referencing the exact concepts from the Question Results. "
            "CRITICAL: Do NOT write a concluding paragraph. Stop your analysis immediately after your last analytical point."
        )
        system, prompt = build_prompt(
            LEARNING_ANALYTICS_SYSTEM,
            [{"text": context, "chapter_title": "", "topic_title": ""}],
            task_instruction,
        )

        try:
            ai_result = await self.ollama.generate_structured(
                prompt=prompt, system=system
            )
            return {
                "strengths": ai_result.get("strengths", []),
                "areas_for_improvement": ai_result.get("areas_for_improvement", []),
                "recommendations": ai_result.get("recommendations", []),
                "narrative": ai_result.get("narrative", ""),
            }
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {
                "strengths": [],
                "areas_for_improvement": [],
                "recommendations": [],
                "narrative": "Could not generate insights at this time.",
            }

    async def calculate_student_risk_score(
        self, db: AsyncSession, student_id: int
    ) -> Dict[str, Any]:
        """
        Calculates a risk score for a student based on recent performance trends to flag for dropout/failure risk.
        """
        stmt = (
            select(StudentResult)
            .where(StudentResult.student_id == student_id)
            .order_by(StudentResult.id.desc())
            .limit(3)
        )
        result = await db.execute(stmt)
        recent_results = result.scalars().all()

        if len(recent_results) < 2:
            return {
                "risk_level": "Low",
                "trend": "Insufficient Data",
                "flag": False,
                "reason": "Not enough recent assessments to calculate trend.",
                "recent_scores": []
            }
        
        scores = []
        for sr in recent_results:
            comp_stmt = select(CompetencyResult).where(
                CompetencyResult.student_result_id == sr.id
            )
            comp_res = await db.execute(comp_stmt)
            total_correct = 0
            total_attempted = 0
            for cr in comp_res.scalars().all():
                total_correct += (cr.questions_correct or 0)
                total_attempted += (cr.questions_attempted or 0)
            
            if total_attempted > 0:
                scores.append(total_correct / total_attempted * 100)
            else:
                scores.append(0.0)
        
        # scores are from newest to oldest
        scores.reverse() # now oldest to newest
        
        trend_diff = scores[-1] - scores[0]
        avg_score = sum(scores) / len(scores)
        
        risk_level = "Low"
        flag = False
        reason = "Student is performing well and stable."
        
        if avg_score < 40:
            risk_level = "High"
            flag = True
            reason = "Consistently low performance across recent assessments."
        elif trend_diff < -15:
            risk_level = "Medium"
            flag = True
            reason = f"Performance has dropped by {abs(trend_diff):.1f}% recently."
        
        trend_str = "Declining" if trend_diff < -5 else "Improving" if trend_diff > 5 else "Stable"
        
        return {
            "risk_level": risk_level,
            "trend": trend_str,
            "flag": flag,
            "reason": reason,
            "recent_scores": scores
        }
