"use client";

import katex from "katex";

interface MathTextProps {
  text: string;
  className?: string;
}

type Segment =
  | { type: "text"; value: string }
  | { type: "math"; value: string; displayMode: boolean };

export default function MathText({ text, className }: MathTextProps) {
  const html = renderMathText(normalizeText(text));

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function renderMathText(text: string): string {
  return tokenizeMathText(text).map((segment) => {
    if (segment.type === "text") {
      return renderTextSegment(segment.value);
    }

    return renderMathSegment(segment.value, segment.displayMode);
  }).join("");
}

function renderTextSegment(text: string): string {
  return text
    .split(/(\n)/)
    .map((part) => {
      if (part === "\n") {
        return "\n";
      }

      if (isMathLine(part)) {
        return renderMathSegment(toLatexExpression(part), true);
      }

      return renderInlinePlainMath(part);
    })
    .join("");
}

function renderInlinePlainMath(text: string): string {
  const expressionPattern = /x\^m\d(?:\s+ln\s+x)?|x\^\([^)]+\)\/\d+(?:\s+ln\s+x)?|\bm\d\b/g;
  let html = "";
  let index = 0;
  let match: RegExpExecArray | null;

  while ((match = expressionPattern.exec(text)) !== null) {
    html += renderMarkdownText(text.slice(index, match.index));
    html += renderMathSegment(toLatexExpression(match[0]), false);
    index = match.index + match[0].length;
  }

  html += renderMarkdownText(text.slice(index));
  return html;
}

function renderMathSegment(value: string, displayMode: boolean): string {
  try {
    const rendered = katex.renderToString(value, {
      displayMode,
      throwOnError: false,
      strict: false,
    });
    return displayMode ? rendered : `<span class="math-inline">${rendered}</span>`;
  } catch {
    return escapeHtml(value);
  }
}

function tokenizeMathText(text: string): Segment[] {
  const segments: Segment[] = [];
  let index = 0;

  while (index < text.length) {
    const delimiter = findNextMathBoundary(text, index);
    if (!delimiter) {
      segments.push({ type: "text", value: text.slice(index) });
      break;
    }

    if (delimiter.start > index) {
      segments.push({ type: "text", value: text.slice(index, delimiter.start) });
    }

    segments.push(delimiter.segment);
    index = delimiter.end;
  }

  return segments;
}

function findNextMathBoundary(text: string, from: number) {
  const delimiter = findNextDelimiter(text, from);
  const bareLatex = findNextBareLatex(text, from);

  if (!delimiter) {
    return bareLatex;
  }
  if (!bareLatex) {
    return delimiter;
  }

  return delimiter.start <= bareLatex.start ? delimiter : bareLatex;
}

function findNextDelimiter(text: string, from: number) {
  const delimiters = [
    { open: "\\[", close: "\\]", displayMode: true },
    { open: "$$", close: "$$", displayMode: true },
    { open: "\\(", close: "\\)", displayMode: false },
    { open: "$", close: "$", displayMode: false },
  ];

  let match: { start: number; open: string; close: string; displayMode: boolean } | null = null;
  for (const delimiter of delimiters) {
    const start = text.indexOf(delimiter.open, from);
    if (start === -1) {
      continue;
    }
    if (!match || start < match.start) {
      match = { start, ...delimiter };
    }
  }

  if (!match) {
    return null;
  }

  const contentStart = match.start + match.open.length;
  const contentEnd = text.indexOf(match.close, contentStart);
  if (contentEnd === -1) {
    return null;
  }

  return {
    start: match.start,
    end: contentEnd + match.close.length,
    segment: {
      type: "math" as const,
      value: text.slice(contentStart, contentEnd),
      displayMode: match.displayMode,
    },
  };
}

