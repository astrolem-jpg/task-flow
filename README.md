# task-flow

개인용 Task 카드 관리 웹 앱. 설계 문서: PRD.md, ARCHITECTURE.md, DECISIONS.md.

현재 단계: M2 (M1의 Task 등록·상태 변경·수정·삭제, SQLite 저장에 더해 가입·로그인·로그아웃과 사용자별 Task, R-009). 비밀번호 찾기, 소셜 로그인, 팀 공유는 만들지 않는다.

## 구조

- `backend/` API (FastAPI, uv로 관리)
- `frontend/` 화면 (React·Vite)

## API 실행

처음 한 번, `backend/.env`(Git 제외)에 세션 비밀값을 넣는다. 값이 비어 있으면 API가 시작되지 않는다.

```
SESSION_SECRET=<긴 임의의 문자열>
```

DB 구조는 Alembic으로 관리한다(D-024). **기존 `taskflow.db`가 있으면 먼저 `.db`로 끝나는 이름으로 백업한 뒤** 적용한다. 적용하기 전에 API를 켜면 새 테이블이 없어 `/auth/*`가 오류를 낸다.

```powershell
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --env-file .env --port 8000
```

확인: http://127.0.0.1:8000/health → `{"status":"ok"}`

로그인 전에 만든 카드는 **처음 가입하는 사람**의 카드가 된다(D-021).

## 화면 실행

Node.js가 필요하다(개발 환경은 DEV-ENVIRONMENT.md 참고). API를 먼저 띄운 뒤:

```powershell
cd frontend
npm install
npm run dev
```

확인: http://localhost:5173 → 로그인하지 않았으면 `/login`으로 이동한다. 가입한 뒤 로그인하면 카드 보드가 보인다.

화면은 열린 주소의 호스트로 API(8000 포트)를 부른다(D-025). 쿠키가 전달되려면 화면과 API의 호스트가 같아야 하므로 `localhost`와 `127.0.0.1`을 섞어 쓰지 않는다. 다른 API 주소를 쓰려면 환경 변수 `VITE_API_URL`을 지정한다.

## API 테스트

```powershell
cd backend
uv run pytest
```

카드는 `backend/data/taskflow.db`(Git 제외)에 저장된다. 다른 위치를 쓰려면 환경 변수 `TASKFLOW_DB`를 지정한다.
