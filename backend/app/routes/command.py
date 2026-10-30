from fastapi import APIRouter, Depends

from app import ai_command
from app.auth import get_current_user
from app.rules import clean_command
from app.schemas import CommandRequest, CommandResponse, User

# 로그인한 사용자의 카드를 읽기만 한다. 제안만 돌려주고 아무것도 저장하지 않는다.
router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


@router.post("/command", response_model=CommandResponse)
def tasks_command(
    body: CommandRequest, user: User = Depends(get_current_user)
) -> CommandResponse:
    text = clean_command(body.text)
    return CommandResponse(**ai_command.command(user.id, text))
