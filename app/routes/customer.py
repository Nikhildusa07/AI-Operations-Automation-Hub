from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Request as RequestModel


router = APIRouter(
    prefix="/customer",
    tags=["Customer Dashboard"]
)

templates = Jinja2Templates(
    directory="app/templates"
)


# =========================================================
# CUSTOMER DASHBOARD
# =========================================================

@router.get("/", response_class=HTMLResponse)
def customer_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    customer_email = request.session.get("customer_email")

    if not customer_email:
        return RedirectResponse(
            url="/web/",
            status_code=303
        )

    requests = (
        db.query(RequestModel)
        .filter(
            RequestModel.customer_email == customer_email
        )
        .order_by(
            RequestModel.created_at.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="customer_dashboard.html",
        context={
            "customer_email": customer_email,
            "requests": requests,
        }
    )


# =========================================================
# CUSTOMER LOGOUT
# =========================================================

@router.get("/logout")
def customer_logout(request: Request):

    request.session.pop("customer_email", None)
    request.session.pop("customer_name", None)

    return RedirectResponse(
        url="/web/",
        status_code=303
    )