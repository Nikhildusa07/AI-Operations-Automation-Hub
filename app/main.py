import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates

from .database import engine, Base
from . import models

from .routes.auth import router as auth_router
from .routes.requests import router as requests_router
from .routes.web_form import router as web_form_router
from .routes.dashboard import router as dashboard_router
from .routes.reviews import router as reviews_router
from .routes.data import router as data_router
from .routes.emails import router as emails_router
from .routes.decision import router as decision_router
from .routes.support import router as support_router
from .routes.documents import router as documents_router
from .routes.automation import router as automation_router
from .routes.tasks import router as tasks_router
from .routes.knowledge import router as knowledge_router
from .routes.meetings import router as meetings_router
from .routes.scheduler import router as scheduler_router
from .routes.activity_logs import router as activity_logs_router
from .routes.invoices import router as invoices_router
from .routes.ai_cost import router as ai_cost_router
from .routes.user import router as user_router
from .routes.customer import router as customer_router
from .routes.reports import router as reports_router
from .routes.external_api import router as external_api_router



# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="AI-Powered Business Operations Automation System",
    description="AI-powered business request automation system",
    version="1.0.0",
)


# =========================================================
# SESSION MIDDLEWARE
# =========================================================

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not configured in the environment.")

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="business_admin_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=IS_PRODUCTION,
)


# =========================================================
# TEMPLATES
# =========================================================

templates = Jinja2Templates(directory="app/templates")


# =========================================================
# ROUTERS
# =========================================================

app.include_router(auth_router)
app.include_router(requests_router)
app.include_router(web_form_router)
app.include_router(dashboard_router)
app.include_router(reviews_router)
app.include_router(data_router)
app.include_router(emails_router)
app.include_router(decision_router)
app.include_router(support_router)
app.include_router(documents_router)
app.include_router(automation_router)
app.include_router(tasks_router)
app.include_router(knowledge_router)
app.include_router(meetings_router)
app.include_router(scheduler_router)
app.include_router(activity_logs_router)
app.include_router(invoices_router)
app.include_router(ai_cost_router)
app.include_router(customer_router)
app.include_router(user_router)
app.include_router(reports_router)
app.include_router(external_api_router)



# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Operations Automation Hub",
        "version": "1.0.0",
    }

@app.get("/business-request", response_class=HTMLResponse)
def business_request(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="request_form.html",
    )
# =========================================================
# MAIN LANDING PAGE
# =========================================================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
    )
@app.get("/customer/", response_class=HTMLResponse)
def customer_portal(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="request_form.html",
    )