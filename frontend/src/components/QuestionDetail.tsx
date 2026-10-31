"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useState } from "react";
import MathText from "@/components/MathText";
import { apiFetch, resolveApiAssetUrl } from "@/lib/api";
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

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

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

  const details: [string, string][] = [
    ["Source", question.source_role === "sample_exam" ? "Sample exam" : "Textbook"],
    ["Subject", question.subject ?? "–"],
    ["Chapter", question.chapter ?? "–"],
    ["Page", question.page_start != null ? String(question.page_start) : "–"],
    [
      "Confidence",
      question.extracted_confidence != null
        ? `${(question.extracted_confidence * 100).toFixed(0)}%`
        : "–",
    ],
  ];

  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className="modal-panel flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            {question.question_number && (
              <span className="kbd text-xs">#{question.question_number}</span>
            )}
            <button
              onClick={translate}
              disabled={translating}
              className="btn btn-secondary btn-sm"
            >
              {translating ? (
                <>
                  <span className="inline-flex gap-0.5" aria-hidden>
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="h-1 w-1 rounded-full bg-current"
                        style={{ animation: `pulse-dot 1.2s ease-in-out ${i * 0.16}s infinite` }}
                      />
                    ))}
                  </span>
                  번역 중
                </>
              ) : (
                "한국어로 번역"
              )}
            </button>
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-icon" aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden><path d="M4 4l8 8M12 4l-8 8" /></svg>
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
          <MathText
            text={question.question_text}
            className="block whitespace-pre-line text-[15px] leading-[1.75] tracking-[-0.008em]"
          />

          {translationError && <p className="text-[13px] text-danger">{translationError}</p>}

          {translatedText && (
            <div className="fade-in-up surface-muted p-4">
              <p className="text-eyebrow mb-2">Korean translation</p>
              <MathText
                text={translatedText}
                className="block whitespace-pre-line text-[14.5px] leading-[1.8] tracking-[-0.012em]"
              />
            </div>
          )}

          {figures.length > 0 && (
            <div className="grid gap-3">
              {figures.map((figure) => {
                const src = resolveApiAssetUrl(figure.url);
                return (
                  <figure key={figure.id} className="overflow-hidden rounded-xl border border-border">
                    <div className="flex min-h-40 w-full items-center justify-center bg-white p-3">
                      <img
                        src={src}
                        alt={figure.label ?? figure.id}
                        className="max-h-[28rem] max-w-full object-contain"
                        loading="lazy"
                      />
                    </div>
                    <figcaption className="border-t border-border px-3 py-2 text-xs text-muted-foreground">
                      {figure.caption || figure.label || figure.id}
                    </figcaption>
                  </figure>
                );
              })}
            </div>
          )}
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 border-t border-border bg-muted/50 px-6 py-4 text-[13px] sm:grid-cols-3">
          {details.map(([label, value]) => (
            <div key={label} className="min-w-0">
              <dt className="text-label">{label}</dt>
              <dd className="mt-0.5 truncate tabular-nums" title={value}>{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
