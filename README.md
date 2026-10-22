# task-flow

개인용 Task 카드 관리 웹 앱. 설계 문서: PRD.md, ARCHITECTURE.md, DECISIONS.md.

현재 단계: M1 (Task 등록·상태 변경·수정·삭제, SQLite 저장). 로그인과 사용자별 Task(R-009)는 M1 범위에 없다.

## 구조

- `backend/` API (FastAPI, uv로 관리)
- `frontend/` 화면 (React·Vite)

## API 실행

```powershell
cd backend
uv run uvicorn app.main:app --port 8000
```

확인: http://127.0.0.1:8000/health → `{"status":"ok"}`

## 화면 실행

Node.js가 필요하다(개발 환경은 DEV-ENVIRONMENT.md 참고). API를 먼저 띄운 뒤:

```powershell
cd frontend
npm install
npm run dev
```

확인: http://localhost:5173 → "API 상태: ok"

## API 테스트

```powershell
cd backend
uv run pytest
```

카드는 `backend/data/taskflow.db`(Git 제외)에 저장된다. 다른 위치를 쓰려면 환경 변수 `TASKFLOW_DB`를 지정한다.
