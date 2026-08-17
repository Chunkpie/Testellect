from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_db
from app.services.omr_service import OMRService

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Integration"])
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Mock WhatsApp Webhook endpoint.
    In a real scenario, Twilio or WhatsApp Business API hits this endpoint 
    with image media URLs when a teacher sends an OMR sheet.
    """
    try:
        # For Twilio, data is form-encoded
        form_data = await request.form()
        
        # In a real app, you'd extract MediaUrl0, From (phone number), etc.
        # body = form_data.get("Body", "")
        # media_url = form_data.get("MediaUrl0")
        # sender = form_data.get("From")
        
        logger.info(f"Received WhatsApp Webhook: {dict(form_data)}")
        
        # Mock logic: If an image is sent, process it
        # Since this is a demo, we assume the omr_service will be triggered
        # via a background task so we can reply to WhatsApp quickly.
        
        # Example pseudo-code for background processing:
        # omr_service = OMRService()
        # background_tasks.add_task(omr_service.process_whatsapp_omr, db, media_url, sender)
        
        return {"status": "received", "message": "OMR image received. Processing..."}
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
