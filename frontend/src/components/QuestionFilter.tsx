"use client";

export interface QuestionFilters {
  subject: string;
  chapter: string;
  search: string;
}

interface QuestionFilterProps {
  filters: QuestionFilters;
  subjects: string[];
  chapters: string[];
  onChange: (filters: QuestionFilters) => void;
}

export default function QuestionFilter({ filters, subjects, chapters, onChange }: QuestionFilterProps) {
  function update(key: keyof QuestionFilters, value: string) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="surface grid gap-3 p-4 sm:grid-cols-[minmax(0,10rem)_minmax(0,16rem)_minmax(0,1fr)]">
      <div className="flex min-w-0 flex-col gap-1.5">
        <label htmlFor="filter-subject" className="text-label">Subject</label>
        <select
          id="filter-subject"
          value={filters.subject}
          onChange={(e) => update("subject", e.target.value)}
          className="field"
        >
          <option value="">All subjects</option>
          {subjects.map((subject) => (
            <option key={subject} value={subject}>{subject}</option>
          ))}
        </select>
      </div>

      <div className="flex min-w-0 flex-col gap-1.5">
        <label htmlFor="filter-chapter" className="text-label">Chapter</label>
        <select
          id="filter-chapter"
          value={filters.chapter}
          onChange={(e) => update("chapter", e.target.value)}
          className="field truncate"
        >
          <option value="">All chapters</option>
          {chapters.map((chapter) => (
            <option key={chapter} value={chapter}>{chapter}</option>
          ))}
        </select>
      </div>

      <div className="flex min-w-0 flex-col gap-1.5">
        <label htmlFor="filter-search" className="text-label">Search</label>
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle-foreground"
            viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden
          >
            <circle cx="7" cy="7" r="4.5" />
            <path d="m10.5 10.5 3 3" />
          </svg>
          <input
            id="filter-search"
            type="text"
            value={filters.search}
            onChange={(e) => update("search", e.target.value)}
            placeholder="문제 내용으로 검색"
            className="field pl-8"
          />
        </div>
      </div>
    </div>
  );
}
