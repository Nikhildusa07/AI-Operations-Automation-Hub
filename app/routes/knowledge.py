from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.knowledge_service import (
    add_knowledge,
    get_knowledge,
    ask_knowledge_base
)


router = APIRouter(
    prefix="/api/knowledge",
    tags=["AI Knowledge Base"]
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class KnowledgeCreateRequest(BaseModel):
    title: str
    content: str
    category: str = "General"


class KnowledgeQuestionRequest(BaseModel):
    question: str


# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
def knowledge_health():

    return {
        "success": True,
        "module": "AI Knowledge Base",
        "status": "operational"
    }


# =========================================================
# ADD KNOWLEDGE
# =========================================================

@router.post("/add")
def create_knowledge(
    request: KnowledgeCreateRequest
):

    try:

        knowledge = add_knowledge(
            title=request.title,
            content=request.content,
            category=request.category
        )

        return {
            "success": True,
            "message": (
                "Knowledge added successfully."
            ),
            "knowledge": knowledge
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# =========================================================
# LIST KNOWLEDGE
# =========================================================

@router.get("/")
def list_knowledge():

    knowledge = get_knowledge()

    return {
        "success": True,
        "count": len(knowledge),
        "knowledge": knowledge
    }


# =========================================================
# ASK KNOWLEDGE BASE
# =========================================================

@router.post("/ask")
def ask_knowledge(
    request: KnowledgeQuestionRequest
):

    try:

        result = ask_knowledge_base(
            question=request.question
        )

        return {
            "success": True,
            "question": request.question,
            "result": result
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        print(
            f"Knowledge base error: {repr(exc)}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process knowledge base question."
            )
        )