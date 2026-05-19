"use client";

import { useState } from "react";
import {
  LLM_PROVIDER_STORAGE_KEY,
  LlmProvider,
  getSelectedLlmProvider,
} from "@/lib/api";

const MODEL_OPTIONS = [
  { id: "claude", label: "Claude" },
  { id: "deepseek", label: "DeepSeek" },
];

export default function ModelSelector() {
  const [provider, setProvider] = useState<LlmProvider>(() => getSelectedLlmProvider());

  function updateProvider(nextProvider: LlmProvider) {
    setProvider(nextProvider);
    localStorage.setItem(LLM_PROVIDER_STORAGE_KEY, nextProvider);
  }

  return (
    <label className="ml-auto flex items-center gap-2 text-xs text-zinc-500">
      API
      <select
        value={provider}
        onChange={(e) => updateProvider(e.target.value as LlmProvider)}
        className="rounded border border-zinc-300 bg-white px-2 py-1 text-xs text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
      >
        {MODEL_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
