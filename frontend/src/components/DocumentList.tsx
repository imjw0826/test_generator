"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { DocumentInfo } from "@/lib/types";

interface ExtractionProgress {
  active: boolean;
  current: number;
  total: number;
  percent: number;
}

const STATUS_STYLES: Record<string, string> = {
  uploaded: "text-amber-600 dark:text-amber-400",
  parsed: "text-sky-600 dark:text-sky-400",
  extracted: "text-emerald-600 dark:text-emerald-400",
  failed: "text-red-600 dark:text-red-400",
};

const ROLE_LABELS: Record<string, string> = {
  textbook: "Textbook",
  sample_exam: "Sample Exam",
};

interface DocumentListProps {
  documents: DocumentInfo[];
  loading: boolean;
  onDocumentUpdated: (doc: DocumentInfo) => void;
  onDocumentDeleted: (docId: number) => void;
}

export default function DocumentList({
  documents,
  loading,
  onDocumentUpdated,
  onDocumentDeleted,
}: DocumentListProps) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<Record<number, string[]>>({});
  const [outlineDoc, setOutlineDoc] = useState<DocumentInfo | null>(null);
  const [editingSubjectId, setEditingSubjectId] = useState<number | null>(null);
  const [editingSubjectValue, setEditingSubjectValue] = useState("");
  const [extractProgress, setExtractProgress] = useState<Record<number, ExtractionProgress>>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (busyId === null || busyAction !== "extract") {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }
    const docId = busyId;
    pollingRef.current = setInterval(async () => {
      try {
        const data = await apiFetch<ExtractionProgress>(`/api/documents/${docId}/progress`);
        if (data.active) {
          setExtractProgress((prev) => ({ ...prev, [docId]: data }));
        }
      } catch {
        // ignore polling errors
      }
    }, 1000);
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [busyId, busyAction]);

  async function handleAction(doc: DocumentInfo, action: "process" | "extract" | "reprocess") {
    const docId = doc.id;
    setBusyId(docId);
    setBusyAction(action);
    setActionError(null);
    try {
      const chapters = selectedChapters[docId] ?? [];
      const chapterRanges = sortedOutline(doc)
        .map((chapter, index) => ({ chapter, key: chapterKey(chapter, index) }))
        .filter((item) => chapters.includes(item.key))
        .map(({ chapter }) => ({
          title: chapter.title,
          start_page: chapter.start_page,
          end_page: chapter.end_page,
        }));
      const updated = await apiFetch<DocumentInfo>(`/api/documents/${docId}/${action}`, {
        method: "POST",
        body: action === "extract" && chapters.length > 0
          ? JSON.stringify({ chapter_ranges: chapterRanges })
          : undefined,
      });
      onDocumentUpdated(updated);
      if (updated.pdf_scope === "full" && (action === "process" || action === "reprocess")) {
        setOutlineDoc(updated);
      }
      if (action === "extract") {
        setOutlineDoc(null);
        setExtractProgress((prev) => {
          const next = { ...prev };
          delete next[docId];
          return next;
        });
      }
    } catch (err) {
      console.error(`${action} failed:`, err);
      setActionError(`${doc.original_name}: ${errorDetail(err)}`);
    } finally {
      setBusyId(null);
      setBusyAction(null);
    }
  }

  function startEditSubject(doc: DocumentInfo) {
    setEditingSubjectId(doc.id);
    setEditingSubjectValue(doc.subject);
  }

  function cancelEditSubject() {
    setEditingSubjectId(null);
    setEditingSubjectValue("");
  }

  async function saveSubject(doc: DocumentInfo) {
    const trimmed = editingSubjectValue.trim();
    if (!trimmed || trimmed === doc.subject) {
      cancelEditSubject();
      return;
    }
    try {
      const updated = await apiFetch<DocumentInfo>(`/api/documents/${doc.id}`, {
        method: "PATCH",
        body: JSON.stringify({ subject: trimmed }),
      });
      onDocumentUpdated(updated);
    } catch (err) {
      console.error("subject update failed:", err);
    } finally {
      cancelEditSubject();
    }
  }

  async function handleDelete(doc: DocumentInfo) {
    const confirmed = window.confirm(`Delete "${doc.original_name}" and its extracted questions?`);
    if (!confirmed) {
      return;
    }

    setBusyId(doc.id);
    setBusyAction("delete");
    try {
      await apiFetch<{ deleted: Record<string, number> }>(`/api/documents/${doc.id}`, {
        method: "DELETE",
      });
      onDocumentDeleted(doc.id);
    } catch (err) {
      console.error("delete failed:", err);
      setActionError(`${doc.original_name}: ${errorDetail(err)}`);
    } finally {
      setBusyId(null);
      setBusyAction(null);
    }
  }

  function toggleChapter(docId: number, key: string) {
    setSelectedChapters((prev) => {
      const current = prev[docId] ?? [];
      const next = current.includes(key)
        ? current.filter((item) => item !== key)
        : [...current, key];
      return { ...prev, [docId]: next };
    });
  }

  function chapterKey(chapter: { title: string; start_page: number; end_page: number }, index: number) {
    return `${chapter.title}::${chapter.start_page}-${chapter.end_page}::${index}`;
  }

  function sortedOutline(doc: DocumentInfo) {
    return [...(doc.chapter_outline ?? [])].sort((a, b) => {
      const aContentsPage = Number(a.page_label);
      const bContentsPage = Number(b.page_label);
      const aSortPage = Number.isFinite(aContentsPage) ? aContentsPage : a.start_page;
      const bSortPage = Number.isFinite(bContentsPage) ? bContentsPage : b.start_page;
      if (aSortPage !== bSortPage) {
        return aSortPage - bSortPage;
      }
      const aLevel = outlineLevel(a.title, a.level);
      const bLevel = outlineLevel(b.title, b.level);
      if (aLevel !== bLevel) {
        return aLevel - bLevel;
      }
      return a.title.localeCompare(b.title, undefined, { numeric: true });
    });
  }

  function treeIndent(level: number | undefined) {
    return Math.min(Math.max((level ?? 1) - 1, 0), 4) * 20;
  }

  function outlineLevel(title: string, level: number | undefined) {
    if (level) {
      return level;
    }
    const chapterMatch = title.match(/^\s*chapter\s+\d+\b/i);
    if (chapterMatch) {
      return 1;
    }
    const match = title.match(/^\s*(\d+(?:\.\d+)*)\b/);
    return match ? match[1].split(".").length : 1;
  }

  function formatDate(value: string) {
    const date = new Date(value);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
  }

  if (loading) {
    return (
      <div className="surface divide-y divide-[var(--border)]">
        {[0, 1].map((i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-4">
            <div className="h-3 w-40 animate-pulse rounded-full bg-muted" />
            <div className="h-3 w-20 animate-pulse rounded-full bg-muted" />
            <div className="ml-auto h-7 w-24 animate-pulse rounded-full bg-muted" />
          </div>
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="surface-muted px-6 py-12 text-center">
        <p className="text-[13px] font-medium">No documents yet</p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          위에서 PDF를 업로드하면 여기에 표시됩니다.
        </p>
      </div>
    );
  }

  return (
    <>
    {actionError && (
      <div className="fade-in-up mb-3 flex items-start justify-between gap-3 rounded-xl bg-[var(--danger-soft)] px-4 py-3 text-[13px] text-danger">
        <span>{actionError}</span>
        <button onClick={() => setActionError(null)} className="shrink-0 text-xs font-medium underline-offset-2 hover:underline">
          Dismiss
        </button>
      </div>
    )}
    <div className="surface overflow-x-auto">
      <table className="w-full min-w-[720px] whitespace-nowrap text-left text-[13px]">
        <thead>
          <tr className="border-b border-border">
            <th className="text-label px-5 py-3 font-medium">File</th>
            <th className="text-label px-3 py-3 font-medium">Subject</th>
            <th className="text-label px-3 py-3 font-medium">Role</th>
            <th className="text-label px-3 py-3 font-medium">Status</th>
            <th className="text-label px-3 py-3 text-right font-medium">Pages</th>
            <th className="text-label px-3 py-3 font-medium">Uploaded</th>
            <th className="text-label px-5 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {documents.map((doc) => {
            const isBusy = busyId === doc.id;
            const selectedForDoc = selectedChapters[doc.id] ?? [];
            const needsChapterSelection = doc.pdf_scope === "full" && selectedForDoc.length === 0;
            return (
              <tr key={doc.id} className="align-top transition-colors duration-150 hover:bg-accent">
                <td className="max-w-56 px-5 py-3.5 font-medium tracking-[-0.01em]">
                  <span className="block truncate" title={doc.original_name}>
                    {doc.original_name}
                  </span>
                </td>
                <td className="px-3 py-3.5">
                  {editingSubjectId === doc.id ? (
                    <input
                      autoFocus
                      type="text"
                      value={editingSubjectValue}
                      onChange={(e) => setEditingSubjectValue(e.target.value)}
                      onBlur={() => saveSubject(doc)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveSubject(doc);
                        if (e.key === "Escape") cancelEditSubject();
                      }}
                      className="field h-7 min-w-24 px-2 text-[13px]"
                    />
                  ) : (
                    <button
                      onClick={() => startEditSubject(doc)}
                      title="클릭하여 과목 수정"
                      className="group -mx-1.5 flex items-center gap-1 rounded-md px-1.5 py-0.5 transition-colors duration-150 hover:bg-accent-strong"
                    >
                      <span>{doc.subject}</span>
                      <svg
                        className="h-3 w-3 flex-shrink-0 text-subtle-foreground opacity-0 transition-opacity duration-150 group-hover:opacity-100"
                        viewBox="0 0 16 16" fill="currentColor"
                      >
                        <path d="M11.013 1.427a1.75 1.75 0 0 1 2.474 0l1.086 1.086a1.75 1.75 0 0 1 0 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 0 1-.927-.928l.929-3.25c.081-.286.235-.547.445-.758l8.61-8.61Zm.176 4.823L9.75 4.81l-6.286 6.287a.253.253 0 0 0-.064.108l-.558 1.953 1.953-.558a.253.253 0 0 0 .108-.064Zm1.238-3.763a.25.25 0 0 0-.354 0L10.811 3.75l1.439 1.44 1.263-1.263a.25.25 0 0 0 0-.354Z"/>
                      </svg>
                    </button>
                  )}
                </td>
                <td className="px-3 py-3.5">
                  <div>{ROLE_LABELS[doc.document_role]}</div>
                  <div className="text-xs text-subtle-foreground">
                    {doc.pdf_scope === "full" ? "Full PDF" : "Chapter PDF"}
                  </div>
                </td>
                <td className="px-3 py-3.5">
                  <span className={`badge badge-dot capitalize ${STATUS_STYLES[doc.status] || ""}`}>
                    {doc.status}
                  </span>
                </td>
                <td className="px-3 py-3.5 text-right tabular-nums">{doc.page_count ?? "–"}</td>
                <td className="px-3 py-3.5 tabular-nums text-muted-foreground">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-5 py-3">
                  <div className="flex flex-wrap gap-1.5">
                    {(doc.status === "uploaded" || doc.status === "failed") && (
                      <button
                        onClick={() => handleAction(doc, "process")}
                        disabled={isBusy}
                        className="btn btn-primary btn-sm"
                      >
                        {isBusy && busyAction === "process" ? "Parsing…" : "Parse"}
                      </button>
                    )}
                    {(doc.status === "parsed" || doc.status === "extracted") && (
                      <button
                        onClick={() => handleAction(doc, "extract")}
                        disabled={isBusy || needsChapterSelection}
                        title={needsChapterSelection ? "Select at least one chapter first" : undefined}
                        className="btn btn-primary btn-sm"
                      >
                        {isBusy && busyAction === "extract" ? "Extracting…" : "Extract"}
                      </button>
                    )}
                    {doc.pdf_scope === "full" && (doc.status === "parsed" || doc.status === "extracted") && (
                      <button
                        onClick={() => setOutlineDoc(doc)}
                        disabled={isBusy}
                        className="btn btn-outline btn-sm"
                      >
                        Contents
                      </button>
                    )}
                    {(doc.status === "parsed" || doc.status === "extracted" || doc.status === "failed") && (
                      <button
                        onClick={() => handleAction(doc, "reprocess")}
                        disabled={isBusy}
                        className="btn btn-secondary btn-sm"
                      >
                        {isBusy && busyAction === "reprocess" ? "Parsing…" : "Parse"}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(doc)}
                      disabled={isBusy}
                      className="btn btn-ghost btn-sm hover:text-danger"
                    >
                      {isBusy && busyAction === "delete" ? "Deleting…" : "Delete"}
                    </button>
                  </div>
                  {isBusy && busyAction === "extract" && (() => {
                    const prog = extractProgress[doc.id];
                    const percent = prog?.percent ?? 0;
                    const label = prog
                      ? `${prog.current} / ${prog.total} pages · ${percent}%`
                      : "Starting…";
                    return (
                      <div className="mt-2.5 space-y-1.5">
                        <div className="progress-track">
                          <div className="progress-fill" style={{ width: `${percent}%` }} />
                        </div>
                        <p className="text-xs tabular-nums text-muted-foreground">{label}</p>
                      </div>
                    );
                  })()}
                  {doc.pdf_scope === "full" && doc.status === "parsed" && (!doc.chapter_outline || doc.chapter_outline.length === 0) && (
                    <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                      No contents entries found. Check whether the PDF has a text-readable contents page.
                    </p>
                  )}
                  {doc.error_message && (
                    <p className="mt-1.5 max-w-xs truncate text-xs text-danger" title={doc.error_message}>
                      {doc.error_message}
                    </p>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    {outlineDoc && (
      <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setOutlineDoc(null)}>
        <div
          role="dialog"
          aria-modal="true"
          className="modal-panel flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
            <div className="min-w-0">
              <h3 className="text-title">Select chapters</h3>
              <p className="mt-1 truncate text-[13px] text-muted-foreground" title={outlineDoc.original_name}>
                {outlineDoc.original_name}
              </p>
            </div>
            <button
              onClick={() => setOutlineDoc(null)}
              className="btn btn-ghost btn-icon"
              aria-label="Close"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden><path d="M4 4l8 8M12 4l-8 8" /></svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            {outlineDoc.chapter_outline && outlineDoc.chapter_outline.length > 0 ? (
              <div className="space-y-1">
                {sortedOutline(outlineDoc).map((chapter, index) => {
                  const key = chapterKey(chapter, index);
                  const level = outlineLevel(chapter.title, chapter.level);
                  const checked = (selectedChapters[outlineDoc.id] ?? []).includes(key);
                  return (
                    <label
                      key={key}
                      className={`flex cursor-pointer items-start gap-3 rounded-xl px-3 py-2.5 transition-colors duration-150 ${
                        checked ? "bg-accent-strong" : "hover:bg-accent"
                      }`}
                      style={{ marginLeft: treeIndent(level) }}
                    >
                      <input
                        type="checkbox"
                        className="checkbox mt-0.5"
                        checked={checked}
                        onChange={() => toggleChapter(outlineDoc.id, key)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className={`block text-[13px] tracking-[-0.01em] ${level === 1 ? "font-semibold" : "font-medium"}`}>
                          {chapter.title}
                        </span>
                        <span className="text-xs tabular-nums text-muted-foreground">
                          PDF p.{chapter.start_page}–{chapter.end_page}
                          {chapter.page_label && ` · contents p.${chapter.page_label}`}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            ) : (
              <p className="rounded-xl bg-amber-500/10 p-4 text-[13px] text-amber-700 dark:text-amber-300">
                No contents entries were found. This usually means the PDF contents page is missing or not text-readable.
              </p>
            )}
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-border px-6 py-4">
            <span className="text-label tabular-nums">
              {(selectedChapters[outlineDoc.id] ?? []).length} selected
            </span>
            <div className="flex gap-2">
              <button onClick={() => setOutlineDoc(null)} className="btn btn-secondary">
                Close
              </button>
              <button
                onClick={() => handleAction(outlineDoc, "extract")}
                disabled={
                  busyId === outlineDoc.id ||
                  (selectedChapters[outlineDoc.id] ?? []).length === 0 ||
                  !outlineDoc.chapter_outline ||
                  outlineDoc.chapter_outline.length === 0
                }
                className="btn btn-primary"
              >
                {busyId === outlineDoc.id && busyAction === "extract" ? "Extracting…" : "Extract selected"}
              </button>
            </div>
          </div>
        </div>
      </div>
    )}
    </>
  );
}

function errorDetail(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  const body = message.replace(/^API error \d+:\s*/, "");
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed?.detail === "string") return parsed.detail;
  } catch {
    // not JSON
  }
  return body;
}
