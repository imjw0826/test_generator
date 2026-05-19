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
    <div className="flex flex-wrap gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-zinc-500">Subject</label>
        <select
          value={filters.subject}
          onChange={(e) => update("subject", e.target.value)}
          className="rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
        >
          <option value="">All subjects</option>
          {subjects.map((subject) => (
            <option key={subject} value={subject}>{subject}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-zinc-500">Chapter</label>
        <select
          value={filters.chapter}
          onChange={(e) => update("chapter", e.target.value)}
          className="rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
        >
          <option value="">All chapters</option>
          {chapters.map((chapter) => (
            <option key={chapter} value={chapter}>{chapter}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-1 flex-col gap-1">
        <label className="text-xs font-medium text-zinc-500">Search within selected chapter</label>
        <input
          type="text"
          value={filters.search}
          onChange={(e) => update("search", e.target.value)}
          placeholder="Search question content..."
          className="min-w-[200px] rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-800"
        />
      </div>
    </div>
  );
}
