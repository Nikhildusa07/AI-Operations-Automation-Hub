from fastapi import APIRouter, File, HTTPException, UploadFile

from ..services.document_service import (
    extract_text_from_document,
    analyze_document,
)


router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoice Processing"],
)


@router.get("/health")
def invoice_health():
    return {
        "success": True,
        "module": "Invoice Processing",
        "status": "operational",
    }


@router.post("/analyze")
async def analyze_invoice(
    file: UploadFile = File(...)
):
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required.",
            )

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        extracted = extract_text_from_document(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        extracted_text = extracted.get(
            "text",
            "",
        )

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Document does not contain readable text.",
            )

        analysis = analyze_document(
            extracted_text=extracted_text,
            filename=file.filename,
        )

        structured_fields = analysis.get(
            "structured_fields",
            {},
        )

        document_type = str(
            analysis.get(
                "document_type",
                "Other",
            )
        ).strip().lower()

        if "invoice" not in document_type:
            return {
                "success": False,
                "message": "Uploaded document is not identified as an invoice.",
                "filename": file.filename,
                "analysis": analysis,
            }

        return {
            "success": True,
            "message": "Invoice processed successfully.",
            "filename": file.filename,
            "document": {
                "document_type": analysis.get(
                    "document_type"
                ),
                "summary": analysis.get(
                    "summary"
                ),
                "invoice": {
                    "invoice_number": structured_fields.get(
                        "invoice_number"
                    ),
                    "vendor": structured_fields.get(
                        "vendor"
                    ),
                    "invoice_date": structured_fields.get(
                        "invoice_date"
                    ),
                    "amount": structured_fields.get(
                        "amount"
                    ),
                    "tax": structured_fields.get(
                        "tax"
                    ),
                    "total_amount": structured_fields.get(
                        "total_amount"
                    ),
                    "due_date": structured_fields.get(
                        "due_date"
                    ),
                    "payment_status": structured_fields.get(
                        "payment_status"
                    ),
                },
                "missing_fields": analysis.get(
                    "missing_fields",
                    [],
                ),
                "confidence_score": analysis.get(
                    "confidence_score",
                    0.0,
                ),
                "recommended_action": analysis.get(
                    "short_report",
                    {},
                ).get(
                    "recommended_action",
                    "",
                ),
            },
            "analysis_source": analysis.get(
                "analysis_source",
                "UNKNOWN",
            ),
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"INVOICE ANALYSIS ERROR: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Invoice processing failed.",
        )