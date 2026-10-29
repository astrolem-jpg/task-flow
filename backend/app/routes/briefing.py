from fastapi import APIRouter, Depends

from app import ai_briefing
from app.auth import get_current_user
from app.schemas import BriefingResponse, User

# 로그인한 사용자의 카드를 읽기만 한다. POST /tasks, /tasks/{id}...와 경로가 겹치지 않는다.
router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


@router.post("/briefing", response_model=BriefingResponse)
def tasks_briefing(user: User = Depends(get_current_user)) -> BriefingResponse:
    return BriefingResponse(**ai_briefing.briefing(user.id))
