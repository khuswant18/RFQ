from fastapi import APIRouter, Request

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive WhatsApp webhook events (from Twilio or Meta).
    """
    data = await request.json()
    
    # TODO: Process incoming WhatsApp message
    # Extract text/image, create RFQ, trigger pipeline
    
    return {"status": "received", "message": "WhatsApp webhook received"}
