import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/external", tags=["External API Integration"])


@router.get("/exchange-rate")
def exchange_rate(base: str = "USD", target: str = "INR"):
    """Third-party API integration used for operational currency information."""
    url = "https://api.frankfurter.app/latest"
    try:
        response = requests.get(url, params={"from": base.upper(), "to": target.upper()}, timeout=8)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "provider": "Frankfurter",
            "base": base.upper(),
            "target": target.upper(),
            "rate": data.get("rates", {}).get(target.upper()),
            "date": data.get("date"),
        }
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"External API unavailable: {exc}")
