# test_generator (Study Question Generator)

## 1. 프로젝트 소개

교과서나 기출 시험지 PDF에서 연습문제를 자동으로 뽑아 문제은행을 만들고, 그 문제로 연습 세트와 시험지 PDF를 생성하는 대학 시험 대비용 웹앱입니다. 교재 속 문제를 일일이 옮겨 적지 않고도 과목·단원별로 골라 풀 수 있게 하는 것이 목적입니다.

## 2. 기술 스택

- **백엔드:** Python, FastAPI, SQLAlchemy, SQLite
- **프론트엔드:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4
- **PDF 분석:** PyMuPDF
- **AI:** Anthropic Claude (문제 추출·목차 정리·번역·풀이), DeepSeek (선택)
- **수식·시험지:** KaTeX, LaTeX (tectonic 권장)
- **배포:** Vercel(프론트엔드), 별도 컨테이너 호스트(백엔드)

## 3. 이용 방법

**웹사이트:** https://test-generator-black.vercel.app

1. 교과서 전체 PDF 또는 단원·기출 PDF를 과목 이름과 함께 올립니다.
2. **Parse**를 누르면 페이지와 그림을 분석하고, 교과서는 목차를 만들어 줍니다.
3. 목차에서 원하는 단원을 골라 **Extract**를 누르면 AI가 페이지 이미지를 읽어 문제를 수식 그대로 추출합니다.
4. 문제은행에서 과목·단원·검색어로 문제를 찾아보고, 한국어 번역을 볼 수 있습니다.
5. 무작위 연습 세트를 만들거나 시험지 PDF, 풀이 PDF를 내려받습니다.

로컬에서 실행하려면 Python 3.11+, Node 20+, LaTeX 엔진(`tectonic`)이 필요합니다.

```bash
git clone https://github.com/imjw0826/test_generator.git
cd test_generator

# 백엔드
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # ANTHROPIC_API_KEY 입력
uvicorn app.main:app --reload

# 프론트엔드 (새 터미널)
cd frontend
npm install
npm run dev
```

http://localhost:3000 을 엽니다. 백엔드는 http://localhost:8000 에서 실행됩니다. 웹에 직접 배포하는 절차는 `HOSTING.md`에 있습니다.

## 4. 최근 업데이트

2026-10-31
