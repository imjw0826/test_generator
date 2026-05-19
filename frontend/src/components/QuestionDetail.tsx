"use client";

import Image from "next/image";
import { useState } from "react";
import MathText from "@/components/MathText";
import { API_BASE, apiFetch } from "@/lib/api";
import { QuestionInfo, QuestionTranslationResponse } from "@/lib/types";

interface QuestionDetailProps {
  question: QuestionInfo;
  onClose: () => void;
}

export default function QuestionDetail({ question, onClose }: QuestionDetailProps) {
  const figures = question.figure_refs ?? [];
  const [translatedText, setTranslatedText] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);

  async function translate() {
    setTranslating(true);
    setTranslationError(null);
    try {
      const data = await apiFetch<QuestionTranslationResponse>(`/api/questions/${question.id}/translate`, {
        method: "POST",
      });
      setTranslatedText(data.translated_text);
    } catch (err) {
      setTranslationError(err instanceof Error ? err.message : "Translation failed");
    } finally {
      setTranslating(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <div className="flex items-center gap-2">
            {question.question_number && (
              <span className="rounded bg-zinc-100 px-2 py-1 text-sm font-mono font-bold dark:bg-zinc-700">
                #{question.question_number}
              </span>
            )}
            <button
              onClick={translate}
              disabled={translating}
              className="rounded bg-blue-500 px-3 py-1 text-xs font-medium text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {translating ? "Translating..." : "Translate to Korean"}
            </button>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-700"
          >
            &times;
          </button>
        </div>

        <MathText text={question.question_text} className="mb-4 block whitespace-pre-line text-sm leading-relaxed" />

        {translationError && <p className="mb-4 text-sm text-red-500">{translationError}</p>}

        {translatedText && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-950/30">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-blue-600 dark:text-blue-300">
              Korean Translation
            </p>
            <MathText text={translatedText} className="block whitespace-pre-line text-sm leading-relaxed" />
          </div>
        )}

        {figures.length > 0 && (
          <div className="mb-4 grid gap-3">
            {figures.map((figure) => {
              const src = figure.url.startsWith("http") ? figure.url : `${API_BASE}${figure.url}`;
              return (
                <figure key={figure.id} className="overflow-hidden rounded border border-zinc-200 dark:border-zinc-700">
                  <div className="relative h-96 w-full bg-white">
                    <Image
                      src={src}
                      alt={figure.label ?? figure.id}
                      fill
                      sizes="(max-width: 768px) 90vw, 672px"
                      className="object-contain"
                    />
                  </div>
                  <figcaption className="border-t border-zinc-200 px-3 py-2 text-xs text-zinc-500 dark:border-zinc-700">
                    {figure.caption || figure.label || figure.id}
                  </figcaption>
                </figure>
              );
            })}
          </div>
        )}

        <div className="space-y-2 border-t border-zinc-200 pt-4 text-sm dark:border-zinc-700">
          <div className="grid grid-cols-2 gap-2 text-zinc-500">
            <div>Source: <span className="text-zinc-800 dark:text-zinc-200">{question.source_role}</span></div>
            <div>Subject: <span className="text-zinc-800 dark:text-zinc-200">{question.subject ?? "-"}</span></div>
            <div>Page: <span className="text-zinc-800 dark:text-zinc-200">{question.page_start ?? "-"}</span></div>
            <div>Chapter: <span className="text-zinc-800 dark:text-zinc-200">{question.chapter ?? "-"}</span></div>
            <div>
              Confidence:{" "}
              <span className="text-zinc-800 dark:text-zinc-200">
                {question.extracted_confidence != null
                  ? `${(question.extracted_confidence * 100).toFixed(0)}%`
                : "-"}
              </span>
            </div>
          </div>

          {question.tags && question.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-2">
              {question.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