function findNextBareLatex(text: string, from: number) {
  const commandPattern = /\\(?:frac|dfrac|tfrac|sqrt|sum|int|lim|sin|cos|tan|log|ln|left|right|begin|end|alpha|beta|gamma|delta|theta|lambda|mu|pi|sigma|omega)\b/g;
  commandPattern.lastIndex = from;

  let match: RegExpExecArray | null;
  while ((match = commandPattern.exec(text)) !== null) {
    const start = match.index;
    const end = findBareLatexEnd(text, start);
    if (end <= start) {
      continue;
    }

    const value = text.slice(start, end).trim();
    if (!isLikelyStandaloneLatex(value)) {
      continue;
    }

    return {
      start,
      end,
      segment: {
        type: "math" as const,
        value,
        displayMode: false,
      },
    };
  }

  return null;
}

function findBareLatexEnd(text: string, start: number): number {
  let index = start;
  let braceDepth = 0;

  while (index < text.length) {
    const char = text[index];

    if (char === "{") {
      braceDepth += 1;
    } else if (char === "}") {
      braceDepth = Math.max(0, braceDepth - 1);
    } else if (braceDepth === 0 && /[\s,.;:!?]/.test(char) && index > start) {
      break;
    }

    index += 1;
  }

  return index;
}

function normalizeText(text: string): string {
  return stripMarkdownArtifacts(text)
    .replace(/\\\\\(/g, "\\(")
    .replace(/\\\\\)/g, "\\)")
    .replace(/\\\\\[/g, "\\[")
    .replace(/\\\\\]/g, "\\]")
    .replace(/([.!?])(\([a-z]\))/g, "$1\n$2")
    .replace(/([^\s])(\([a-z]\))/g, "$1\n$2")
    .replace(/(\([a-z]\))(?=\S)/g, "$1 ")
    // Join continuation lines that start with "/" onto the previous line
    // e.g. "m³\n/kg" → "m³/kg" (split unit from PDF column layout)
    .replace(/([^\n])\n(\/[a-zA-Z])/g, "$1$2")
    .replace(/\n{2,}/g, "\n");
}

function renderMarkdownText(text: string): string {
  let html = "";
  let index = 0;

  for (const match of text.matchAll(/\*\*([^*]+?)\*\*/g)) {
    html += escapeHtml(text.slice(index, match.index));
    html += `<strong>${escapeHtml(match[1].trim())}</strong>`;
    index = (match.index ?? 0) + match[0].length;
  }

  html += escapeHtml(text.slice(index));
  return html;
}

function stripMarkdownArtifacts(text: string): string {
  return text
    .replace(/\*\*([^*]+?)\*\*/g, "$1")
    .replace(/\.\s*\*\s*\*/g, "")
    .replace(/\*\s*\*\s*\./g, "")
    .replace(/\*\s*\*/g, "")
    .replace(/\*\*/g, "");
}

function isMathLine(value: string): boolean {
  const text = value.trim();
  if (text.length < 3 || text.length > 140) {
    return false;
  }
  if (/[가-힣]/.test(text)) {
    return false;
  }

  // Must contain "=" to qualify as a display equation.
  // This prevents unit strings like "/kg" or "kJ/kg − K" (which contain "/"
  // but are not equations) from being rendered as centred display math.
  const hasEquality = /=/.test(text);
  const hasWords = /[A-Za-z]{4,}/.test(text.replace(/\bln\b/g, ""));
  return hasEquality && !hasWords;
}

function isLikelyStandaloneLatex(value: string): boolean {
  if (/[가-힣]/.test(value)) {
    return false;
  }
  if (/\\(?:begin|end|frac|dfrac|tfrac|sqrt|sum|int|lim|left|right)/.test(value)) {
    return true;
  }
  if (/\\(?:ln|log|sin|cos|tan)\b/.test(value)) {
    return /[A-Za-z0-9_^{}]/.test(value);
  }
  return false;
}

function toLatexExpression(value: string): string {
  return value
    .trim()
    .replace(/\bx\^m(\d)\b/g, "x^{m_$1}")
    .replace(/\bx\^\(([^)]+)\)\/(\d+)/g, "x^{($1)/$2}")
    .replace(/\bm(\d)\b/g, "m_$1")
    .replace(/\bx(\d+)\b/g, "x^{$1}")
    .replace(/\bD(\d+)\b/g, "D^{$1}")
    .replace(/\bln\b/g, "\\ln")
    .replace(/!/g, "-");
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
