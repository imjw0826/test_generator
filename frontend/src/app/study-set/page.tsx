"use client";

import { useCallback, useEffect, useState } from "react";
import { apiDownload, apiFetch } from "@/lib/api";
import { QuestionFilterOptionsResponse, QuestionInfo } from "@/lib/types";
import QuestionCard from "@/components/QuestionCard";
import QuestionDetail from "@/components/QuestionDetail";
import TaskProgress, { useTaskProgress, ProgressStage } from "@/components/TaskProgress";

// ── Stage definitions ────────────────────────────────────────────────────────

const GENERATE_STAGES: ProgressStage[] = [
  { label: "문제 랜덤 선택 중...", durationMs: 600 },
];

const EXAM_PDF_STAGES: ProgressStage[] = [
  { label: "문제 선택 중...", durationMs: 400 },
  { label: "LaTeX 문서 생성 중...", durationMs: 800 },
  { label: "PDF 컴파일 중 (tectonic)...", durationMs: 5000 },
];

const SOLUTIONS_PDF_STAGES: ProgressStage[] = [
  { label: "문제 선택 중...", durationMs: 400 },
  { label: "Claude Opus로 풀이 생성 중...", durationMs: 45000 },
  { label: "LaTeX 문서 생성 중...", durationMs: 800 },
  { label: "PDF 컴파일 중 (tectonic)...", durationMs: 5000 },
];

interface StudySetResponse {
  questions: QuestionInfo[];
  total_available: number;
  total_selected: number;
}

