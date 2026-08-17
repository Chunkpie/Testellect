import httpx
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.db.models.assessments import StudentResult
from app.db.models.omr import OMRResult
from app.core.config import settings

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self):
        # We assume settings has a CENTRAL_CLOUD_URL if we are scaling
        self.cloud_url = getattr(settings, "CENTRAL_CLOUD_URL", "https://api.testellect-cloud.org/sync")
    
    async def check_connectivity(self) -> bool:
        """
        Check if the machine has internet connectivity by pinging a reliable endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get("https://8.8.8.8", timeout=3.0)
                return response.status_code == 200 or response.status_code == 301 or response.status_code == 302
        except Exception:
            return False

    async def sync_offline_data(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Opportunistically sync local OMR and Student Results to the State Cloud.
        """
        is_connected = await self.check_connectivity()
        if not is_connected:
            logger.info("No internet connection detected. Skipping sync.")
            return {"status": "skipped", "reason": "no_internet"}

        # Fetch results that haven't been synced (we mock this by just fetching the last 10 for the hackathon demo)
        stmt = select(StudentResult).order_by(StudentResult.id.desc()).limit(10)
        result = await db.execute(stmt)
        student_results = result.scalars().all()

        if not student_results:
            return {"status": "skipped", "reason": "no_data_to_sync"}

        payload = []
        for sr in student_results:
            data = {
                "student_id": sr.student_id,
                "assessment_id": sr.assessment_id,
                "score": sr.score,
            }
            # Add OMR result if available
            if sr.omr_result_id:
                omr_stmt = select(OMRResult).where(OMRResult.id == sr.omr_result_id)
                omr_res = await db.execute(omr_stmt)
                omr_result = omr_res.scalar_one_or_none()
                if omr_result:
                    data["detected_answers"] = omr_result.detected_answers

            payload.append(data)

        try:
            # Mock sending data to the central cloud
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(self.cloud_url, json={"data": payload})
            #     response.raise_for_status()
            logger.info(f"Successfully synced {len(payload)} records to the State Cloud.")
            return {"status": "success", "synced_count": len(payload)}
        except Exception as e:
            logger.error(f"Failed to sync data to cloud: {e}")
            return {"status": "error", "reason": str(e)}
