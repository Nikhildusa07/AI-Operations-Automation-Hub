from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.templating import Jinja2Templates

from app.services.document_service import (
    extract_text_from_document,
    analyze_document,
)


router = APIRouter(
    prefix="/documents",
    tags=["Document Intelligence"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


# =========================================================
# DOCUMENT INTELLIGENCE PAGE
# GET /documents
# =========================================================

@router.get("")
@router.get("/")
async def documents_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="document_dashboard.html",
        context={
            "admin_username": request.session.get(
                "admin_username",
                "Admin",
            ),
        },
    )


# =========================================================
# DOCUMENT INTELLIGENCE PAGE ALIAS
# GET /documents-ui
# =========================================================

@router.get("/ui")
async def documents_ui(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="document_dashboard.html",
        context={
            "admin_username": request.session.get(
                "admin_username",
                "Admin",
            ),
        },
    )


# =========================================================
# EXTRACT DOCUMENT
# POST /documents/extract
# =========================================================

@router.post("/extract")
async def extract_document(
    file: UploadFile = File(...),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        result = extract_text_from_document(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        return {
            "success": True,
            "filename": file.filename,
            "file_size": len(file_bytes),
            "result": result,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing failed: "
                f"{str(exc)}"
            ),
        )


# =========================================================
# AI DOCUMENT ANALYSIS
# POST /documents/analyze
# =========================================================

@router.post("/analyze")
async def analyze_uploaded_document(
    file: UploadFile = File(...),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    try:
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

        extracted_text = ""

        if isinstance(extracted, dict):
            extracted_text = extracted.get(
                "text",
                "",
            )
        elif isinstance(extracted, str):
            extracted_text = extracted

        analysis = analyze_document(
            extracted_text=extracted_text,
            filename=file.filename,
        )

        return {
            "success": True,
            "filename": file.filename,
            "file_size": len(file_bytes),
            "extraction": extracted,
            "ai_analysis": analysis,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Document AI analysis failed: "
                f"{str(exc)}"
            ),
        )