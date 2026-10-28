from fastapi import APIRouter, Depends

from app import ai_suggest
from app.auth import get_current_user
from app.rules import clean_title
from app.schemas import SuggestRequest, SuggestResponse

# 로그인한 사용자만 쓸 수 있다. 제안만 돌려주며 DB의 카드를 읽거나 바꾸지 않는다.
router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


@router.post("/suggest", response_model=SuggestResponse)
def suggest_task(body: SuggestRequest) -> SuggestResponse:
    title = clean_title(body.title)
    return SuggestResponse(**ai_suggest.suggest(title, body.description))
