from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.data_service import (
    load_dataset,
    analyze_dataset,
    clean_dataset,
    generate_business_insights,
)


router = APIRouter(
    prefix="/api/data",
    tags=["Data Processing"],
)


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
def data_health():
    return {
        "success": True,
        "module": "Data Processing",
        "status": "operational",
    }


# =========================================================
# ANALYZE DATASET
# =========================================================

@router.post("/analyze")
async def analyze_data(
    file: UploadFile = File(...),
):
    try:
        if not file.filename:
            raise ValueError("Filename is required.")

        file_bytes = await file.read()

        dataframe = load_dataset(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        analysis = analyze_dataset(
            dataframe=dataframe,
            filename=file.filename,
        )

        business_insights = generate_business_insights(
            analysis
        )

        return {
            "success": True,
            "filename": file.filename,
            "analysis": analysis,
            "business_insights": business_insights,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"DATA ANALYSIS ERROR: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process dataset.",
        )


# =========================================================
# AUTOMATED DATA CLEANING
# =========================================================

@router.post("/clean")
async def clean_data(
    file: UploadFile = File(...),
):
    try:
        if not file.filename:
            raise ValueError("Filename is required.")

        file_bytes = await file.read()

        dataframe = load_dataset(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        cleaned_dataframe, cleaning_report = clean_dataset(
            dataframe
        )

        cleaned_analysis = analyze_dataset(
            dataframe=cleaned_dataframe,
            filename=file.filename,
        )

        return {
            "success": True,
            "message": "Dataset cleaned successfully.",
            "filename": file.filename,
            "cleaning_report": cleaning_report,
            "cleaned_analysis": cleaned_analysis,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"DATA CLEANING ERROR: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to clean dataset.",
        )