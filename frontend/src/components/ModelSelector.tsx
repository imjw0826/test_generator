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
    <label className="ml-auto flex shrink-0 items-center gap-2">
      <span className="text-label hidden sm:inline">Model</span>
      <select
        value={provider}
        onChange={(e) => updateProvider(e.target.value as LlmProvider)}
        className="field h-8 w-auto rounded-full text-xs font-medium"
        aria-label="LLM provider"
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
