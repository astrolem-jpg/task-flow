# task-flow

개인용 Task 카드 관리 웹 앱. 설계 문서: PRD.md, ARCHITECTURE.md, DECISIONS.md.

현재 단계: M0 (프로젝트 기본 구조). Task 기능, 데이터베이스, 로그인은 아직 없다.

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
