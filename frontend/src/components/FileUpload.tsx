"use client";

import { useState, useRef } from "react";
import { apiUpload } from "@/lib/api";
import { DocumentInfo, DocumentRole, PdfScope } from "@/lib/types";

interface FileUploadProps {
  role: DocumentRole;
  label: string;
  pdfScope: PdfScope;
  subjects: string[];
  onUploaded: (doc: DocumentInfo) => void;
}

export default function FileUpload({ role, label, pdfScope, subjects, onUploaded }: FileUploadProps) {
  const [subject, setSubject] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const datalistId = `${role}-subjects`;

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_role", role);
      formData.append("subject", subject);
      formData.append("pdf_scope", pdfScope);

      const doc = await apiUpload<DocumentInfo>("/api/upload", formData);
      onUploaded(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 p-6 dark:border-zinc-700">
      <h3 className="mb-3 text-lg font-semibold">{label}</h3>
      <div className="mb-4 flex flex-col gap-1">
        <label className="text-xs font-medium text-zinc-500">Subject</label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          list={datalistId}
          placeholder="Create or select a subject"
          className="rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-800"
        />
        <datalist id={datalistId}>
          {subjects.map((item) => (
            <option key={item} value={item} />
          ))}
        </datalist>
      </div>
      <p className="mb-4 rounded bg-zinc-50 px-3 py-2 text-xs text-zinc-500 dark:bg-zinc-800">
        {pdfScope === "full"
          ? "Full PDF: parse contents first, then select chapters."
          : "Chapter PDF: parse and extract questions directly."}
      </p>
      <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-300 bg-zinc-50 p-8 transition hover:border-blue-400 hover:bg-blue-50 dark:border-zinc-600 dark:bg-zinc-800 dark:hover:border-blue-500 dark:hover:bg-zinc-700">
        <span className="mb-2 text-sm text-zinc-500">
          {uploading ? "Uploading..." : "Click to select PDF"}
        </span>
        <span className="text-xs text-zinc-400">PDF only, max 50 MB</span>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleUpload}
          disabled={uploading}
        />
      </label>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
