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
    <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50">
      {/* Stage label */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Animated dots indicator */}
          <span className="inline-flex gap-0.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-blue-500"
                style={{
                  animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
                }}
              />
            ))}
          </span>
          <span className="text-sm text-zinc-700 dark:text-zinc-300">{currentLabel}</span>
        </div>
        <span className="shrink-0 text-xs tabular-nums text-zinc-400">
          {Math.round(percent)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
        <div
          className={`h-full rounded-full transition-all duration-100 ${
            percent >= 100 ? "bg-green-500" : isLlmStage ? "bg-amber-500" : "bg-blue-500"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Stage chips */}
      {stages.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {stages.map((stage, i) => {
            const done = i < stageIndex || percent >= 100;
            const active = i === stageIndex && percent < 100;
            return (
              <span
                key={i}
                className={`rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${
                  done
                    ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
                    : active
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400"
                    : "bg-zinc-100 text-zinc-400 dark:bg-zinc-700 dark:text-zinc-500"
                }`}
              >
                {done && "✓ "}
                {stage.label.replace("...", "").replace(" 중", "")}
              </span>
            );
          })}
        </div>
      )}

      {/* LLM notice */}
      {isLlmStage && (
        <p className="mt-2 text-xs text-zinc-400">
          Claude Opus가 각 문제의 풀이를 작성하고 있습니다. 문제 수에 따라 30초~1분 소요될 수 있습니다.
        </p>
      )}

      <style jsx>{`
        @keyframes pulse-dot {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
