from pathlib import Path
from io import BytesIO
import json
import os
from typing import Dict, Any

import pandas as pd
from pypdf import PdfReader
from docx import Document
from dotenv import load_dotenv
from google import genai


load_dotenv()


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".csv",
    ".xlsx",
}


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
# CLEAN JSON RESPONSE
# =========================================================

def _clean_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    return text


# =========================================================
# DOCUMENT EXTRACTION
# =========================================================

def extract_text_from_document(
    file_bytes: bytes,
    filename: str
) -> dict:

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if extension == ".pdf":
        return _extract_pdf(file_bytes)

    if extension == ".docx":
        return _extract_docx(file_bytes)

    if extension == ".txt":
        return _extract_txt(file_bytes)

    if extension == ".csv":
        return _extract_csv(file_bytes)

    if extension == ".xlsx":
        return _extract_xlsx(file_bytes)

    raise ValueError(
        "Unable to process the uploaded document."
    )


# =========================================================
# PDF
# =========================================================

def _extract_pdf(file_bytes: bytes) -> dict:

    reader = PdfReader(BytesIO(file_bytes))

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())

    text = "\n\n".join(
        f"--- Page {index + 1} ---\n{page_text}"
        for index, page_text in enumerate(pages)
        if page_text
    )

    return {
        "document_type": "PDF",
        "page_count": len(reader.pages),
        "text": text,
    }


# =========================================================
# DOCX
# =========================================================

def _extract_docx(file_bytes: bytes) -> dict:

    document = Document(BytesIO(file_bytes))

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    text = "\n".join(paragraphs)

    return {
        "document_type": "DOCX",
        "paragraph_count": len(paragraphs),
        "text": text,
    }


# =========================================================
# TXT
# =========================================================

def _extract_txt(file_bytes: bytes) -> dict:

    text = file_bytes.decode(
        "utf-8",
        errors="replace"
    )

    return {
        "document_type": "TXT",
        "text": text,
    }


# =========================================================
# CSV
# =========================================================

def _extract_csv(file_bytes: bytes) -> dict:

    dataframe = pd.read_csv(
        BytesIO(file_bytes)
    )

    return {
        "document_type": "CSV",
        "rows": len(dataframe),
        "columns": list(dataframe.columns),
        "text": dataframe.to_string(
            index=False
        ),
    }


# =========================================================
# XLSX
# =========================================================

def _extract_xlsx(file_bytes: bytes) -> dict:

    dataframe = pd.read_excel(
        BytesIO(file_bytes)
    )

    return {
        "document_type": "XLSX",
        "rows": len(dataframe),
        "columns": list(dataframe.columns),
        "text": dataframe.to_string(
            index=False
        ),
    }


# =========================================================
# AI DOCUMENT ANALYSIS
# =========================================================

