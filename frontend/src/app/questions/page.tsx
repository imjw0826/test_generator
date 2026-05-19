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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Question Bank</h1>
        <p className="mt-1 text-zinc-500">
          Browse and filter extracted questions. {total} question{total !== 1 ? "s" : ""} found.
        </p>
      </div>

      <QuestionFilter
        filters={filters}
        subjects={filterOptions.subjects}
        chapters={chapters}
        onChange={handleFiltersChange}
      />

      {loading ? (
        <p className="py-8 text-center text-zinc-400">Loading questions...</p>
      ) : questions.length === 0 ? (
        <p className="py-8 text-center text-zinc-400">
          No questions found. Upload and extract a textbook PDF first.
        </p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            {questions.map((q) => (
              <QuestionCard
                key={q.id}
                question={q}
                onClick={setSelected}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 pt-4">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="rounded border border-zinc-300 px-3 py-1 text-sm disabled:opacity-30 dark:border-zinc-600"
              >
                Previous
              </button>
              <span className="text-sm text-zinc-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={currentPage >= totalPages}
                className="rounded border border-zinc-300 px-3 py-1 text-sm disabled:opacity-30 dark:border-zinc-600"
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
