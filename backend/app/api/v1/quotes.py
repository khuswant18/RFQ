from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["quotes"])


@router.get("/rfq/{rfq_id}/quote")
async def get_quote(rfq_id: str):
    """Download the generated quote PDF for an RFQ."""
    try:
        pdf_path = f"storage/quotes/QT-{rfq_id}.pdf"
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Quote not found or not yet generated")
        return FileResponse(pdf_path, media_type="application/pdf")
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"❌ /rfq/{rfq_id}/quote error: {str(exc)}")
        return {
            "status": "error",
            "error": str(exc),
            "message": "Failed to fetch quote. Check server logs."
        }
