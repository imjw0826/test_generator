"use client";

import { useState } from "react";
import { PDF_INSPECTOR_STORAGE_KEY, getPdfInspectorEnabled } from "@/lib/api";

export default function PdfInspectorToggle() {
  const [enabled, setEnabled] = useState<boolean>(() => getPdfInspectorEnabled());

  function updateEnabled(nextEnabled: boolean) {
    setEnabled(nextEnabled);
    localStorage.setItem(PDF_INSPECTOR_STORAGE_KEY, nextEnabled ? "on" : "off");
  }

  return (
    <label
      className="flex items-center gap-2 text-xs text-zinc-500"
      title="Use pdf-inspector layout analysis (font-based chapter headings) when parsing PDFs"
    >
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => updateEnabled(e.target.checked)}
        className="h-3.5 w-3.5 accent-zinc-700 dark:accent-zinc-300"
      />
      pdf-inspector
    </label>
  );
}
