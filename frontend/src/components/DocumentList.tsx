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

const STATUS_COLORS: Record<string, string> = {
  uploaded: "bg-yellow-100 text-yellow-800",
  parsed: "bg-blue-100 text-blue-800",
  extracted: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
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
    return Math.min(Math.max((level ?? 1) - 1, 0), 4) * 24;
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
    return <p className="py-8 text-center text-zinc-400">Loading documents...</p>;
  }

  if (documents.length === 0) {
    return (
      <p className="py-8 text-center text-zinc-400">
        No documents uploaded yet. Upload a PDF above to get started.
      </p>
    );
  }

  return (
    <>
    {actionError && (
      <div className="mb-3 flex items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        <span>{actionError}</span>
        <button onClick={() => setActionError(null)} className="text-xs underline">
          Dismiss
        </button>
      </div>
    )}
    <div className="overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-700">
      <table className="w-full text-left text-sm">
        <thead className="bg-zinc-50 dark:bg-zinc-800">
          <tr>
            <th className="px-4 py-3 font-medium">File</th>
            <th className="px-4 py-3 font-medium">Subject</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Pages</th>
            <th className="px-4 py-3 font-medium">Uploaded</th>
            <th className="px-4 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-700">
          {documents.map((doc) => {
            const isBusy = busyId === doc.id;
            const selectedForDoc = selectedChapters[doc.id] ?? [];
            const needsChapterSelection = doc.pdf_scope === "full" && selectedForDoc.length === 0;
            return (
              <tr key={doc.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                <td className="max-w-56 px-4 py-3 font-medium">
                  <span className="block truncate" title={doc.original_name}>
                    {doc.original_name}
                  </span>
                </td>
                <td className="px-4 py-3">
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
                      className="w-full min-w-24 rounded border border-blue-400 px-2 py-0.5 text-sm outline-none focus:ring-1 focus:ring-blue-400 dark:bg-zinc-800"
                    />
                  ) : (
                    <button
                      onClick={() => startEditSubject(doc)}
                      title="클릭하여 과목 수정"
                      className="group flex items-center gap-1 rounded px-1 -mx-1 hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition"
                    >
                      <span>{doc.subject}</span>
                      <svg
                        className="h-3 w-3 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                        viewBox="0 0 16 16" fill="currentColor"
                      >
                        <path d="M11.013 1.427a1.75 1.75 0 0 1 2.474 0l1.086 1.086a1.75 1.75 0 0 1 0 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 0 1-.927-.928l.929-3.25c.081-.286.235-.547.445-.758l8.61-8.61Zm.176 4.823L9.75 4.81l-6.286 6.287a.253.253 0 0 0-.064.108l-.558 1.953 1.953-.558a.253.253 0 0 0 .108-.064Zm1.238-3.763a.25.25 0 0 0-.354 0L10.811 3.75l1.439 1.44 1.263-1.263a.25.25 0 0 0 0-.354Z"/>
                      </svg>
                    </button>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div>{ROLE_LABELS[doc.document_role]}</div>
                  <div className="text-xs text-zinc-500">
                    {doc.pdf_scope === "full" ? "Full PDF" : "Chapter PDF"}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[doc.status] || ""}`}
                  >
                    {doc.status}
                  </span>
                </td>
                <td className="px-4 py-3">{doc.page_count ?? "-"}</td>
                <td className="px-4 py-3 text-zinc-500">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {(doc.status === "uploaded" || doc.status === "failed") && (
                      <button
                        onClick={() => handleAction(doc, "process")}
                        disabled={isBusy}
                        className="rounded bg-blue-500 px-3 py-1 text-xs font-medium text-white transition hover:bg-blue-600 disabled:opacity-50"
                      >
                        {isBusy && busyAction === "process" ? "Parsing..." : "Parse"}
                      </button>
                    )}
                    {(doc.status === "parsed" || doc.status === "extracted") && (
                      <button
                        onClick={() => handleAction(doc, "extract")}
                        disabled={isBusy || needsChapterSelection}
                        title={needsChapterSelection ? "Select at least one chapter first" : undefined}
                        className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
                      >
                        {isBusy && busyAction === "extract" ? "Extracting..." : "Extract"}
                      </button>
                    )}
                    {doc.pdf_scope === "full" && (doc.status === "parsed" || doc.status === "extracted") && (
                      <button
                        onClick={() => setOutlineDoc(doc)}
                        disabled={isBusy}
                        className="rounded border border-blue-300 px-3 py-1 text-xs font-medium text-blue-600 transition hover:bg-blue-50 disabled:opacity-50 dark:border-blue-800 dark:text-blue-400 dark:hover:bg-blue-950/30"
                      >
                        Contents
                      </button>
                    )}
                    {(doc.status === "parsed" || doc.status === "extracted" || doc.status === "failed") && (
                      <button
                        onClick={() => handleAction(doc, "reprocess")}
                        disabled={isBusy}
                        className="rounded border border-zinc-300 px-3 py-1 text-xs font-medium transition hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-600 dark:hover:bg-zinc-800"
                      >
                        {isBusy && busyAction === "reprocess" ? "Parsing..." : "Parse"}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(doc)}
                      disabled={isBusy}
                      className="rounded border border-red-300 px-3 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/30"
                    >
                      {isBusy && busyAction === "delete" ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                  {isBusy && busyAction === "extract" && (() => {
                    const prog = extractProgress[doc.id];
                    const percent = prog?.percent ?? 0;
                    const label = prog
                      ? `${prog.current} / ${prog.total} pages (${percent}%)`
                      : "Starting...";
                    return (
                      <div className="mt-2 space-y-1">
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
                          <div
                            className="h-full rounded-full bg-green-500 transition-all duration-500"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                        <p className="text-xs text-zinc-500">{label}</p>
                      </div>
                    );
                  })()}
                  {doc.pdf_scope === "full" && doc.status === "parsed" && (!doc.chapter_outline || doc.chapter_outline.length === 0) && (
                    <p className="mt-2 text-xs text-amber-600">
                      No contents entries found. Check whether the PDF has a text-readable contents page.
                    </p>
                  )}
                  {doc.error_message && (
                    <p className="mt-1 text-xs text-red-500 max-w-xs truncate" title={doc.error_message}>
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
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setOutlineDoc(null)}>
        <div
          className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-800"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold">Select Chapters from Contents</h3>
              <p className="mt-1 max-w-xl truncate text-sm text-zinc-500" title={outlineDoc.original_name}>
                {outlineDoc.original_name}
              </p>
            </div>
            <button
              onClick={() => setOutlineDoc(null)}
              className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-700"
            >
              &times;
            </button>
          </div>

          {outlineDoc.chapter_outline && outlineDoc.chapter_outline.length > 0 ? (
            <div className="space-y-2">
              {sortedOutline(outlineDoc).map((chapter, index) => {
                const key = chapterKey(chapter, index);
                const level = outlineLevel(chapter.title, chapter.level);
                return (
                  <label
                    key={key}
                    className="flex items-start gap-3 rounded border border-zinc-200 p-3 text-sm dark:border-zinc-700"
                    style={{ marginLeft: treeIndent(level) }}
                  >
                    <span className="mt-1 flex items-center gap-2">
                      {level > 1 && <span className="h-px w-4 bg-zinc-300 dark:bg-zinc-600" />}
                      <input
                        type="checkbox"
                        checked={(selectedChapters[outlineDoc.id] ?? []).includes(key)}
                        onChange={() => toggleChapter(outlineDoc.id, key)}
                      />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={`block ${level === 1 ? "font-semibold" : "font-medium"}`}>
                        {chapter.title}
                      </span>
                      <span className="text-xs text-zinc-500">
                        PDF pages {chapter.start_page}-{chapter.end_page}
                        {chapter.page_label && ` | contents page ${chapter.page_label}`}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          ) : (
            <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">
              No contents entries were found. This usually means the PDF contents page is missing or not text-readable.
            </p>
          )}

          <div className="mt-5 flex justify-end gap-3">
            <button
              onClick={() => setOutlineDoc(null)}
              className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium transition hover:bg-zinc-50 dark:border-zinc-600 dark:hover:bg-zinc-700"
            >
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
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
            >
              {busyId === outlineDoc.id && busyAction === "extract" ? "Extracting..." : "Extract Selected Chapters"}
            </button>
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
