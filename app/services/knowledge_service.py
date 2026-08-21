import json
import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from google import genai

load_dotenv()


# =========================================================
# GEMINI CLIENT
# =========================================================

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(api_key=api_key)


# =========================================================
# CLEAN JSON
# =========================================================

def _clean_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    return text


# =========================================================
# KNOWLEDGE STORAGE
# =========================================================

_knowledge_base: List[Dict[str, Any]] = []


# =========================================================
# ADD KNOWLEDGE
# =========================================================

def add_knowledge(
    title: str,
    content: str,
    category: str = "General"
) -> Dict[str, Any]:

    if not title or not title.strip():
        raise ValueError(
            "Knowledge title is required."
        )

    if not content or not content.strip():
        raise ValueError(
            "Knowledge content is required."
        )

    knowledge_id = len(_knowledge_base) + 1

    item = {
        "id": knowledge_id,
        "title": title.strip(),
        "content": content.strip(),
        "category": category.strip() or "General"
    }

    _knowledge_base.append(item)

    return item


# =========================================================
# LIST KNOWLEDGE
# =========================================================

def get_knowledge() -> List[Dict[str, Any]]:
    return _knowledge_base


# =========================================================
# SIMPLE RELEVANCE SEARCH
# =========================================================

def _search_knowledge(
    question: str
) -> List[Dict[str, Any]]:

    question_words = {
        word.lower().strip(".,?!")
        for word in question.split()
        if len(word) > 2
    }

    scored_items = []

    for item in _knowledge_base:

        searchable_text = (
            f"{item['title']} "
            f"{item['content']} "
            f"{item['category']}"
        ).lower()

        score = sum(
            1
            for word in question_words
            if word in searchable_text
        )

        if score > 0:
            scored_items.append(
                (score, item)
            )

    scored_items.sort(
        key=lambda value: value[0],
        reverse=True
    )

    return [
        item
        for _, item in scored_items[:5]
    ]


# =========================================================
# AI KNOWLEDGE BASE QUESTION
# =========================================================

def ask_knowledge_base(
    question: str
) -> Dict[str, Any]:

    if not question or not question.strip():
        raise ValueError(
            "Question is required."
        )

    relevant_items = _search_knowledge(
        question
    )

    if not relevant_items:

        return {
            "answer": (
                "I could not find relevant information "
                "in the knowledge base."
            ),
            "sources": [],
            "confidence_score": 0.0,
            "analysis_source": "KNOWLEDGE_BASE"
        }

    context_parts = []

    for item in relevant_items:

        context_parts.append(
            f"Title: {item['title']}\n"
            f"Category: {item['category']}\n"
            f"Content: {item['content']}"
        )

    context = "\n\n".join(
        context_parts
    )

    prompt = f"""
You are an AI Knowledge Base Assistant.

Answer the user's question using ONLY the
provided knowledge base information.

Do not invent information.

Return ONLY valid JSON.

Required structure:

{{
    "answer": "Clear answer to the user's question",
    "confidence_score": 0.0
}}

Rules:

1. Use only the provided knowledge.
2. If the knowledge does not contain the answer,
   clearly say that the information is unavailable.
3. Do not assume or invent policies, prices,
   dates, or business information.
4. confidence_score must be between 0.0 and 1.0.

User question:

{question}

Knowledge base:

{context}
"""

    try:

        client = _get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result_text = response.text.strip()

        result_text = _clean_json(
            result_text
        )

        result = json.loads(
            result_text
        )

        answer = str(
            result.get(
                "answer",
                "No answer available."
            )
        ).strip()

        confidence_score = float(
            result.get(
                "confidence_score",
                0.75
            )
        )

        confidence_score = max(
            0.0,
            min(
                1.0,
                confidence_score
            )
        )

        sources = [
            {
                "id": item["id"],
                "title": item["title"],
                "category": item["category"]
            }
            for item in relevant_items
        ]

        return {
            "answer": answer,
            "sources": sources,
            "confidence_score": confidence_score,
            "analysis_source": "GEMINI"
        }

    except Exception as exc:

        print(
            f"Knowledge base AI analysis unavailable: "
            f"{repr(exc)}"
        )

        return {
            "answer": (
                "The knowledge base information was found, "
                "but AI analysis is currently unavailable."
            ),
            "sources": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "category": item["category"]
                }
                for item in relevant_items
            ],
            "confidence_score": 0.0,
            "analysis_source": "LOCAL_FALLBACK",
            "fallback_reason": (
                "Gemini API unavailable."
            )
        }