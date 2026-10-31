"use client";

import MathText from "@/components/MathText";
import { QuestionInfo } from "@/lib/types";

interface QuestionCardProps {
  question: QuestionInfo;
  onClick: (q: QuestionInfo) => void;
}

export default function QuestionCard({ question, onClick }: QuestionCardProps) {
  const meta = [
    question.subject,
    question.page_start ? `p.${question.page_start}` : null,
  ].filter(Boolean);

  return (
    <button
      type="button"
      onClick={() => onClick(question)}
      className="surface card-interactive flex h-full w-full flex-col gap-3 p-4 text-left"
    >
      <div className="flex min-h-[1.375rem] items-center gap-2 pr-6">
        {question.question_number && (
          <span className="kbd">#{question.question_number}</span>
        )}
        {question.chapter && (
          <span className="truncate text-xs text-muted-foreground" title={question.chapter}>
            {question.chapter}
          </span>
        )}
      </div>

      <MathText
        text={question.question_text}
        className="line-clamp-3 text-[13.5px] leading-[1.65] tracking-[-0.006em] text-foreground"
      />

      {meta.length > 0 && (
        <div className="mt-auto flex items-center gap-1.5 pt-1 text-xs text-subtle-foreground">
          {meta.map((item, index) => (
            <span key={item} className="flex items-center gap-1.5">
              {index > 0 && <span aria-hidden>·</span>}
              <span className="tabular-nums">{item}</span>
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
