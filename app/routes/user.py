from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter(
    prefix="/user",
    tags=["User Portal"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


@router.get("/")
def user_portal(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="user.html",
    )