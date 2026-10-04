"""Ownership verification with generic bounded email-request acceptance."""

from fastapi import BackgroundTasks, Body, Request
from pydantic import EmailStr

from app.api.password_recovery import queue_account_email
from app.core.auth import fastapi_users
from app.schemas.user import UserRead

router = fastapi_users.get_verify_router(UserRead)
router.routes = [
    route for route in router.routes if getattr(route, "path", None) != "/request-verify-token"
]


async def prepare_registration_mail(request: Request, background: BackgroundTasks) -> None:
    request.state.registration_mail = background


@router.post("/request-verify-token", status_code=202)
async def request_verification(
    background: BackgroundTasks, email: EmailStr = Body(..., embed=True)
):
    await queue_account_email(background, str(email), "verify")
