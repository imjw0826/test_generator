"use client";

import { useCallback, useEffect, useState } from "react";
import { apiDownload, apiFetch } from "@/lib/api";
import { QuestionFilterOptionsResponse, QuestionInfo } from "@/lib/types";
import QuestionCard from "@/components/QuestionCard";
import QuestionDetail from "@/components/QuestionDetail";

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
    try {
      const body: Record<string, unknown> = {
        count,
      };
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate study set");
      console.error("Failed to generate study set:", err);
    } finally {
      setLoading(false);
    }
  }

  async function downloadExam() {
    setDownloading(true);
    setError(null);
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
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download exam PDF");
      console.error("Failed to download exam PDF:", err);
    } finally {
      setDownloading(false);
    }
  }

  async function downloadSolutions() {
    setDownloadingSolutions(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { count };
      if (subject) body.subject = subject;
      if (selectedChapters.length > 0) body.chapters = selectedChapters;

      const { blob, filename } = await apiDownload("/api/study-set/solutions-pdf", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download solutions PDF");
      console.error("Failed to download solutions PDF:", err);
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Random Study Set</h1>
        <p className="mt-1 text-zinc-500">
          Generate a local LaTeX exam PDF from stored questions. The solutions PDF uses Opus for explanations.
          {totalAvailable != null && ` ${totalAvailable} questions available.`}
        </p>
      </div>

      <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
        <div className="flex flex-wrap gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-zinc-500">Subject</label>
            <select
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
                setSelectedChapters([]);
              }}
              className="min-w-44 rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
            >
              <option value="">All subjects</option>
              {filterOptions.subjects.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-zinc-500">Chapter</label>
            <div className="min-w-64 rounded border border-zinc-300 bg-white p-2 text-sm dark:border-zinc-600 dark:bg-zinc-800">
              {!subject && (
                <p className="text-xs text-zinc-500">Select one subject before choosing multiple chapters.</p>
              )}
              {subject && availableChapters.length === 0 && (
                <p className="text-xs text-zinc-500">No chapters available.</p>
              )}
              {subject && availableChapters.length > 0 && (
                <div className="max-h-32 space-y-1 overflow-y-auto">
                  {availableChapters.map((chapter) => (
                    <label key={chapter} className="flex items-start gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={selectedChapters.includes(chapter)}
                        onChange={() => toggleChapter(chapter)}
                        className="mt-0.5"
                      />
                      <span>{chapter}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            {selectedChapters.length > 1 && (
              <p className="text-xs text-zinc-500">
                Problems are balanced across {selectedChapters.length} selected chapters.
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-zinc-500">Number of Problems</label>
            <input
              type="number"
              min={1}
              max={100}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-20 rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
            />
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeAnswers}
              onChange={(e) => setIncludeAnswers(e.target.checked)}
            />
            Include short answers under each problem
          </label>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={generate}
              disabled={loading}
              className="rounded bg-blue-500 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate"}
            </button>
            <button
              onClick={downloadExam}
              disabled={downloading}
              className="rounded bg-zinc-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
            >
              {downloading ? "Building PDF..." : "Download PDF"}
            </button>
            <button
              onClick={downloadSolutions}
              disabled={downloadingSolutions}
              className="rounded bg-amber-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-amber-700 disabled:opacity-50"
            >
              {downloadingSolutions ? "Writing Solutions..." : "Download Solutions PDF"}
            </button>
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
      </div>

      {questions.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {questions.length} Question{questions.length !== 1 ? "s" : ""}
            </h2>
            <button
              onClick={generate}
              disabled={loading}
              className="rounded border border-zinc-300 px-3 py-1 text-sm transition hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-800"
            >
              Re-roll
            </button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {questions.map((q) => (
              <div key={q.id} className="relative">
                <QuestionCard question={q} onClick={setSelected} />
                <button
                  onClick={() => handleExclude(q.id)}
                  className="absolute right-2 top-2 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-600 hover:bg-red-200"
                  title="Remove from set"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {selected && (
        <QuestionDetail question={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
