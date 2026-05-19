# Frontend

Next.js App Router frontend for Study Question Generator.

## Runtime Flow

- `/` uploads documents, parses PDFs, shows full-PDF contents selection, and triggers extraction.
- `/questions` browses stored questions by subject, chapter, and text search.
- `/study-set` creates random study sets and downloads generated PDFs from stored questions.
- API calls go through `src/lib/api.ts`; the frontend never reads LLM API keys.
- The selected provider is sent as `X-LLM-Provider` and defaults to `claude`.

## Commands

```bash
npm run dev
npm run lint
npx tsc --noEmit
```

The frontend talks to the backend through `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.
