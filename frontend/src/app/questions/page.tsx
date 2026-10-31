"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { QuestionFilterOptionsResponse, QuestionInfo, QuestionListResponse } from "@/lib/types";
import QuestionFilter, { QuestionFilters } from "@/components/QuestionFilter";
import QuestionCard from "@/components/QuestionCard";
import QuestionDetail from "@/components/QuestionDetail";

const DEFAULT_FILTERS: QuestionFilters = {
  subject: "",
  chapter: "",
  search: "",
};

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<QuestionInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<QuestionFilters>(DEFAULT_FILTERS);
  const [filterOptions, setFilterOptions] = useState<QuestionFilterOptionsResponse>({
    subjects: [],
    chapters: [],
    chapters_by_subject: {},
  });
  const [selected, setSelected] = useState<QuestionInfo | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 30;

  const fetchQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.subject) params.set("subject", filters.subject);
      if (filters.chapter) params.set("chapter", filters.chapter);
      if (filters.search) params.set("search", filters.search);
      params.set("limit", String(limit));
      params.set("offset", String(offset));

      const data = await apiFetch<QuestionListResponse>(`/api/questions?${params}`);
      setQuestions(data.questions);
      setTotal(data.total);
    } catch {
      console.error("Failed to fetch questions");
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

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
    fetchQuestions();
  }, [fetchFilterOptions, fetchQuestions]);

  function handleFiltersChange(newFilters: QuestionFilters) {
    setFilters((current) => ({
      ...newFilters,
      chapter: current.subject !== newFilters.subject ? "" : newFilters.chapter,
    }));
    setOffset(0);
  }

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;
  const chapters = filters.subject
    ? filterOptions.chapters_by_subject[filters.subject] ?? []
    : filterOptions.chapters;

  return (
    <div className="space-y-8">
      <div className="fade-in-up max-w-xl">
        <p className="text-eyebrow mb-3">Step 2 · Browse</p>
        <h1 className="text-display">Question bank</h1>
        <p className="text-lead mt-2">
          추출된 문제를 과목과 챕터별로 찾아보세요.{" "}
          <span className="tabular-nums text-foreground">{total}</span>개의 문제가 있습니다.
        </p>
      </div>

      <QuestionFilter
        filters={filters}
        subjects={filterOptions.subjects}
        chapters={chapters}
        onChange={handleFiltersChange}
      />

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="surface space-y-3 p-4">
              <div className="h-4 w-24 animate-pulse rounded-full bg-muted" />
              <div className="h-3 w-full animate-pulse rounded-full bg-muted" />
              <div className="h-3 w-2/3 animate-pulse rounded-full bg-muted" />
            </div>
          ))}
        </div>
      ) : questions.length === 0 ? (
        <div className="surface-muted px-6 py-12 text-center">
          <p className="text-[13px] font-medium">No questions found</p>
          <p className="mt-1 text-[13px] text-muted-foreground">
            교재 PDF를 업로드하고 문제를 추출하면 여기에 표시됩니다.
          </p>
        </div>
      ) : (
        <>
          <div key={`${offset}-${filters.subject}-${filters.chapter}`} className="stagger grid gap-3 sm:grid-cols-2">
            {questions.map((q) => (
              <QuestionCard
                key={q.id}
                question={q}
                onClick={setSelected}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="btn btn-outline btn-sm"
              >
                Previous
              </button>
              <span className="text-label tabular-nums">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={currentPage >= totalPages}
                className="btn btn-outline btn-sm"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {selected && (
        <QuestionDetail question={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
