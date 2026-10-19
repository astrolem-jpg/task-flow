# DEV-ENVIRONMENT: 개발 환경 기록

확인 날짜: 2026-10-19
확인 방법: 각 도구의 `--version` 실행 결과를 그대로 적었다. 이 기록을 만들면서 설치한 것은 없다.

## 운영체제

| 항목 | 값 |
|---|---|
| 운영체제 | Microsoft Windows 11 Pro 10.0.22631 (64비트, AMD64) |

## 셸

| 항목 | 값 |
|---|---|
| 기본 셸 | PowerShell 7.6.7 |
| Bash | Git Bash를 보조로 쓸 수 있음. PowerShell의 PATH에서는 `bash` 명령이 인식되지 않음 |

## 도구별 버전

| 도구 | 명령 | 결과 (그대로) |
|---|---|---|
| git | `git --version` | `git version 2.56.0.windows.2` |
| node | `node --version` | 실행되지 않음: `'node' 용어는 cmdlet, 함수, 스크립트 파일 또는 실행 프로그램의 이름으로 인식되지 않습니다.` |
| npm | `npm --version` | 실행되지 않음: `'npm' 용어는 cmdlet, 함수, 스크립트 파일 또는 실행 프로그램의 이름으로 인식되지 않습니다.` |
| uv | `uv --version` | `uv 0.13.1 (62faed335 2026-10-13 x86_64-pc-windows-msvc)` |
| python | `python --version` | `Python` (버전 번호 없음) |
| python (uv 설치본) | `C:\Users\EZ\.local\bin\python3.12.exe --version` | `Python 3.12.15` |

## 해석

- `node`와 `npm`은 이 컴퓨터에 설치되어 있지 않다. 화면(React·Vite)을 만들려면 먼저 Node.js가 필요하다.
- PATH의 `python`은 Microsoft Store 연결용 껍데기이며 실제 Python이 아니다. 이 프로젝트의 Python은 uv가 설치한 3.12.15를 쓴다.
- SQLite는 별도 설치 없이 Python 3.12.15의 `sqlite3` 모듈(SQLite 3.53.1)로 확인했다. 이 값은 위 표의 `--version` 결과가 아니라 `import sqlite3`로 읽은 값이다.

## 새로 설치한 것

없음.

설치가 필요한 것으로 확인된 것: Node.js (npm 포함). 설치하면 이 절에 날짜와 버전을 적고 위 표의 node, npm 줄을 새 `--version` 결과로 바꾼다.

## Node.js 설치 기록

날짜: 2026-10-19
- `winget install OpenJS.NodeJS.LTS`와 `winget search`가 종료 코드 -1073741819(접근 위반)로 비정상 종료되어 winget은 쓰지 못했다.
- 대신 nodejs.org의 공식 zip(node-v24.22.0-win-x64.zip)을 받아 SHA256이 SHASUMS256.txt와 일치함을 확인한 뒤 `%LOCALAPPDATA%\Programs\nodejs`에 풀고 사용자 PATH에 추가했다. (관리자 권한 불필요)

| 도구 | 결과 |
|---|---|
| node | `v24.22.0` |
| npm | `11.19.1` |

이미 열려 있던 터미널은 PATH가 갱신되지 않으므로 새로 열어야 한다.
