import asyncio
import httpx
import logging
import json
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.questions import QuestionBank, QuestionOption

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

TRANSLATION_PROMPT = """You are an expert translator for the Gujarat State Education Board (GSEB).
Translate the following English school questions into {target_lang}.
Ensure the mathematical terminology, scientific terminology, and grammatical structure are natural for {target_lang}.

You must return EXACTLY valid JSON in this format:
[
  {{
    "id": 123,
    "q": "Translated Question Text",
    "opt": ["Translated Option 1", "Translated Option 2", "Translated Option 3", "Translated Option 4"],
    "exp": "Translated Explanation"
  }}
]

Input Questions (JSON):
{input_json}
"""

async def _call_gemini(prompt: str) -> list[dict]:
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        for attempt in range(5):
            try:
                response = await client.post(GEMINI_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503) and attempt < 4:
                    logger.warning(f"Gemini API {e.response.status_code} error, retrying in {10 * (attempt + 1)}s...")
                    await asyncio.sleep(10 * (attempt + 1))
                    continue
                import traceback
                logger.error(f"Gemini Translation Error: {e}\n{traceback.format_exc()}")
                if 'response' in locals():
                    logger.error(f"Gemini Response: {response.text}")
                return []
            except Exception as e:
                import traceback
                logger.error(f"Gemini Translation Error: {e}\n{traceback.format_exc()}")
                if 'response' in locals():
                    logger.error(f"Gemini Response: {response.text}")
                return []


async def translate_paper_questions(db: AsyncSession, paper_id: int, target_lang: str):
    """
    Translates all missing questions in a paper to the target language.
    target_lang: 'hindi' or 'gujarati'
    """
    target_lang = target_lang.lower()
    if target_lang not in ['hindi', 'gujarati']:
        return

    # Fetch all questions for this paper
    from app.db.models.papers import PaperQuestion
    
    result = await db.execute(
        select(QuestionBank)
        .join(PaperQuestion, PaperQuestion.question_id == QuestionBank.id)
        .where(PaperQuestion.paper_id == paper_id)
    )
    questions = result.scalars().all()

    # Filter questions that need translation
    to_translate = []
    for q in questions:
        if target_lang == 'hindi' and not q.question_text_hi:
            to_translate.append(q)
        elif target_lang == 'gujarati' and not q.question_text_gu:
            to_translate.append(q)

    if not to_translate:
        return # Everything is already translated!

    logger.info(f"Translating {len(to_translate)} questions to {target_lang} for paper {paper_id}")

    # Fetch options for the ones needing translation
    q_ids = [q.id for q in to_translate]
    opt_result = await db.execute(
        select(QuestionOption).where(QuestionOption.question_id.in_(q_ids)).order_by(QuestionOption.sequence)
    )
    options = opt_result.scalars().all()

    # Build input payload
    input_data = []
    for q in to_translate:
        q_opts = [o for o in options if o.question_id == q.id]
        input_data.append({
            "id": q.id,
            "q": q.question_text_en,
            "opt": [o.option_text_en for o in q_opts],
            "exp": q.explanation_en or ""
        })

    # Gemini might drop the connection if the generation is too massive. 
    # We will batch the translations into chunks of 5 questions.
    translated_data = []
    chunk_size = 5
    
    for i in range(0, len(input_data), chunk_size):
        chunk = input_data[i:i + chunk_size]
        prompt = TRANSLATION_PROMPT.format(
            target_lang=target_lang.capitalize(),
            input_json=json.dumps(chunk, indent=2)
        )
        logger.info(f"Translating chunk {i//chunk_size + 1}/{(len(input_data) + chunk_size - 1)//chunk_size} ({len(chunk)} questions)...")
        chunk_result = await _call_gemini(prompt)
        if chunk_result:
            translated_data.extend(chunk_result)

    if not translated_data:
        logger.error("Failed to translate paper questions")
        return

    # Map translations back to the database
    for t_item in translated_data:
        q_id = t_item.get("id")
        if not q_id: continue
        
        # Update QuestionBank
        q_update = {}
        if target_lang == 'hindi':
            q_update["question_text_hi"] = t_item.get("q", "")
            q_update["explanation_hi"] = t_item.get("exp", "")
        else:
            q_update["question_text_gu"] = t_item.get("q", "")
            q_update["explanation_gu"] = t_item.get("exp", "")
            
        await db.execute(
            update(QuestionBank).where(QuestionBank.id == q_id).values(**q_update)
        )
        
        # Update Options
        opts_translated = t_item.get("opt", [])
        if len(opts_translated) == 4:
            q_opts = [o for o in options if o.question_id == q_id]
            for i, opt in enumerate(q_opts):
                o_update = {}
                if target_lang == 'hindi':
                    o_update["option_text_hi"] = opts_translated[i]
                else:
                    o_update["option_text_gu"] = opts_translated[i]
                    
                await db.execute(
                    update(QuestionOption).where(QuestionOption.id == opt.id).values(**o_update)
                )

    await db.commit()
    logger.info(f"Successfully translated and cached {len(translated_data)} questions in {target_lang}")
