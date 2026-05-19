# Study Question Generator

## Project Overview

Full-stack app for university exam prep. Users upload textbook and sample-exam PDFs, the backend parses pages and figures, Claude extracts student-solvable questions from rendered page images, and users browse a question bank or generate random study sets / exam PDFs.

Current focus: reliable PDF question extraction with math, figures, subject organization, and chapter tagging.

## Tech Stack

- Backend: FastAPI + SQLAlchemy 2.0 + SQLite
- Frontend: Next.js App Router (React 19, Tailwind v4)
- PDF parsing: PyMuPDF
- LLM: Anthropic Claude — `claude-sonnet-4-6` (extraction, outline, translation), `claude-opus-4-7` (solutions). DeepSeek is optionally available via the Anthropic-compatible endpoint when the request carries `X-LLM-Provider: deepseek`.
- Math: KaTeX
- Exam PDF: local LaTeX engine (`tectonic`, `xelatex`, `lualatex`, or `pdflatex`)

## Architecture Rules

- Route files stay thin; business logic lives in `services/` and `core/`.
- PDF parsing, extraction, random selection, and exam generation are separate modules.
- Always persist parsed pages and extracted questions; never generate questions from a raw PDF at request time.
- LLM clients are built only through `app/core/llm_runtime.py`.
- LLM output must be JSON and pass validation/retry handling.
- The main extraction prompt lives in `app/prompts/extract_questions.txt`; smaller task prompts live next to their `core/` module.
- Preserve `raw_text` alongside `cleaned_text` on `ParsedPage`.
- Claude is used for extraction, outline detection, translation, and solutions — never for subject classification.
- Chapter tags come from local heading detection (`chapter_detector.py`) or, for full-PDF uploads, locally parsed contents pages (`chapter_outline_extractor.py`) with Claude fallback and local repair for skipped multiline entries.
- Subject is selected or created at upload time.
- Non-tectonic LaTeX engines must be invoked with `-no-shell-escape`.
- File uploads must be validated by magic bytes (`%PDF-`), not just `Content-Type`.

## Commands

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm run dev
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
cd frontend && npm run lint
cd frontend && npx tsc --noEmit
```

## API

Documents
- `POST /api/upload` — multipart: `file`, `document_role`, `subject`, `pdf_scope`
- `GET /api/documents` / `GET /api/documents/{id}` / `DELETE /api/documents/{id}`
- `GET /api/documents/{id}/chapters`
- `POST /api/documents/{id}/process` — parse PDF, persist pages/figures, detect chapters or full-PDF contents
- `POST /api/documents/{id}/extract` — extract questions from parsed pages (full PDFs require selected `chapter_ranges`)
- `POST /api/documents/{id}/reprocess`
- `DELETE /api/reset`

Questions
- `GET /api/questions` — filter by `subject`, `chapter`, `document_id`, `source_role`, `search`
- `GET /api/questions/{id}`
- `GET /api/questions/filter-options`
- `POST /api/questions/{id}/translate` — Korean translation, preserves LaTeX

Study set
- `POST /api/study-set/random`
- `POST /api/study-set/exam-pdf`
- `POST /api/study-set/solutions-pdf`

Header `X-LLM-Provider` (`claude` | `deepseek`) routes a single request through a different provider.

## Structure

```
backend/app/
  api/        upload.py, documents.py, extraction.py, questions.py, random_sets.py
  core/       pdf_parser, text_cleaner, candidate_detector, chapter_detector,
              chapter_outline_extractor, question_extractor, question_normalizer,
              question_translator, solution_generator, exam_generator,
              random_selector, llm_runtime
  services/   document_service, extraction_service, question_service
  models/     document, parsed_page, question, practice_session
  schemas/    document, question, random_set
  prompts/    extract_questions.txt
  db/         base.py, database.py
  config.py, main.py
backend/tests/
frontend/src/
  app/        layout.tsx, page.tsx, questions/page.tsx, study-set/page.tsx
  components/ FileUpload, DocumentList, QuestionCard, QuestionFilter,
              QuestionDetail, MathText, ModelSelector
  lib/        api.ts, types.ts
scripts/      full_project_check.py, workflow_smoke.py
```

## Data Models

- `Document` — uploaded PDF, subject, role, `pdf_scope`, status, `chapter_outline` (JSON)
- `ParsedPage` — `raw_text`, `cleaned_text`, `section_hint`, `figures` (JSON)
- `Question` — `question_text`, `normalized_question_text`, `chapter`, `tags`, `figure_refs`, `extracted_confidence`, source role
- `PracticeSession` — optional history of generated study sets

## Configuration

`backend/.env` (see `backend/.env.example`):

- `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`
- `CORS_ORIGINS` — comma-separated, e.g. `http://localhost:3000,https://your-frontend.vercel.app`
- `DATABASE_URL`, `UPLOAD_DIR`, `FIGURE_DIR`, `GENERATED_EXAM_DIR`
- `DEBUG` — must be `false` in production

## Hosting

Frontend deploys to Vercel. The backend cannot — it needs a long-lived process plus disk plus a LaTeX binary. Use Railway / Render / Fly.io / Docker host. See `README.md`.
