# ⏱️ LIG DNA 근무시간 관리 (Work Time Tracker)

> **LIG DNA 워크스페이스 전용 모던 파이썬 Flask 기반 개인 근무시간 관리 웹 애플리케이션**

---

## 🌟 주요 기능

1. **출근 / 퇴근 기록**
   - `출근하기` / `퇴근하기` 버튼 한 번으로 현재 시간(KST) 기록
   - 같은 날 중복 출근·중복 퇴근, 출근 없이 퇴근하는 등의 오류 상태를 서버에서 검증

2. **오늘의 근무 상태**
   - 근무 전 / 근무 중 / 근무 종료 상태를 큰 카드로 표시
   - 근무 중일 때 1초 단위로 갱신되는 실시간 경과시간 타이머 (DB에는 출근 시각만 저장)
   - 오늘 근무시간, 예상 퇴근시간(목표 8시간 + 휴게 1시간 기준), 초과/부족 근무시간 표시

3. **주간 / 월간 통계**
   - 이번 주 요일별 근무시간 바 차트 + 주간 합계
   - 이번 달 총 근무일수, 총 근무시간, 평균 근무시간

4. **근무 기록 조회 / 수정 / 삭제**
   - 최근 근무 기록 목록 (최신순)
   - 이전/다음 날짜 이동 또는 날짜 선택으로 특정 날짜 기록 조회
   - 출근/퇴근/휴게시간을 수정하면 실제 근무시간을 자동 재계산
   - 삭제 시 확인 메시지 표시

5. **신뢰할 수 있는 데이터 보관**
   - Supabase(관리형 Postgres)를 사용하여 서버 재시작·재배포 후에도 데이터 영구 보존
   - 시간은 DB에 KST 텍스트로 저장, 근무시간은 분 단위 정수로 계산 후 화면에서 "N시간 M분"으로 변환

---

## 📁 디렉토리 구조

```
LIG_DNA_TODO_APP/
├── app.py                  # Flask 백엔드 서버 및 근무시간 REST API, Postgres(Supabase) 연동
├── requirements.txt        # 파이썬 의존성 패키지 (Flask, psycopg2-binary, python-dotenv 등)
├── vercel.json              # Vercel 배포 설정 (@vercel/python)
├── run.bat                 # 윈도우 더블클릭 실행 스크립트 (브라우저 자동 실행)
├── README.md               # 프로젝트 안내 문서
├── static/
│   ├── css/
│   │   └── style.css       # 모던 다크 글래스모피즘 스타일시트
│   └── js/
│       └── app.js          # 프론트엔드 비동기 API 통신, 실시간 타이머, 통계 렌더링
└── templates/
    └── index.html          # 메인 반응형 근무시간 대시보드 템플릿
```

---

## 🗄️ 데이터베이스

`work_records` 테이블 (앱 시작 시 `CREATE TABLE IF NOT EXISTS`로 자동 생성):

| 컬럼            | 설명                          |
| --------------- | ----------------------------- |
| id              | 근무 기록 고유 ID              |
| user_id         | 사용자 식별자 (현재는 `default` 고정, 로그인 기능 없음) |
| work_date       | 근무 날짜 (`YYYY-MM-DD`)        |
| clock_in        | 출근 시각 (`YYYY-MM-DD HH:MM:SS`, KST) |
| clock_out       | 퇴근 시각 (`YYYY-MM-DD HH:MM:SS`, KST) |
| break_minutes   | 휴게시간(분), 기본 60분         |
| work_minutes    | 실제 근무시간(분)               |
| created_at / updated_at | 레코드 생성/수정 시각    |

과거 Todo 앱에서 쓰던 `todos` 테이블은 삭제하지 않고 DB에 그대로 남아 있습니다 (앱 코드에서는 더 이상 참조하지 않음).

> ⚠️ **인증 관련 참고**: 이 앱에는 로그인 기능이 없습니다 (개인용 단일 사용자 앱). `user_id` 컬럼은 향후 다중 사용자 지원을 염두에 두고 만들어 두었을 뿐, 현재는 모든 데이터가 `default` 사용자로 기록/조회됩니다.

---

## 🚀 실행 방법

이 앱은 Postgres 데이터베이스가 필요합니다. 프로젝트 루트에 `.env` 파일을 만들고 `.env.example`을 참고해 `POSTGRES_URL`을 채워주세요.

### 방법 1. 더블 클릭으로 바로 실행 (가장 추천)
`.env` 설정 후, 폴더 내 `run.bat` 파일을 더블 클릭하면 자동으로 브라우저가 열리고 서버가 실행됩니다.

### 방법 2. 터미널 명령어로 직접 실행
```powershell
cd c:\Users\user\Desktop\260916_CLAUDE_RPA\LIG_DNA_TODO_APP
pip install -r requirements.txt
python app.py
```
브라우저에서 `http://127.0.0.1:5000` 으로 접속합니다.

## ☁️ Vercel 배포

이 저장소는 Vercel에서 바로 배포할 수 있도록 `vercel.json`이 구성되어 있습니다.

1. Vercel 대시보드에서 이 GitHub 저장소(`260916_LIG_G`)를 Import
2. Storage 탭에서 Postgres 데이터베이스를 생성 후 프로젝트에 연결 (환경변수 `POSTGRES_URL` 자동 주입)
3. Deploy

로컬에서 같은 DB로 테스트하려면 `vercel env pull .env` 명령으로 환경변수를 받아올 수 있습니다.