export default function StudySetPage() {
  const [count, setCount] = useState(10);
  const [subject, setSubject] = useState("");
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [includeAnswers, setIncludeAnswers] = useState(false);
  const [excludeIds, setExcludeIds] = useState<number[]>([]);

  const [filterOptions, setFilterOptions] = useState<QuestionFilterOptionsResponse>({
    subjects: [],
    chapters: [],
    chapters_by_subject: {},
  });
  const [questions, setQuestions] = useState<QuestionInfo[]>([]);
  const [totalAvailable, setTotalAvailable] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadingSolutions, setDownloadingSolutions] = useState(false);
  const [selected, setSelected] = useState<QuestionInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generateProgress = useTaskProgress();
  const examProgress = useTaskProgress();
  const solutionsProgress = useTaskProgress();

  const availableChapters = subject
    ? filterOptions.chapters_by_subject[subject] ?? []
    : filterOptions.chapters;

  const fetchFilterOptions = useCallback(async () => {
    try {
      const data = await apiFetch<QuestionFilterOptionsResponse>("/api/questions/filter-options");
      setFilterOptions(data);
    } catch {
      console.error("Failed to fetch question filters");
    }
  }, []);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  async function generate() {
    setLoading(true);
    setError(null);
    generateProgress.start(GENERATE_STAGES);
    try {
      const body: Record<string, unknown> = { count };
      if (subject) body.subjects = [subject];
      if (selectedChapters.length > 0) body.chapters = selectedChapters;
      if (excludeIds.length > 0) body.exclude_question_ids = excludeIds;

      const data = await apiFetch<StudySetResponse>("/api/study-set/random", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setQuestions(data.questions);
      setTotalAvailable(data.total_available);
      setExcludeIds([]);
      generateProgress.finish();
    } catch (err) {
      generateProgress.cancel();
      setError(err instanceof Error ? err.message : "Failed to generate study set");
    } finally {
      setLoading(false);
    }
  }

  async function downloadExam() {
    setDownloading(true);
    setError(null);
    examProgress.start(EXAM_PDF_STAGES);
    try {
      const body: Record<string, unknown> = {
        count,
        include_answers: includeAnswers,
      };
      if (subject) body.subject = subject;
      if (selectedChapters.length > 0) body.chapters = selectedChapters;

      const { blob, filename } = await apiDownload("/api/study-set/exam-pdf", {
        method: "POST",
        body: JSON.stringify(body),
      });
      examProgress.finish();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      examProgress.cancel();
      setError(err instanceof Error ? err.message : "Failed to download exam PDF");
    } finally {
      setDownloading(false);
    }
  }

  async function downloadSolutions() {
    setDownloadingSolutions(true);
    setError(null);
    solutionsProgress.start(SOLUTIONS_PDF_STAGES);
    try {
      const body: Record<string, unknown> = { count };
      if (subject) body.subject = subject;
      if (selectedChapters.length > 0) body.chapters = selectedChapters;

      const { blob, filename } = await apiDownload("/api/study-set/solutions-pdf", {
        method: "POST",
        body: JSON.stringify(body),
      });
      solutionsProgress.finish();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      solutionsProgress.cancel();
      setError(err instanceof Error ? err.message : "Failed to download solutions PDF");
    } finally {
      setDownloadingSolutions(false);
    }
  }

  function toggleChapter(chapter: string) {
    setSelectedChapters((prev) =>
      prev.includes(chapter)
        ? prev.filter((item) => item !== chapter)
        : [...prev, chapter]
    );
  }

  function handleExclude(id: number) {
    setQuestions((prev) => prev.filter((q) => q.id !== id));
    setExcludeIds((prev) => [...prev, id]);
  }

  return (
    <div className="space-y-8">
      <div className="fade-in-up max-w-xl">
        <p className="text-eyebrow mb-3">Step 3 · Practice</p>
        <h1 className="text-display">Random study set</h1>
        <p className="text-lead mt-2">
          저장된 문제로 무작위 세트를 만들고 LaTeX 시험지 PDF로 내려받습니다. 풀이 PDF는 Claude Opus가 작성합니다.
          {totalAvailable != null && (
            <>
              {" "}
              <span className="tabular-nums text-foreground">{totalAvailable}</span>문제 중에서 고릅니다.
            </>
          )}
        </p>
      </div>

      <div className="surface p-5">
        <div className="grid gap-4 sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)_7rem]">
          <div className="flex min-w-0 flex-col gap-1.5">
            <label htmlFor="set-subject" className="text-label">Subject</label>
            <select
              id="set-subject"
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
                setSelectedChapters([]);
              }}
              className="field"
            >
              <option value="">All subjects</option>
              {filterOptions.subjects.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>

          <div className="flex min-w-0 flex-col gap-1.5">
            <span className="text-label">
              Chapters
              {selectedChapters.length > 0 && (
                <span className="ml-1.5 tabular-nums text-foreground">{selectedChapters.length} selected</span>
              )}
            </span>
            <div className="min-h-9 rounded-[0.625rem] bg-muted p-1.5">
              {!subject && (
                <p className="px-1.5 py-1 text-[13px] text-subtle-foreground">과목을 먼저 선택하면 여러 챕터를 고를 수 있습니다.</p>
              )}
              {subject && availableChapters.length === 0 && (
                <p className="px-1.5 py-1 text-[13px] text-subtle-foreground">No chapters available.</p>
              )}
              {subject && availableChapters.length > 0 && (
                <div className="max-h-36 space-y-0.5 overflow-y-auto">
                  {availableChapters.map((chapter) => (
                    <label
                      key={chapter}
                      className="flex cursor-pointer items-start gap-2.5 rounded-lg px-1.5 py-1.5 text-[13px] tracking-[-0.006em] transition-colors duration-150 hover:bg-card"
                    >
                      <input
                        type="checkbox"
                        checked={selectedChapters.includes(chapter)}
                        onChange={() => toggleChapter(chapter)}
                        className="checkbox mt-px"
                      />
                      <span>{chapter}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            {selectedChapters.length > 1 && (
              <p className="text-xs text-muted-foreground">
                선택한 {selectedChapters.length}개 챕터에서 고르게 출제합니다.
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="set-count" className="text-label">Problems</label>
            <input
              id="set-count"
              type="number"
              min={1}
              max={100}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="field tabular-nums"
            />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-4">
          <label className="flex cursor-pointer items-center gap-2.5 text-[13px]">
            <input
              type="checkbox"
              checked={includeAnswers}
              onChange={(e) => setIncludeAnswers(e.target.checked)}
              className="checkbox"
            />
            Include short answers
          </label>

          <div className="flex flex-wrap gap-2">
            <button onClick={generate} disabled={loading} className="btn btn-primary">
              {loading ? "Generating…" : "Generate"}
            </button>
            <button onClick={downloadExam} disabled={downloading} className="btn btn-outline">
              {downloading ? "Building PDF…" : "Exam PDF"}
            </button>
            <button onClick={downloadSolutions} disabled={downloadingSolutions} className="btn btn-outline">
              {downloadingSolutions ? "Writing solutions…" : "Solutions PDF"}
            </button>
          </div>
        </div>
        <TaskProgress state={generateProgress.state} />
        <TaskProgress state={examProgress.state} />
        <TaskProgress state={solutionsProgress.state} />
        {error && <p className="mt-3 text-[13px] text-danger">{error}</p>}
      </div>

      {questions.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-title">
              <span className="tabular-nums">{questions.length}</span> question{questions.length !== 1 ? "s" : ""}
            </h2>
            <button onClick={generate} disabled={loading} className="btn btn-secondary btn-sm">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2.5v2.75h-2.75" />
              </svg>
              Re-roll
            </button>
          </div>

          <div key={questions.map((q) => q.id).join("-")} className="stagger grid gap-3 sm:grid-cols-2">
            {questions.map((q) => (
              <div key={q.id} className="group relative">
                <QuestionCard question={q} onClick={setSelected} />
                <button
                  onClick={() => handleExclude(q.id)}
                  className="btn btn-ghost btn-icon absolute right-2 top-2 h-7 w-7 opacity-60 transition-opacity group-hover:opacity-100 hover:text-danger"
                  title="Remove from set"
                  aria-label="Remove from set"
                >
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden><path d="M4 4l8 8M12 4l-8 8" /></svg>
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {selected && (
        <QuestionDetail question={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
