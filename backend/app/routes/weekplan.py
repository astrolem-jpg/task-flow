from fastapi import APIRouter, Depends

from app import ai_weekplan
from app.auth import get_current_user
from app.schemas import User, WeekPlanResponse

# 로그인한 사용자의 카드를 읽기만 한다. POST /tasks, /tasks/{id}...와 경로가 겹치지 않는다.
router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


@router.post("/weekplan", response_model=WeekPlanResponse)
def tasks_weekplan(user: User = Depends(get_current_user)) -> WeekPlanResponse:
    return WeekPlanResponse(**ai_weekplan.weekplan(user.id))
