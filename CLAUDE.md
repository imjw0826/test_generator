# Study Question Generator

## Overview

Full-stack app for extracting study questions from university PDFs. Users upload textbook or sample-exam PDFs, the backend parses them into stored pages and figures, Claude extracts questions from rendered page images, and the frontend lets users browse the question bank or generate random study sets and exam PDFs.

Product focus: reliable PDF question extraction.

- Preserve raw and cleaned page text.
- Send Claude rendered page images (not PyMuPDF text) so math survives as LaTeX.
- Detect chapter headings locally and tag extracted questions.
- Organize uploaded documents and questions by subject.

## Stack

- Backend: FastAPI, SQLAlchemy 2.0, SQLite
- Frontend: Next.js App Router (React 19)
- PDF parsing: PyMuPDF (`fitz`)
- LLM: Anthropic Claude (`claude-sonnet-4-6` extraction, `claude-opus-4-7` solutions). DeepSeek is available via the Anthropic-compatible base URL when `X-LLM-Provider: deepseek` is sent.
- Math rendering: KaTeX
- Exam PDF generation: local LaTeX engine — `tectonic` (preferred), `xelatex`, `lualatex`, or `pdflatex`. No LLM call.

## Commands

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Backend tests
cd backend && source .venv/bin/activate && python -m pytest tests/ -v

# Frontend checks
cd frontend && npm run lint
cd frontend && npx tsc --noEmit
```

## Architecture Rules

- API routes stay thin; business logic belongs in `services/` and `core/`.
- PDF parsing, question extraction, and random selection are separate modules.
- Never generate questions from a raw PDF at request time; persist parsed pages and extracted questions first.
- LLM clients are constructed only via `app/core/llm_runtime.py`. Extraction lives in `app/core/question_extractor.py`; outline / translation / solutions live in their own `core/` modules.
- LLM output must be JSON and pass validation/retry handling.
- Prompts live in `app/prompts/` for the extraction prompt; smaller per-task prompts live next to their core module.
- `raw_text` and `cleaned_text` are both preserved on `ParsedPage`.
- Claude is used for extraction/translation/outline/solutions only — never for subject classification.
- Subject is selected or created at upload time; chapter tags come from local heading detection or contents pages parsed locally with Claude fallback.

## Workflow

1. `POST /api/upload` with `document_role` (`textbook` | `sample_exam`), `subject`, and `pdf_scope` (`chapter` | `full`). The current UI uses full PDF for textbooks and chapter PDF for sample exams.
2. `POST /api/documents/{id}/process` — parse pages, write figures, detect chapters. For `pdf_scope=full`, text-readable contents pages are parsed locally first; Claude Sonnet is a fallback JSON normalizer when local parsing cannot produce a usable outline.
3. `POST /api/documents/{id}/extract` — for full PDFs, pass selected `chapter_ranges`; backend renders selected pages to PNG, sends them to Claude Sonnet, then persists questions.
4. `GET /api/questions` to browse, `POST /api/study-set/random` for a random set, `POST /api/study-set/exam-pdf` or `/api/study-set/solutions-pdf` for a generated PDF.
5. `DELETE /api/reset` clears all uploaded documents, extracted data, and generated files.

## Endpoints

- `POST /api/upload`
- `GET /api/documents` / `GET /api/documents/{id}` / `DELETE /api/documents/{id}`
- `GET /api/documents/{id}/chapters`
- `POST /api/documents/{id}/process` / `POST /api/documents/{id}/extract` / `POST /api/documents/{id}/reprocess`
- `DELETE /api/reset`
- `GET /api/questions` / `GET /api/questions/{id}` / `GET /api/questions/filter-options`
- `POST /api/questions/{id}/translate`
- `POST /api/study-set/random`
- `POST /api/study-set/exam-pdf` / `POST /api/study-set/solutions-pdf`

The `X-LLM-Provider` request header (`claude` | `deepseek`) overrides the LLM provider for the duration of a single request. Claude supports image-based extraction; DeepSeek is used through the text-compatible API path.

## Configuration

All config is loaded by `app/config.py` from `backend/.env`. See `backend/.env.example`. Important keys:

- `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY` — LLM credentials.
- `CORS_ORIGINS` — comma-separated allowed frontend origins.
- `DATABASE_URL`, `UPLOAD_DIR`, `FIGURE_DIR`, `GENERATED_EXAM_DIR` — storage locations.
- `DEBUG` — must be `false` in production (controls SQLAlchemy echo).

## Layout

```
backend/app/
  api/         # thin route handlers
  core/        # PDF parsing, extraction, outline, translation, solutions, exam PDF, random selection
  services/    # orchestration (document_service, extraction_service, question_service)
  models/      # SQLAlchemy ORM (Document, ParsedPage, Question, PracticeSession)
  schemas/     # Pydantic request/response schemas
  prompts/     # extraction system prompt
  db/          # engine, session, runtime schema patcher
  config.py    # Settings (pydantic-settings)
  main.py      # FastAPI app, CORS, lifespan
backend/tests/ # pytest suite
frontend/src/
  app/         # App Router pages: /, /questions, /study-set
  components/  # FileUpload, DocumentList, QuestionCard, QuestionFilter, QuestionDetail, MathText, ModelSelector
  lib/         # api client, types
scripts/       # full_project_check.py, workflow_smoke.py
```

## Data Notes

- Uploaded PDFs: `backend/data/uploads`
- Extracted figures: `backend/data/figures`
- Generated exam PDFs: `backend/data/generated_exams`
- SQLite DB: `backend/data/study_questions.db`
- The SQLite schema is patched at runtime by `db/database.py:ensure_runtime_schema` for additive columns. This is local-dev convenience only; production should use real migrations.

## Hosting

This stack does not fit a serverless host (Vercel functions, Lambda, Cloud Run jobs). It needs a long-lived process with disk for uploads and a LaTeX binary in PATH.

- Frontend (Next.js): Vercel.
- Backend (FastAPI + SQLite + tectonic): Railway, Render, Fly.io, or any Docker host.

See `README.md` for the deployment walkthrough.
