"use client";

import { useCallback, useEffect, useState } from "react";
import FileUpload from "@/components/FileUpload";
import DocumentList from "@/components/DocumentList";
import { apiFetch } from "@/lib/api";
import { DocumentInfo, DocumentListResponse } from "@/lib/types";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const subjects = Array.from(new Set(documents.map((doc) => doc.subject).filter(Boolean))).sort();

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await apiFetch<DocumentListResponse>("/api/documents");
      setDocuments(data.documents);
    } catch {
      console.error("Failed to fetch documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  function handleUploaded(doc: DocumentInfo) {
    setDocuments((prev) => [doc, ...prev]);
  }

  function handleDocumentUpdated(doc: DocumentInfo) {
    setDocuments((prev) => prev.map((d) => (d.id === doc.id ? doc : d)));
  }

  function handleDocumentDeleted(docId: number) {
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
  }

  async function handleResetAll() {
    const confirmed = window.confirm("Delete all uploaded documents and extracted questions?");
    if (!confirmed) {
      return;
    }

    setResetting(true);
    try {
      await apiFetch<{ reset: boolean }>("/api/reset", {
        method: "DELETE",
      });
      setDocuments([]);
    } catch (err) {
      console.error("Failed to reset data:", err);
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Upload Documents</h1>
          <p className="mt-1 text-zinc-500">
            Upload textbook PDFs and sample exam PDFs to extract questions.
          </p>
        </div>
        <button
          onClick={handleResetAll}
          disabled={resetting || loading}
          className="rounded border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/30"
        >
          {resetting ? "Resetting..." : "Reset All"}
        </button>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <FileUpload
          role="textbook"
          label="Textbook Full PDF"
          pdfScope="full"
          subjects={subjects}
          onUploaded={handleUploaded}
        />
        <FileUpload
          role="sample_exam"
          label="Sample Exam Chapter PDF"
          pdfScope="chapter"
          subjects={subjects}
          onUploaded={handleUploaded}
        />
      </div>

      <div>
        <h2 className="mb-4 text-xl font-semibold">Uploaded Documents</h2>
        <DocumentList
          documents={documents}
          loading={loading}
          onDocumentUpdated={handleDocumentUpdated}
          onDocumentDeleted={handleDocumentDeleted}
        />
      </div>
    </div>
  );
}
