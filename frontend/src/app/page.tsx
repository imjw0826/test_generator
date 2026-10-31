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
    <div className="space-y-12">
      <div className="fade-in-up flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-xl">
          <p className="text-eyebrow mb-3">Step 1 · Upload</p>
          <h1 className="text-display">Upload documents</h1>
          <p className="text-lead mt-2">
            교재와 기출 PDF를 올리면 페이지 이미지를 그대로 읽어 수식까지 살린 문제를 추출합니다.
          </p>
        </div>
        <button
          onClick={handleResetAll}
          disabled={resetting || loading}
          className="btn btn-danger btn-sm"
        >
          {resetting ? "Resetting..." : "Reset all"}
        </button>
      </div>

      <div className="stagger grid gap-4 sm:grid-cols-2">
        <FileUpload
          role="textbook"
          label="Textbook"
          description="Full PDF · 목차를 먼저 읽고, 원하는 챕터만 골라 추출합니다."
          pdfScope="full"
          subjects={subjects}
          onUploaded={handleUploaded}
        />
        <FileUpload
          role="sample_exam"
          label="Sample exam"
          description="Chapter PDF · 바로 파싱하고 문제를 추출합니다."
          pdfScope="chapter"
          subjects={subjects}
          onUploaded={handleUploaded}
        />
      </div>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-title">Uploaded documents</h2>
          {!loading && documents.length > 0 && (
            <span className="text-label tabular-nums">{documents.length} files</span>
          )}
        </div>
        <DocumentList
          documents={documents}
          loading={loading}
          onDocumentUpdated={handleDocumentUpdated}
          onDocumentDeleted={handleDocumentDeleted}
        />
      </section>
    </div>
  );
}
