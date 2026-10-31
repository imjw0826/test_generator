"use client";

import { useEffect, useRef, useState } from "react";

export interface ProgressStage {
  label: string;
  /** Estimated wall-clock duration for this stage in milliseconds. */
  durationMs: number;
}

interface TaskProgressState {
  running: boolean;
  /** 0–100 */
  percent: number;
  stageIndex: number;
  stages: ProgressStage[];
}

const TICK_MS = 80;
/** Never auto-advance past this threshold — wait for the real response. */
const MAX_AUTO_PERCENT = 93;

/**
 * Hook that drives a fake-but-realistic multi-stage progress bar.
 *
 * Usage:
 *   const progress = useTaskProgress();
 *   progress.start(EXAM_PDF_STAGES);
 *   await apiCall();
 *   progress.finish();          // snaps to 100 % then hides
 */
export function useTaskProgress() {
  const [state, setState] = useState<TaskProgressState>({
    running: false,
    percent: 0,
    stageIndex: 0,
    stages: [],
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function start(stages: ProgressStage[]) {
    if (intervalRef.current) clearInterval(intervalRef.current);

    const totalMs = stages.reduce((s, st) => s + st.durationMs, 0);
    let elapsed = 0;

    setState({ running: true, percent: 0, stageIndex: 0, stages });

    intervalRef.current = setInterval(() => {
      elapsed += TICK_MS;
      const raw = (elapsed / totalMs) * 100;
      const percent = Math.min(raw, MAX_AUTO_PERCENT);

      // Figure out which stage we are in based on elapsed time.
      let acc = 0;
      let stageIndex = stages.length - 1;
      for (let i = 0; i < stages.length; i++) {
        acc += stages[i].durationMs;
        if (elapsed < acc) {
          stageIndex = i;
          break;
        }
      }

      setState((prev) => ({ ...prev, percent, stageIndex }));
    }, TICK_MS);
  }

  function finish() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    // Snap to 100 % briefly so the user sees completion.
    setState((prev) => ({
      ...prev,
      percent: 100,
      stageIndex: (prev.stages.length || 1) - 1,
    }));
    setTimeout(() => {
      setState({ running: false, percent: 0, stageIndex: 0, stages: [] });
    }, 600);
  }

  function cancel() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setState({ running: false, percent: 0, stageIndex: 0, stages: [] });
  }

  // Cleanup on unmount.
  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  return { state, start, finish, cancel };
}

// ─── UI component ────────────────────────────────────────────────────────────

interface TaskProgressProps {
  state: TaskProgressState;
}

export default function TaskProgress({ state }: TaskProgressProps) {
  if (!state.running) return null;

  const { percent, stageIndex, stages } = state;
  const currentLabel = stages[stageIndex]?.label ?? "처리 중...";
  const isLlmStage = currentLabel.includes("Opus") || currentLabel.includes("AI") || currentLabel.includes("풀이");

  return (
    <div className="fade-in-up mt-4 rounded-xl bg-muted p-3.5">
      <div className="mb-2.5 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex gap-0.5" aria-hidden>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1 w-1 rounded-full bg-foreground"
                style={{ animation: `pulse-dot 1.2s ease-in-out ${i * 0.16}s infinite` }}
              />
            ))}
          </span>
          <span className="text-[13px] font-medium tracking-[-0.01em]">{currentLabel}</span>
        </div>
        <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
          {Math.round(percent)}%
        </span>
      </div>

      <div className="progress-track">
        <div
          className={`progress-fill ${percent >= 100 ? "bg-emerald-500" : isLlmStage ? "bg-amber-500" : ""}`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {stages.length > 1 && (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {stages.map((stage, i) => {
            const done = i < stageIndex || percent >= 100;
            const active = i === stageIndex && percent < 100;
            return (
              <span
                key={i}
                className={`badge transition-colors duration-150 ${
                  done
                    ? "text-foreground"
                    : active
                    ? "bg-card text-foreground shadow-[0_0_0_1px_var(--border)]"
                    : "text-subtle-foreground"
                }`}
              >
                {done && (
                  <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="m3.5 8.5 3 3 6-7" /></svg>
                )}
                {stage.label.replace("...", "").replace(" 중", "")}
              </span>
            );
          })}
        </div>
      )}

      {isLlmStage && (
        <p className="mt-2.5 text-xs text-muted-foreground">
          Claude Opus가 문제마다 풀이를 쓰고 있습니다. 문제 수에 따라 30초에서 1분쯤 걸립니다.
        </p>
      )}
    </div>
  );
}
