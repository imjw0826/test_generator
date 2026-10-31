"use client";

import { useState, useRef } from "react";
import { apiUpload } from "@/lib/api";
import { DocumentInfo, DocumentRole, PdfScope } from "@/lib/types";

interface FileUploadProps {
  role: DocumentRole;
  label: string;
  description: string;
  pdfScope: PdfScope;
  subjects: string[];
  onUploaded: (doc: DocumentInfo) => void;
}

export default function FileUpload({ role, label, description, pdfScope, subjects, onUploaded }: FileUploadProps) {
  const [subject, setSubject] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const datalistId = `${role}-subjects`;
  const inputId = `${role}-subject-input`;

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
    <div className="surface flex flex-col gap-5 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-title">{label}</h3>
          <p className="mt-1 text-[13px] leading-5 text-muted-foreground">{description}</p>
        </div>
        <span className="badge shrink-0">{pdfScope === "full" ? "Full PDF" : "Chapter PDF"}</span>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={inputId} className="text-label">Subject</label>
        <input
          id={inputId}
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          list={datalistId}
          placeholder="과목을 입력하거나 선택하세요"
          className="field"
        />
        <datalist id={datalistId}>
          {subjects.map((item) => (
            <option key={item} value={item} />
          ))}
        </datalist>
      </div>

      <label
        className={`group flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--border-strong)] px-6 py-8 text-center transition-[background-color,border-color] duration-150 ease-out hover:border-foreground/40 hover:bg-accent ${
          uploading ? "pointer-events-none opacity-60" : ""
        }`}
      >
        <span className="grid h-9 w-9 place-items-center rounded-full bg-muted text-muted-foreground transition-transform duration-[250ms] ease-[var(--ease-smooth-out)] group-hover:-translate-y-0.5">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M8 10.5V2.5M4.75 5.75 8 2.5l3.25 3.25M2.5 10v1.75c0 .97.78 1.75 1.75 1.75h7.5c.97 0 1.75-.78 1.75-1.75V10" />
          </svg>
        </span>
        <span className="text-[13px] font-medium tracking-[-0.01em]">
          {uploading ? "Uploading…" : "Click to select a PDF"}
        </span>
        <span className="text-xs text-subtle-foreground">PDF only · max 50 MB</span>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleUpload}
          disabled={uploading}
        />
      </label>
      {error && <p className="text-[13px] text-danger">{error}</p>}
    </div>
  );
}