def analyze_document(
    extracted_text: str,
    filename: str
) -> Dict[str, Any]:

    if not extracted_text or not extracted_text.strip():
        raise ValueError(
            "Document does not contain readable text."
        )

    prompt = f"""
You are an AI document intelligence assistant.

Analyze the following business document.

Return ONLY valid JSON.

Required JSON structure:

{{
    "document_type": "Invoice, Contract, Report, Receipt, Resume, Email, Form, or Other",

    "summary": "A short summary of the document",

    "important_information": [
        "important point 1",
        "important point 2"
    ],

    "structured_fields": {{
        "invoice_number": null,
        "vendor": null,
        "invoice_date": null,
        "amount": null,
        "tax": null,
        "total_amount": null,
        "due_date": null,
        "payment_status": null
    }},

    "missing_fields": [],

    "confidence_score": 0.0,

    "short_report": {{
        "title": "Document Intelligence Report",
        "overview": "Short business overview",
        "key_findings": [
            "finding 1",
            "finding 2"
        ],
        "risk_flags": [
            "risk or issue"
        ],
        "recommended_action": "Recommended next action"
    }}
}}

Rules:

1. Identify the most appropriate document type.

2. Provide a concise summary.

3. Extract the most important business information.

4. Extract structured fields when the document contains
   those values.

5. For invoice documents, use these fields:

   - invoice_number
   - vendor
   - invoice_date
   - amount
   - tax
   - total_amount
   - due_date
   - payment_status

6. If a structured field is not present in the document,
   return null.

7. Do not invent information.

8. If amount and tax are available, total_amount may be
   calculated as amount + tax.

9. missing_fields must contain important expected fields
   that are absent.

10. For non-invoice documents, keep invoice-specific fields
    as null unless equivalent information is clearly present.

11. The short_report must be based only on information
    found in the document.

12. key_findings should contain the most relevant business
    findings.

13. risk_flags should contain actual issues found in the
    document. If there are no obvious risks, return [].

14. recommended_action should be practical and based on
    the document.

15. confidence_score must be between 0.0 and 1.0.

16. Return ONLY valid JSON.
Do not include markdown or explanations outside the JSON.

Filename:

{filename}

Document content:

{extracted_text}
"""

    try:

        client = _get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        result_text = response.text.strip()

        result_text = _clean_json(
            result_text
        )

        result = json.loads(
            result_text
        )

        # -------------------------------------------------
        # DOCUMENT TYPE
        # -------------------------------------------------

        document_type = str(
            result.get(
                "document_type",
                "Other"
            )
        ).strip()

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        summary = str(
            result.get(
                "summary",
                "Document analyzed successfully."
            )
        ).strip()

        # -------------------------------------------------
        # IMPORTANT INFORMATION
        # -------------------------------------------------

        important_information = result.get(
            "important_information",
            []
        )

        if not isinstance(
            important_information,
            list
        ):
            important_information = [
                str(important_information)
            ]

        # -------------------------------------------------
        # STRUCTURED FIELDS
        # -------------------------------------------------

        structured_fields = result.get(
            "structured_fields",
            {}
        )

        if not isinstance(
            structured_fields,
            dict
        ):
            structured_fields = {}

        expected_fields = [
            "invoice_number",
            "vendor",
            "invoice_date",
            "amount",
            "tax",
            "total_amount",
            "due_date",
            "payment_status",
        ]

        for field in expected_fields:

            if field not in structured_fields:
                structured_fields[field] = None

        # -------------------------------------------------
        # MISSING FIELDS
        # -------------------------------------------------

        missing_fields = result.get(
            "missing_fields",
            []
        )

        if not isinstance(
            missing_fields,
            list
        ):
            missing_fields = [
                str(missing_fields)
            ]

        missing_fields = list(
            dict.fromkeys(
                str(field).strip()
                for field in missing_fields
                if str(field).strip()
            )
        )

        # -------------------------------------------------
        # CONFIDENCE SCORE
        # -------------------------------------------------

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

        # -------------------------------------------------
        # SHORT REPORT
        # -------------------------------------------------

        short_report = result.get(
            "short_report",
            {}
        )

        if not isinstance(
            short_report,
            dict
        ):
            short_report = {}

        report_title = str(
            short_report.get(
                "title",
                "Document Intelligence Report"
            )
        ).strip()

        report_overview = str(
            short_report.get(
                "overview",
                summary
            )
        ).strip()

        key_findings = short_report.get(
            "key_findings",
            []
        )

        if not isinstance(
            key_findings,
            list
        ):
            key_findings = [
                str(key_findings)
            ]

        risk_flags = short_report.get(
            "risk_flags",
            []
        )

        if not isinstance(
            risk_flags,
            list
        ):
            risk_flags = [
                str(risk_flags)
            ]

        recommended_action = str(
            short_report.get(
                "recommended_action",
                "Review the document and proceed according to business policy."
            )
        ).strip()

        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return {
            "document_type": document_type,

            "summary": summary,

            "important_information":
                important_information,

            "structured_fields":
                structured_fields,

            "missing_fields":
                missing_fields,

            "confidence_score":
                confidence_score,

            "short_report": {
                "title": report_title,
                "overview": report_overview,
                "key_findings": key_findings,
                "risk_flags": risk_flags,
                "recommended_action":
                    recommended_action,
            },

            "analysis_source":
                "GEMINI",
        }

    except Exception as exc:

        print(
            f"Document AI analysis unavailable: {exc}"
        )

        # -------------------------------------------------
        # SAFE FALLBACK
        # -------------------------------------------------

        return {
            "document_type": "Other",

            "summary": (
                "The document was successfully "
                "extracted, but AI analysis "
                "was unavailable."
            ),

            "important_information": [],

            "structured_fields": {
                "invoice_number": None,
                "vendor": None,
                "invoice_date": None,
                "amount": None,
                "tax": None,
                "total_amount": None,
                "due_date": None,
                "payment_status": None,
            },

            "missing_fields": [],

            "confidence_score": 0.0,

            "short_report": {
                "title":
                    "Document Intelligence Report",
                "overview":
                    "AI analysis was unavailable.",
                "key_findings": [],
                "risk_flags": [],
                "recommended_action":
                    "Review the extracted document manually.",
            },

            "analysis_source":
                "LOCAL_FALLBACK",

            "fallback_reason":
                "Gemini API unavailable.",
        }