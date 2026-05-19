"use client";

import MathText from "@/components/MathText";
import { QuestionInfo } from "@/lib/types";

interface QuestionCardProps {
  question: QuestionInfo;
  onClick: (q: QuestionInfo) => void;
}

export default function QuestionCard({ question, onClick }: QuestionCardProps) {
  return (
    <div
      onClick={() => onClick(question)}
      className="cursor-pointer rounded-lg border border-zinc-200 p-4 transition hover:border-blue-300 hover:shadow-sm dark:border-zinc-700 dark:hover:border-blue-600"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {question.question_number && (
            <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs font-mono font-medium dark:bg-zinc-800">
              #{question.question_number}
            </span>
          )}
        </div>
      </div>

      <MathText text={question.question_text} className="line-clamp-3 text-sm leading-relaxed" />

      {question.tags && question.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {question.tags.map((tag) => (
            <span
              key={tag}
              className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-2 text-xs text-zinc-400">
        {question.subject && <span>{question.subject}</span>}
        {question.chapter && <span> &middot; {question.chapter}</span>}
        {question.page_start && <span> &middot; Page {question.page_start}</span>}
      </div>
    </div>
  );
}
