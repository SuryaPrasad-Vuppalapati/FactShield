import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { api } from "./lib/api";
import type { DocumentItem, FlaggedGradeItem, QuizQuestion } from "./lib/types";

import "./App.css";

const MD_COMPONENTS = {
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
  ),
};

// ── Simple toast notification system ─────────────────────────────────────────
interface Toast { id: string; message: string; type: "error" | "success" | "info"; }
let _toastSetter: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

function showToast(message: string, type: Toast["type"] = "error") {
  if (!_toastSetter) return;
  const id = Math.random().toString(36).slice(2);
  _toastSetter(prev => [...prev, { id, message, type }]);
  setTimeout(() => _toastSetter!(prev => prev.filter(t => t.id !== id)), 4000);
}

const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  _toastSetter = setToasts;
  return (
    <div style={{ position: "fixed", bottom: "1.5rem", right: "1.5rem", zIndex: 9999, display: "flex", flexDirection: "column", gap: "0.5rem", pointerEvents: "none" }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          padding: "0.75rem 1.1rem", borderRadius: "10px", fontSize: "0.85rem", fontWeight: 500,
          background: t.type === "error" ? "#fee2e2" : t.type === "success" ? "#dcfce7" : "#e0f2fe",
          color: t.type === "error" ? "#991b1b" : t.type === "success" ? "#166534" : "#0c4a6e",
          border: `1px solid ${t.type === "error" ? "#fca5a5" : t.type === "success" ? "#86efac" : "#7dd3fc"}`,
          boxShadow: "0 4px 12px rgba(0,0,0,0.12)", maxWidth: "320px", pointerEvents: "auto",
          animation: "fadeIn 0.2s ease",
        }}>{t.message}</div>
      ))}
    </div>
  );
};

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  data?: any;
}

interface FactShieldScoreBadgeProps {
  entailment: boolean | null;
  consistency: boolean;
  confidence: number;        // 0–1 decimal
  trustScore?: number;       // 0–1 decimal
  trustTier?: string;        // "verified" | "partial" | "unverified"
  entailmentScore?: number;
  consistencyScore?: number;
  sourceRef?: string;
  role?: "student" | "teacher";
  badgeTitle?: string;
}

// Tier visual config
const TIER_CONFIG = {
  verified: {
    label: "FactShield Verified",
    color: "#1a7f37",
    bg: "#f0fdf4",
    border: "#86efac",
    dot: "#16a34a",
    desc: "Response is grounded in your document and self-consistent.",
  },
  partial: {
    label: "Partially Verified",
    color: "#92400e",
    bg: "#fffbeb",
    border: "#fcd34d",
    dot: "#d97706",
    desc: "Some claims may draw from general knowledge. Cross-check key facts.",
  },
  unverified: {
    label: "Not Verified",
    color: "#991b1b",
    bg: "#fef2f2",
    border: "#fca5a5",
    dot: "#dc2626",
    desc: "Response could not be verified against your document.",
  },
} as const;

export const FactShieldScoreBadge: React.FC<FactShieldScoreBadgeProps> = ({
  entailment,
  consistency,
  confidence,
  trustScore = 0,
  trustTier = "unverified",
  entailmentScore = 0,
  consistencyScore = 0,
  sourceRef,
  badgeTitle,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const tier = TIER_CONFIG[trustTier as keyof typeof TIER_CONFIG] ?? TIER_CONFIG.unverified;
  const trustPct = Math.round(trustScore * 100);

  // Per-pipeline colors
  const pipelineColor = (pass: boolean | null) =>
    pass === null ? "#9b9b9b" : pass ? "#16a34a" : "#dc2626";
  const confColor = confidence >= 0.65 ? "#16a34a" : confidence >= 0.35 ? "#d97706" : "#dc2626";

  return (
    <div className="factshield-score-badge-wrapper" style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>

      {badgeTitle && (
        <span style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {badgeTitle}
        </span>
      )}

      {/* Source banner */}
      {sourceRef && (
        <div style={{ fontSize: "11px", color: "var(--color-text-secondary)", borderLeft: "2px solid #1d759e", paddingLeft: "0.5rem", marginBottom: "0.15rem", fontStyle: "italic" }}>
          {"Source: "}
          {sourceRef.split(", ").map((part, i, arr) => {
            const m = part.match(/^\[(.+?)\]\((.+?)\)$/);
            return (
              <span key={i}>
                {m ? (
                  <a href={m[2]} target="_blank" rel="noopener noreferrer" style={{ color: "#1d759e", textDecoration: "underline", fontStyle: "normal" }}>{m[1]}</a>
                ) : <span>{part}</span>}
                {i < arr.length - 1 && ", "}
              </span>
            );
          })}
        </div>
      )}

      {/* PRIMARY: Trust tier banner */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
        <div
          onClick={() => setExpanded(e => !e)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.45rem 0.75rem",
            borderRadius: "8px",
            backgroundColor: tier.bg,
            border: `1px solid ${tier.border}`,
            cursor: "pointer",
            width: "fit-content",
            userSelect: "none",
          }}
        >
          {/* Pulsing dot */}
          <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: tier.dot, display: "inline-block", flexShrink: 0 }} />

          <span style={{ fontSize: "12px", fontWeight: 700, color: tier.color, letterSpacing: "0.01em" }}>
            {tier.label}
          </span>

          {/* Trust score pill */}
          <span style={{
            fontSize: "11px", fontWeight: 600, color: tier.color,
            backgroundColor: "rgba(0,0,0,0.06)", borderRadius: "4px",
            padding: "0px 5px",
          }}>
            {trustPct}%
          </span>

          <span style={{ fontSize: "10px", color: tier.color, opacity: 0.7, marginLeft: "0.25rem" }}>
            {expanded ? "▲" : "▼"} details
          </span>
        </div>

        {/* Help button */}
        <div style={{ position: "relative" }}>
          <button
            type="button"
            onClick={() => setShowHelp(h => !h)}
            style={{
              width: 18, height: 18, borderRadius: "50%", border: "1px solid #94a3b8",
              background: "#f1f5f9", color: "#64748b", fontSize: "10px", fontWeight: 700,
              cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center",
              padding: 0, lineHeight: 1,
            }}
            title="What does this score mean?"
          >?</button>
          {showHelp && (
            <div style={{
              position: "absolute", bottom: "calc(100% + 6px)", left: 0, zIndex: 100,
              background: "#1e293b", color: "#e2e8f0", borderRadius: "10px",
              padding: "0.8rem 1rem", fontSize: "11.5px", lineHeight: 1.6,
              width: 240, boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
            }}>
              <div style={{ fontWeight: 700, marginBottom: "0.4rem", color: "#fff" }}>FactShield Trust Score</div>
              <div>Three research pipelines validate every response:</div>
              <div style={{ margin: "0.4rem 0 0.2rem", paddingLeft: "0.5rem", borderLeft: "2px solid #4ade80" }}>
                <b style={{ color: "#4ade80" }}>Verified ≥ 65%</b> — grounded in your document, self-consistent, high confidence.
              </div>
              <div style={{ margin: "0.2rem 0", paddingLeft: "0.5rem", borderLeft: "2px solid #f59e0b" }}>
                <b style={{ color: "#f59e0b" }}>Partial 35–64%</b> — draws from general knowledge or web sources. Cross-check key facts.
              </div>
              <div style={{ margin: "0.2rem 0", paddingLeft: "0.5rem", borderLeft: "2px solid #ef4444" }}>
                <b style={{ color: "#ef4444" }}>Unverified &lt;35%</b> — could not be verified. Confirm with your instructor.
              </div>
              <div style={{ marginTop: "0.5rem", opacity: 0.7, fontSize: "10.5px" }}>Click "details" to see the 3-pipeline breakdown.</div>
            </div>
          )}
        </div>
      </div>

      {/* Tier description (always shown) */}
      <div style={{ fontSize: "11px", color: "var(--color-text-secondary)", paddingLeft: "0.2rem" }}>
        {tier.desc}
      </div>

      {/* SECONDARY: 3-pipeline breakdown (expandable) */}
      {expanded && (
        <div style={{
          display: "flex", flexDirection: "column", gap: "0.3rem",
          padding: "0.5rem 0.65rem",
          borderRadius: "6px",
          backgroundColor: "#fcfcfa",
          border: "1px solid var(--color-border)",
          fontSize: "11.5px",
          fontFamily: "monospace",
        }}>
          <div style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.15rem" }}>
            3-Pipeline Breakdown
          </div>

          {/* Entailment */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ color: "var(--color-text-secondary)", minWidth: 110 }}>Entailment (NLI):</span>
            <span style={{ color: pipelineColor(entailment), fontWeight: 600 }}>
              {entailment === null ? "Skipped" : entailment ? "Passed" : "Failed"}
            </span>
            {entailmentScore > 0 && (
              <span style={{ color: "#9b9b9b" }}>({entailmentScore.toFixed(3)})</span>
            )}
          </div>

          {/* Consistency */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ color: "var(--color-text-secondary)", minWidth: 110 }}>Consistency (3x):</span>
            <span style={{ color: pipelineColor(consistency), fontWeight: 600 }}>
              {consistency ? "Passed" : "Failed"}
            </span>
            {consistencyScore > 0 && (
              <span style={{ color: "#9b9b9b" }}>({consistencyScore.toFixed(3)})</span>
            )}
          </div>

          {/* Confidence */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ color: "var(--color-text-secondary)", minWidth: 110 }}>Confidence:</span>
            <span style={{ color: confColor, fontWeight: 600 }}>
              {confidence >= 0.65 ? "High" : confidence >= 0.35 ? "Medium" : "Low"}
            </span>
            <span style={{ color: "#9b9b9b" }}>({confidence.toFixed(3)})</span>
          </div>

          <div style={{ marginTop: "0.2rem", fontSize: "10px", color: "#9b9b9b" }}>
            Trust = 0.50×NLI + 0.30×Consistency + 0.20×Confidence (document source)
          </div>
        </div>
      )}
    </div>
  );
};


// ── Submission Audit Panel ────────────────────────────────────────────────────
const ISSUE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  "Overgeneralization": { bg: "#fff7ed", border: "#fb923c", text: "#9a3412" },
  "Contradiction":      { bg: "#fef2f2", border: "#f87171", text: "#991b1b" },
  "Unsupported Claim":  { bg: "#fffbeb", border: "#fbbf24", text: "#92400e" },
  "External Information": { bg: "#f0f9ff", border: "#38bdf8", text: "#0c4a6e" },
};

interface AuditFlag { sentence: string; issue: string; why: string; docSays: string; revision: string; }

function parseAudit(text: string): { overall: string; passed: string[]; flagged: AuditFlag[]; actions: string[] } | null {
  if (!text.includes("Submission Audit")) return null;
  const overall = text.match(/\*\*Overall:\*\*([^\n]+)/)?.[1]?.trim() ?? "";
  const passedSection = text.match(/###\s*✅ Passed\n([\s\S]*?)(?=###|$)/)?.[1] ?? "";
  const passed = [...passedSection.matchAll(/^[-*]\s+"?([^"\n]+)"?/gm)].map(m => m[1].trim());
  const flaggedSection = text.match(/###\s*⚠️ Flagged\n([\s\S]*?)(?=###|$)/)?.[1] ?? "";
  const flagged: AuditFlag[] = [];
  const flagBlocks = flaggedSection.split(/\n(?=\*\*\d+\.)/);
  for (const block of flagBlocks) {
    const sentence = block.match(/^\*\*\d+\.\s+"?([^"*\n]+)"?\*\*/)?.[1]?.trim() ?? "";
    if (!sentence) continue;
    const issue   = block.match(/\*\*Issue:\*\*\s*([^\n]+)/)?.[1]?.trim() ?? "";
    const why     = block.match(/\*\*Why:\*\*\s*([^\n]+)/)?.[1]?.trim() ?? "";
    const docSays = block.match(/\*\*Document says:\*\*\s*"?([^"*\n]+)"?/)?.[1]?.trim() ?? "";
    const revision = block.match(/\*\*Revision:\*\*\s*"?([^"*\n]+)"?/)?.[1]?.trim() ?? "";
    flagged.push({ sentence, issue, why, docSays, revision });
  }
  const actionsSection = text.match(/###\s*📋 Action Items\n([\s\S]*?)(?=###|$)/)?.[1] ?? "";
  const actions = [...actionsSection.matchAll(/^\d+\.\s+(.+)/gm)].map(m => m[1].trim());
  return { overall, passed, flagged, actions };
}

const SubmissionAuditPanel: React.FC<{ text: string }> = ({ text }) => {
  const audit = parseAudit(text);
  if (!audit) return (
    <div className="markdown-body"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{text}</ReactMarkdown></div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Header */}
      <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--color-text-primary)" }}>
        Submission Audit
        {audit.overall && <span style={{ marginLeft: "0.75rem", fontSize: "0.85rem", fontWeight: 400, color: "var(--color-text-secondary)" }}>{audit.overall}</span>}
      </div>

      {/* Passed */}
      {audit.passed.length > 0 && (
        <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: "8px", padding: "0.75rem 1rem" }}>
          <div style={{ fontWeight: 600, color: "#166534", marginBottom: "0.4rem", fontSize: "0.85rem" }}>✅ Passed ({audit.passed.length})</div>
          {audit.passed.map((s, i) => (
            <div key={i} style={{ fontSize: "0.83rem", color: "#166534", padding: "2px 0" }}>• "{s}"</div>
          ))}
        </div>
      )}

      {/* Flagged */}
      {audit.flagged.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
          <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "#b45309" }}>⚠️ Flagged ({audit.flagged.length})</div>
          {audit.flagged.map((f, i) => {
            const colors = ISSUE_COLORS[f.issue] ?? { bg: "#f9fafb", border: "#9ca3af", text: "#374151" };
            return (
              <div key={i} style={{ background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: "8px", padding: "0.75rem 1rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                <div style={{ fontSize: "0.88rem", fontWeight: 600, color: colors.text }}>"{f.sentence}"</div>
                <div style={{ fontSize: "0.8rem" }}><span style={{ fontWeight: 600 }}>Issue:</span> <span style={{ background: colors.border, color: "#fff", borderRadius: "4px", padding: "0 6px", fontSize: "0.75rem" }}>{f.issue}</span></div>
                {f.why     && <div style={{ fontSize: "0.8rem", color: "#374151" }}><span style={{ fontWeight: 600 }}>Why: </span>{f.why}</div>}
                {f.docSays && <div style={{ fontSize: "0.8rem", color: "#1d4ed8", fontStyle: "italic" }}><span style={{ fontWeight: 600, fontStyle: "normal" }}>Document: </span>"{f.docSays}"</div>}
                {f.revision && <div style={{ fontSize: "0.8rem", color: "#166534" }}><span style={{ fontWeight: 600 }}>Revision: </span>"{f.revision}"</div>}
              </div>
            );
          })}
        </div>
      )}

      {/* Action Items */}
      {audit.actions.length > 0 && (
        <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "0.75rem 1rem" }}>
          <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "#334155", marginBottom: "0.4rem" }}>📋 Action Items</div>
          {audit.actions.map((a, i) => (
            <div key={i} style={{ fontSize: "0.82rem", color: "#475569", padding: "2px 0" }}>{i + 1}. {a}</div>
          ))}
        </div>
      )}
    </div>
  );
};
// ─────────────────────────────────────────────────────────────────────────────

const normalizeAnswer = (v: string): string => (v || "").toString().trim().toLowerCase().replace(/\s+/g, " ");

const quizAnswerMatches = (question: QuizQuestion, userValue: string): boolean => {
  const accepted = Array.isArray(question.answer) ? question.answer : [question.answer];
  return accepted.some((a) => normalizeAnswer(String(a)) === normalizeAnswer(userValue));
};

// Shared button styles matching the design system
const btnPrimary: React.CSSProperties = {
  background: "var(--color-accent)",
  color: "#fff",
  border: "none",
  borderRadius: "8px",
  padding: "0.45rem 1rem",
  fontSize: "0.85rem",
  fontWeight: 500,
  cursor: "pointer",
  transition: "opacity 0.15s",
};
const btnSecondary: React.CSSProperties = {
  background: "var(--color-accent-light, #E6F1FB)",
  color: "var(--color-accent)",
  border: "1px solid var(--color-accent)",
  borderRadius: "8px",
  padding: "0.45rem 1rem",
  fontSize: "0.85rem",
  fontWeight: 500,
  cursor: "pointer",
  transition: "opacity 0.15s",
};

const QuizGeneratorPanel: React.FC<{ quiz: QuizQuestion[] }> = ({ quiz }) => {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, { ok: boolean; user: string }>>({});
  const [warnings, setWarnings] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const panelIdRef = useRef(`quiz-${Math.random().toString(36).slice(2, 9)}`);

  const totalQuestions = quiz.length;
  const totalChecked = Object.values(checked).filter(Boolean).length;
  const totalCorrect = Object.values(result).filter((r) => r.ok).length;
  const pct = submitted ? Math.round((totalCorrect / totalQuestions) * 100) : null;

  const handleCheck = (id: number, q: QuizQuestion) => {
    const val = (answers[id] || "").trim();
    if (!val) {
      setWarnings((prev) => ({ ...prev, [id]: "Please select or enter an answer first." }));
      return;
    }
    const ok = quizAnswerMatches(q, val);
    setChecked((prev) => ({ ...prev, [id]: true }));
    setResult((prev) => ({ ...prev, [id]: { ok, user: val } }));
    setWarnings((prev) => ({ ...prev, [id]: "" }));
  };

  const handleSubmit = () => {
    const newChecked: Record<number, boolean> = {};
    const newResult: Record<number, { ok: boolean; user: string }> = {};
    quiz.forEach((q, idx) => {
      const id = idx + 1;
      const val = (answers[id] || "").trim();
      newChecked[id] = true;
      newResult[id] = { ok: val ? quizAnswerMatches(q, val) : false, user: val };
    });
    setChecked(newChecked);
    setResult(newResult);
    setWarnings({});
    setSubmitted(true);
  };

  const scoreColor = pct === null ? "#378ADD" : pct >= 80 ? "#166534" : pct >= 50 ? "#92400e" : "#991b1b";
  const scoreBg   = pct === null ? "#E6F1FB"  : pct >= 80 ? "#f0fdf4"  : pct >= 50 ? "#fffbeb" : "#fef2f2";

  return (
    <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Header card */}
      <div style={{ border: "1px solid var(--color-border)", borderRadius: "10px", padding: "1rem", background: "var(--color-surface-subtle, #f8fafc)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Quiz Generator</div>
            <h4 style={{ margin: "0.2rem 0 0", fontSize: "1.05rem" }}>Topic-based adaptive quiz</h4>
          </div>
          <span className="role-pill-tag student-pill">{totalQuestions} Questions</span>
        </div>
        {submitted && pct !== null ? (
          <div style={{ marginTop: "0.65rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{ background: scoreBg, color: scoreColor, borderRadius: "8px", padding: "0.4rem 0.9rem", fontWeight: 600, fontSize: "1rem" }}>
              {pct}%
            </div>
            <div style={{ fontSize: "0.88rem", color: "var(--color-text-secondary)" }}>
              {totalCorrect} / {totalQuestions} correct
              {pct >= 80 ? " — Great work!" : pct >= 50 ? " — Keep practising." : " — Review the explanations below."}
            </div>
          </div>
        ) : (
          <p style={{ margin: "0.65rem 0 0", color: "var(--color-text-secondary)", fontSize: "0.88rem" }}>
            {totalChecked > 0 ? <><strong>{totalCorrect}</strong> / <strong>{totalChecked}</strong> checked so far</> : "Answer questions below, then submit for your score."}
          </p>
        )}
      </div>

      {/* Questions */}
      {quiz.map((q, idx) => {
        const id = idx + 1;
        const userAns = answers[id] || "";
        const isLocked = !!checked[id];
        const res = result[id];
        return (
          <div key={id} style={{ border: "1px solid var(--color-border)", borderRadius: "10px", padding: "1rem", background: "var(--color-surface, #fff)", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <strong style={{ fontSize: "0.9rem" }}>Q{id}</strong>
              <span className="role-pill-tag student-pill" style={{ padding: "0.15rem 0.45rem" }}>Level {q.level}</span>
              <span className="role-pill-tag" style={{ padding: "0.15rem 0.45rem", background: "#f3f4f6", color: "#4b5563" }}>{q.type.toUpperCase()}</span>
            </div>

            <div className="markdown-body" style={{ fontSize: "0.93rem" }}>
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{q.q}</ReactMarkdown>
            </div>

            {q.type === "code" && q.code && (
              <pre style={{ margin: 0, background: "#0b1220", color: "#dbe8ff", borderRadius: "8px", padding: "0.75rem", overflowX: "auto", fontSize: "0.83rem" }}>{q.code}</pre>
            )}

            {q.type === "mcq" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                {(q.options || []).map((option, optIdx) => {
                  const isSelected = userAns === option;
                  const isCorrectOption = isLocked && res && normalizeAnswer(option) === normalizeAnswer(Array.isArray(q.answer) ? q.answer[0] : q.answer);
                  const isWrongSelected = isLocked && isSelected && !res?.ok;
                  return (
                    <label key={optIdx} style={{
                      display: "flex", alignItems: "flex-start", gap: "0.5rem",
                      padding: "0.45rem 0.65rem", borderRadius: "8px", cursor: isLocked ? "default" : "pointer",
                      border: `1px solid ${isCorrectOption ? "#86efac" : isWrongSelected ? "#fca5a5" : isSelected ? "var(--color-accent)" : "var(--color-border)"}`,
                      background: isCorrectOption ? "#f0fdf4" : isWrongSelected ? "#fef2f2" : isSelected ? "var(--color-accent-light, #E6F1FB)" : "#fff",
                    }}>
                      <input type="radio" name={`${panelIdRef.current}-q${id}`} value={option}
                        checked={isSelected} disabled={isLocked}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [id]: e.target.value }))}
                        style={{ marginTop: "0.2rem" }} />
                      <span style={{ fontSize: "0.88rem" }}>{option}</span>
                    </label>
                  );
                })}
              </div>
            ) : q.type === "code" ? (
              <textarea rows={3} value={userAns} disabled={isLocked}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [id]: e.target.value }))}
                placeholder="Type the missing line / step"
                style={{ width: "100%", border: "1px solid var(--color-border)", borderRadius: "8px", padding: "0.55rem", fontFamily: "monospace", fontSize: "0.85rem", boxSizing: "border-box" }} />
            ) : (
              <input type="text" value={userAns} disabled={isLocked}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [id]: e.target.value }))}
                placeholder={q.type === "math" ? "Type expression / value" : "Type your answer"}
                style={{ width: "100%", border: "1px solid var(--color-border)", borderRadius: "8px", padding: "0.55rem", fontSize: "0.88rem", boxSizing: "border-box" }} />
            )}

            {!isLocked && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <button type="button" style={btnSecondary} onClick={() => handleCheck(id, q)}>Check Answer</button>
                {warnings[id] && <span style={{ fontSize: "0.8rem", color: "#b45309" }}>{warnings[id]}</span>}
              </div>
            )}

            {isLocked && res && (
              <div style={{ borderRadius: "8px", padding: "0.65rem 0.75rem", background: res.ok ? "#f0fdf4" : "#fef2f2", color: res.ok ? "#166534" : "#991b1b", fontSize: "0.85rem" }}>
                <div style={{ fontWeight: 600, marginBottom: res.ok ? 0 : "0.25rem" }}>{res.ok ? "✓ Correct" : "✗ Needs review"}</div>
                {!res.ok && <div style={{ marginBottom: "0.3rem", fontSize: "0.83rem" }}><strong>Correct answer:</strong> {Array.isArray(q.answer) ? q.answer[0] : q.answer}</div>}
                <div style={{ color: res.ok ? "#15803d" : "#7f1d1d", fontSize: "0.82rem" }}>{q.explain}</div>
              </div>
            )}
          </div>
        );
      })}

      {/* Submit bar */}
      {!submitted && (
        <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "0.25rem" }}>
          <button type="button" style={btnPrimary} onClick={handleSubmit}>
            Submit Quiz
          </button>
        </div>
      )}
    </div>
  );
};


function App() {
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [activeTool, setActiveTool] = useState<string>("concept-guide");

  // Document list states (shared context)
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [activeDocIds, setActiveDocIds] = useState<string[]>([]);

  // Chat message logs
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [currentInput, setCurrentInput] = useState<string>("");
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>("Retrieving sources...");

  // Session history states
  const [sessions, setSessions] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem("factshield_sessions");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => {
    return "session-" + Math.random().toString(36).substring(7);
  });
  const [showHistory, setShowHistory] = useState<boolean>(false);

  const hasActiveDocs = activeDocIds.length > 0;

  const toggleActiveDoc = (docId: string) => {
    setActiveDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  // File Upload / Banner states
  const [uploadedStudentFileName, setUploadedStudentFileName] = useState<string>("");
  const [showScrollBottom, setShowScrollBottom] = useState<boolean>(false);

  // Dashboard state
  const [flaggedGrades, setFlaggedGrades] = useState<FlaggedGradeItem[]>([]);
  const [dashboardStatus, setDashboardStatus] = useState<string>("");

  const messageStreamRef = useRef<HTMLDivElement>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initial welcome message for chat rooms
  const getWelcomeMessage = (tool: string): string => {
    switch (tool) {
      case "concept-guide":
        return "Concept Guide ready. Ask a question, and I'll explain it grounded strictly in your document.";
      case "problem-navigator":
        return "Problem Navigator ready. Tell me where you're stuck, and I'll guide you step-by-step without giving the answer.";
      case "submission-validator":
        return "Submission Validator ready. Paste your draft assignment, and I'll audit it sentence-by-sentence.";
      case "quiz-generator":
        return "Quiz Generator ready. Ask any topic and I will generate a topic-focused interactive quiz.";
      case "assignment-grader":
        return "Assignment Grader ready. Paste the student's submission and instructions for objective grading.";
      case "exam-generator":
        return "Exam Generator ready. Provide topics and I will create an audited exam sheet.";
      case "adaptive-feedback":
        return "Adaptive Feedback Engine ready. Paste a student's failed answer and I will generate a proactive micro-lesson.";
      case "learning-insights":
        return "Learning Insights Engine ready. What analytical data do you need from the class performance?";
      default:
        return "How can I help you today?";
    }
  };

  // Get active chat logs list
  const getActiveLogs = (): Message[] => {
    if (chatMessages.length === 0) {
      return [{ id: "welcome", sender: "ai", text: getWelcomeMessage(activeTool) }];
    }
    return chatMessages;
  };

  // Load documents on startup
  const fetchDocs = async () => {
    try {
      const res = await api.listDocuments();
      setDocuments(res.documents);
      if (res.documents.length > 0 && activeDocIds.length === 0) {
        setActiveDocIds(res.documents.map((doc) => doc.id));
      }
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const getToolDisplayName = (tool: string): string => {
    switch (tool) {
      case "concept-guide": return "Concept Guide";
      case "problem-navigator": return "Problem Navigator";
      case "submission-validator": return "Submission Validator";
      case "quiz-generator": return "Quiz Generator";
      case "assignment-grader": return "Assignment Grader";
      case "exam-generator": return "Exam Generator";
      case "adaptive-feedback": return "Adaptive Feedback";
      case "learning-insights": return "Learning Insights";
      default: return tool;
    }
  };

  const getToolIdFromDisplayName = (displayName: string): string => {
    switch (displayName) {
      case "Concept Guide": return "concept-guide";
      case "Problem Navigator": return "problem-navigator";
      case "Submission Validator": return "submission-validator";
      case "Quiz Generator": return "quiz-generator";
      case "Assignment Grader": return "assignment-grader";
      case "Exam Generator": return "exam-generator";
      case "Adaptive Feedback": return "adaptive-feedback";
      case "Learning Insights": return "learning-insights";
      default: return displayName;
    }
  };

  const formatRelativeTime = (timestamp: number): string => {
    const now = Date.now();
    const diffMs = now - timestamp;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    
    if (diffSec < 60) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    
    const diffDays = Math.floor(diffHr / 24);
    if (diffDays === 1) return "Yesterday";
    return `${diffDays}d ago`;
  };

  // Save current session to history in localStorage
  const saveCurrentSession = (messagesList: Message[], tool: string, sessionId: string) => {
    const realMessages = messagesList.filter(m => m.id !== "welcome");
    if (realMessages.length === 0) return;

    setSessions((prev) => {
      const firstUserMsg = realMessages.find(m => m.sender === "user")?.text || "New Chat";
      const title = firstUserMsg.substring(0, 30) + (firstUserMsg.length > 30 ? "..." : "");

      const updatedSession = {
        id: sessionId,
        role: role === "student" ? "Student" : "Teacher",
        mode: getToolDisplayName(tool),
        title,
        timestamp: Date.now(),
        messages: messagesList
      };

      const filtered = prev.filter(s => s.id !== sessionId);
      const newSessions = [updatedSession, ...filtered].slice(0, 20);
      localStorage.setItem("factshield_sessions", JSON.stringify(newSessions));
      return newSessions;
    });
  };

  // Start a new chat session
  const startNewChat = (modeOverride?: string) => {
    saveCurrentSession(chatMessages, activeTool, currentSessionId);
    
    const newId = "session-" + Math.random().toString(36).substring(7);
    setCurrentSessionId(newId);
    const targetMode = modeOverride || activeTool;
    setChatMessages([
      {
        id: "welcome",
        sender: "ai",
        text: getWelcomeMessage(targetMode)
      }
    ]);
  };

  // Switch role switch handler
  const handleRoleChangeClick = (newRole: "student" | "teacher") => {
    saveCurrentSession(chatMessages, activeTool, currentSessionId);
    setRole(newRole);
    const defaultTool = newRole === "student" ? "concept-guide" : "assignment-grader";
    setActiveTool(defaultTool);
    startNewChat(defaultTool);
  };

  // Switch tool/mode item click handler
  const handleToolClick = (tool: string) => {
    saveCurrentSession(chatMessages, activeTool, currentSessionId);
    setActiveTool(tool);
    startNewChat(tool);
  };

  // Restore previous session
  const restoreSession = (session: any) => {
    saveCurrentSession(chatMessages, activeTool, currentSessionId);
    
    setCurrentSessionId(session.id);
    const toolId = getToolIdFromDisplayName(session.mode);
    setActiveTool(toolId);
    setChatMessages(session.messages);

    const studentTools = ["concept-guide", "problem-navigator", "submission-validator", "quiz-generator"];
    if (studentTools.includes(toolId)) {
      setRole("student");
    } else {
      setRole("teacher");
    }
  };

  // Delete specific session from history
  const deleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setSessions((prev) => {
      const newSessions = prev.filter(s => s.id !== sessionId);
      localStorage.setItem("factshield_sessions", JSON.stringify(newSessions));
      return newSessions;
    });
    if (currentSessionId === sessionId) {
      startNewChat();
    }
  };

  // Load dashboard items when student insights is active
  useEffect(() => {
    if (activeTool === "learning-insights") {
      setDashboardStatus("Loading flagged submissions...");
      api.getFlaggedGrades()
        .then((res) => {
          setFlaggedGrades(res.flagged_grades);
          setDashboardStatus(res.flagged_grades.length > 0 ? "Done" : "No items need review.");
        })
        .catch((err) => {
          setDashboardStatus(`Error loading items: ${err.message || err}`);
        });
    }
  }, [activeTool]);

  // Scroll to bottom helper
  const scrollToBottom = () => {
    if (messageStreamRef.current) {
      messageStreamRef.current.scrollTo({
        top: messageStreamRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  };

  // Auto-scroll on new message
  useEffect(() => {
    if (messageStreamRef.current) {
      messageStreamRef.current.scrollTop = messageStreamRef.current.scrollHeight;
    }
  }, [chatMessages, isTyping]);

  // Monitor scroll for floating button
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const isScrolledUp = el.scrollHeight - el.scrollTop - el.clientHeight > 150;
    setShowScrollBottom(isScrolledUp);
  };

  // Append message to active logs
  const appendMessage = (sender: "user" | "ai", text: string, data?: any) => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(7),
      sender,
      text,
      data,
    };
    setChatMessages((prev) => {
      const updated = [...prev.filter((m) => m.id !== "welcome"), newMessage];
      saveCurrentSession(updated, activeTool, currentSessionId);
      return updated;
    });
  };


  const parseQuizPayload = (rawText: string): QuizQuestion[] | null => {
    try {
      const cleaned = rawText
        .trim()
        .replace(/^```json\s*/i, "")
        .replace(/^```\s*/i, "")
        .replace(/\s*```$/, "");
      const parsed = JSON.parse(cleaned);
      if (Array.isArray(parsed)) return parsed as QuizQuestion[];
      return null;
    } catch {
      return null;
    }
  };

  // Document file deletes from Sidebar list
  const handleDeleteDoc = async (docId: string, filename: string) => {
    if (window.confirm(`Delete ${filename}? This cannot be undone.`)) {
      try {
        await api.deleteDocument(docId);
        setActiveDocIds((prev) => prev.filter((id) => id !== docId));
        await fetchDocs();
      } catch (err: any) {
        showToast(`Failed to delete document: ${err.message || err}`);
      }
    }
  };

  // Extract student answers (Teacher Grader Mode)
  const handleStudentAnswerUpload = async (file: File) => {
    setIsTyping(true);
    try {
      const res = await api.extractText(file);
      setCurrentInput(res.text);
      setUploadedStudentFileName(file.name);
    } catch (err: any) {
      showToast(`Could not parse student answer: ${err.message || err}`);
    } finally {
      setIsTyping(false);
    }
  };

  // Document grounding index upload
  const uploadFileDirectly = async (file: File) => {
    setIsTyping(true);
    const userMsg: Message = {
      id: Math.random().toString(36).substring(7),
      sender: "user",
      text: `[Attached file: ${file.name}]`,
    };
    const tempAiMsgId = "upload-loading-" + Math.random().toString(36).substring(7);
    const loadingMsg: Message = {
      id: tempAiMsgId,
      sender: "ai",
      text: `Indexing ${file.name}... please wait`,
    };

    setChatMessages((prev) => [...prev.filter(m => m.id !== "welcome"), userMsg, loadingMsg]);

    try {
      const res = await api.uploadDocument(file, role);
      await fetchDocs();
      setActiveDocIds((prev) => (prev.includes(res.doc_id) ? prev : [...prev, res.doc_id]));

      setChatMessages((prev) => {
        const updated = prev.map((m) =>
          m.id === tempAiMsgId
            ? { ...m, text: `${file.name} ready — you can now ask questions about it` }
            : m
        );
        saveCurrentSession(updated, activeTool, currentSessionId);
        return updated;
      });
    } catch (err: any) {
      setChatMessages((prev) => {
        const updated = prev.map((m) =>
          m.id === tempAiMsgId
            ? { ...m, text: `Error indexing file: ${err.message || err}` }
            : m
        );
        saveCurrentSession(updated, activeTool, currentSessionId);
        return updated;
      });
    } finally {
      setIsTyping(false);
    }
  };

  // Preset chip direct submit handler
  //   // Submit text message logic
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentInput.trim() || isTyping || isLoading) return;
    if (!activeDocIds.length) {
      appendMessage("ai", "Please upload or select an active document to ground the conversation.");
      return;
    }

    const userInput = currentInput.trim();
    setCurrentInput("");
    setUploadedStudentFileName("");
    appendMessage("user", userInput);
    setIsTyping(true);
    setIsLoading(true);
    setLoadingStage("Retrieving sources...");

    // Cycle through pipeline stages so the user knows what's happening during the ~18s wait
    const stageTimers = [
      setTimeout(() => setLoadingStage("Generating response..."), 2500),
      setTimeout(() => setLoadingStage("Running FactShield pipelines..."), 7000),
      setTimeout(() => setLoadingStage("Validating with MiniCheck + BERTScore..."), 12000),
    ];

    const historyPayload = chatMessages
      .filter((m) => m.id !== "welcome" && m.text)
      .map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text,
      }));

    try {
      if (activeTool === "concept-guide") {
        const res = await api.conceptGuide({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: res });
      }
      else if (activeTool === "problem-navigator") {
        const res = await api.problemNavigator({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: res });
      }
      else if (activeTool === "submission-validator") {
        const res = await api.submissionValidator({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: { ...res, mode: "submission-validator" } });
      }
      else if (activeTool === "quiz-generator") {
        const res = await api.quizGenerator({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        const quiz = parseQuizPayload(res.text);
        appendMessage(
          "ai",
          quiz ? `Quiz ready: ${quiz.length} questions. Check each answer directly below.` : res.text,
          { apiResponse: res, quiz }
        );
      }
      else if (activeTool === "assignment-grader") {
        const res = await api.assignmentGrader({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: res });
      }
      else if (activeTool === "exam-generator") {
        const res = await api.examGenerator({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: res });
      }
      else if (activeTool === "adaptive-feedback") {
        const res = await api.adaptiveFeedback({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: res });
      }
      else if (activeTool === "learning-insights") {
        const res = await api.learningInsights({
          question: userInput,
          doc_ids: activeDocIds,
          chat_history: historyPayload,
        });
        appendMessage("ai", res.text, { apiResponse: res });
      }
    } catch (err: any) {
      appendMessage("ai", `Sorry, an error occurred: ${err.message || err}`);
    } finally {
      stageTimers.forEach(clearTimeout);
      setIsTyping(false);
      setIsLoading(false);
      setLoadingStage("Retrieving sources...");
    }
  };

  const getQuickReplies = (tool: string): string[] => {
    switch (tool) {
      case "concept-guide":
        return ["Give me an example", "Explain it simply", "Where is this in the document?"];
      case "problem-navigator":
        return ["I'm stuck on step 2", "Can you review my calculation?", "What's the next step?"];
      case "submission-validator":
        return ["Check this paragraph", "Did I miss any key points?", "Re-evaluate my revision"];
      case "quiz-generator":
        return ["Give me 5 questions on agile", "Give me a quiz on biology", "Increase difficulty"];
      case "assignment-grader":
        return ["Grade against Chapter 2", "Focus on technical accuracy", "Show rubric breakdown"];
      case "exam-generator":
        return ["Generate 5 multiple choice questions", "Include short answer questions", "Make it harder"];
      case "adaptive-feedback":
        return ["Student answered 'B'", "Explain why option A is incorrect", "Provide a micro-lesson"];
      case "learning-insights":
        return ["Show most missed topics", "Generate intervention plan", "Analyze recent quiz"];
      default:
        return [];
    }
  };

  const renderScoreBlock = (msg: Message) => {
    if (!msg.data) return null;

    const apiRes = msg.data.apiResponse;
    if (!apiRes) return null;

    const sourceRef = apiRes.source_reference || (() => {
      if (!apiRes.fallback_type || apiRes.fallback_type.toLowerCase() === "none") return undefined;
      if (apiRes.fallback_type.toLowerCase() === "academic") return "ArXiv research";
      if (apiRes.fallback_type.toLowerCase() === "web") return "Web search";
      return apiRes.fallback_type;
    })();

    // Scores can come from the top-level fields OR from apiRes.scores
    const sc = apiRes.scores ?? {};
    const entailment = apiRes.entailment ?? sc.entailment ?? null;
    const consistency = apiRes.consistency ?? sc.consistency ?? false;
    const confidence = apiRes.confidence ?? sc.confidence ?? 0;
    const trustScore = apiRes.trust_score ?? sc.trust_score ?? 0;
    const trustTier = apiRes.trust_tier ?? sc.trust_tier ?? "unverified";
    const entailmentScore = sc.entailment_score ?? 0;
    const consistencyScore = sc.consistency_score ?? 0;

    return (
      <FactShieldScoreBadge
        role={role as "student" | "teacher"}
        entailment={entailment}
        consistency={consistency}
        confidence={confidence}
        trustScore={trustScore}
        trustTier={trustTier}
        entailmentScore={entailmentScore}
        consistencyScore={consistencyScore}
        sourceRef={sourceRef}
      />
    );
  };


  const activeLogs = getActiveLogs();

  return (
    <div className="app-container">
      <ToastContainer />
      {/* LEFT SIDEBAR (240px) */}
      <aside className="gemini-sidebar">
        <div className="sidebar-header">
          <div className="logo-section">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--color-accent)', marginRight: '0.4rem', flexShrink: 0 }}>
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <div>
              <h1 className="header-title">FactShield Edu</h1>
              <p className="header-subtitle">Active Learning Assistant</p>
            </div>
          </div>

          {/* Role Switcher Sliding Switch */}
          <div title={role === "student" ? "Student: concept help, problem guidance, quizzes, submission checking" : "Teacher: grading, exam creation, adaptive feedback, learning insights"}>
            <div className="role-switcher-container" onClick={() => handleRoleChangeClick(role === "student" ? "teacher" : "student")}>
              <div className={`role-slider-bg ${role}`} />
              <button type="button" className={`role-switcher-btn ${role === "student" ? "active" : ""}`}>Student</button>
              <button type="button" className={`role-switcher-btn ${role === "teacher" ? "active" : ""}`}>Teacher</button>
            </div>
            <p style={{ fontSize: "10.5px", color: "var(--color-text-secondary)", margin: "0.3rem 0 0", textAlign: "center", lineHeight: 1.4 }}>
              {role === "student"
                ? "Concept guide · Problem help · Quizzes · Validator"
                : "Grader · Exam builder · Feedback · Insights"}
            </p>
          </div>
        </div>

        <div className="sidebar-content">
          {/* Document list context selector */}
          <div className="sidebar-nav-section">
            <span className="sidebar-nav-title">ACTIVE KNOWLEDGE BASES</span>
            <div style={{ marginTop: "0.5rem" }}>
              {documents.length > 0 ? (
                <div className="sidebar-doc-list">
                  {documents.map((doc) => {
                    const isActive = activeDocIds.includes(doc.id);
                    return (
                      <div
                        key={doc.id}
                        className={`sidebar-doc-item ${isActive ? "active" : ""}`}
                        onClick={() => toggleActiveDoc(doc.id)}
                      >
                        <div className="doc-item-left">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                          <span className="doc-filename" title={doc.filename}>
                            {doc.filename}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="doc-delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDoc(doc.id, doc.filename);
                          }}
                          title="Delete document"
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="no-docs-text">
                  No files indexed.
                </div>
              )}
            </div>
          </div>

          {/* History Toggle Accordion */}
          <div className="sidebar-nav-section">
            <div className={`history-header-row ${showHistory ? "open" : ""}`} onClick={() => setShowHistory(!showHistory)}>
              <div className="history-header-left">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                <span>History</span>
              </div>
              <svg className={`chevron-icon ${showHistory ? "rotated" : ""}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
            
            <div className={`history-sessions-list ${showHistory ? "expanded" : ""}`}>
              <div className="new-chat-container">
                <button type="button" className="new-chat-btn" onClick={() => startNewChat()} title="New Chat">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                  <span>New chat</span>
                </button>
              </div>

              {sessions.length > 0 ? (
                <div className="history-sessions-scroll">
                  {sessions.map((s) => {
                    const isActive = s.id === currentSessionId;
                    const sessionRole = s.role || (role === "student" ? "Student" : "Teacher");
                    const sessionMode = s.mode || getToolDisplayName(activeTool);
                    const isStudentRole = sessionRole === "Student";
                    
                    return (
                      <div
                        key={s.id}
                        className={`history-session-item ${isActive ? "active" : ""}`}
                        onClick={() => restoreSession(s)}
                      >
                        <div className="session-item-content">
                          <div className="session-meta-row" style={{ display: "flex", alignItems: "center", gap: "0.25rem", marginBottom: "0.25rem" }}>
                            <span className={`role-pill-tag ${isStudentRole ? "student-pill" : "teacher-pill"}`}>
                              {sessionRole}
                            </span>
                            <span style={{ color: "var(--color-text-muted)", fontSize: "11px" }}>·</span>
                            <span className="session-mode-label">
                              {sessionMode}
                            </span>
                          </div>
                          <span className="session-title" style={{ fontSize: "12px", fontWeight: 400 }}>
                            {s.title}
                          </span>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.25rem" }}>
                          <span className="session-time" style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>
                            {formatRelativeTime(s.timestamp)}
                          </span>
                          <button
                            type="button"
                            className="session-delete-btn"
                            onClick={(e) => deleteSession(e, s.id)}
                            title="Delete session"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="no-history-text">No active history</div>
              )}
            </div>
          </div>

          {/* Workspace Tools list */}
          <div className="sidebar-nav-section">
            <span className="sidebar-nav-title">WORKSPACE TOOLS</span>
            <nav className="sidebar-nav" style={{ marginTop: "0.5rem" }}>
              {role === "student" ? (
                <>
                  <button onClick={() => handleToolClick("concept-guide")} className={`nav-item ${activeTool === "concept-guide" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Concept Guide</span>
                      <span className="nav-item-subtitle">Verified explanation from your document</span>
                    </div>
                  </button>
                  <button onClick={() => handleToolClick("problem-navigator")} className={`nav-item ${activeTool === "problem-navigator" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Problem Navigator</span>
                      <span className="nav-item-subtitle">Guided approach without giving the answer</span>
                    </div>
                  </button>
                  <button onClick={() => handleToolClick("submission-validator")} className={`nav-item ${activeTool === "submission-validator" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <polyline points="10 9 9 9 8 9" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Submission Validator</span>
                      <span className="nav-item-subtitle">Sentence-by-sentence essay audit</span>
                    </div>
                  </button>
                  <button onClick={() => handleToolClick("quiz-generator")} className={`nav-item ${activeTool === "quiz-generator" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M9 9h6v6H9z" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Quiz Generator</span>
                      <span className="nav-item-subtitle">Generate topic-based quizzes like chat-style requests</span>
                    </div>
                  </button>
                </>
              ) : (
                <>
                  <button onClick={() => handleToolClick("assignment-grader")} className={`nav-item ${activeTool === "assignment-grader" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Assignment Grader</span>
                      <span className="nav-item-subtitle">Objective, automated student assessment</span>
                    </div>
                  </button>
                  <button onClick={() => handleToolClick("exam-generator")} className={`nav-item ${activeTool === "exam-generator" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <line x1="9" y1="9" x2="15" y2="9" />
                      <line x1="9" y1="13" x2="15" y2="13" />
                      <line x1="9" y1="17" x2="15" y2="17" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Exam Generator</span>
                      <span className="nav-item-subtitle">Create complete exams from your material</span>
                    </div>
                  </button>
                  <button onClick={() => handleToolClick("adaptive-feedback")} className={`nav-item ${activeTool === "adaptive-feedback" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Adaptive Feedback</span>
                      <span className="nav-item-subtitle">Proactive micro-lesson for failed concepts</span>
                    </div>
                  </button>
                  <button onClick={() => handleToolClick("learning-insights")} className={`nav-item ${activeTool === "learning-insights" ? "active" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mode-icon">
                      <line x1="18" y1="20" x2="18" y2="10" />
                      <line x1="12" y1="20" x2="12" y2="4" />
                      <line x1="6" y1="20" x2="6" y2="14" />
                    </svg>
                    <div className="nav-item-content">
                      <span className="nav-item-title">Learning Insights</span>
                      <span className="nav-item-subtitle">Class-wide performance analytics</span>
                    </div>
                  </button>
                </>
              )}
            </nav>
          </div>
        </div>

        {/* BOTTOM USER ROW */}
        <div className="sidebar-footer" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="user-profile-row">
            <div className="user-profile-avatar">
              {role === "student" ? "ST" : "TE"}
            </div>
            <div className="user-profile-info">
              <span className="user-profile-name">{role === "student" ? "Student Account" : "Teacher Account"}</span>
              <span className="user-profile-role">{role === "student" ? "Student" : "Instructor"}</span>
            </div>
          </div>
        </div>
      </aside>

      {/* RIGHT SIDE CHAT / WORKSPACE */}
      <main className="chat-workspace">
        {activeTool === "dashboard" ? (
          <div style={{ padding: "3rem", overflowY: "auto", flexGrow: 1 }}>
            <div className="gemini-card" style={{ maxWidth: "900px", margin: "0 auto" }}>
              <h2>Low-Confidence Review Dashboard</h2>
              <p style={{ color: "var(--color-text-secondary)", marginBottom: "2rem", fontSize: "0.9rem" }}>
                Submissions that triggered borderline evaluations (score between 40% and 60%) requiring manual audit.
              </p>
              {dashboardStatus && !dashboardStatus.includes("Done") && (
                <div className="status-message loading">{dashboardStatus}</div>
              )}
              {flaggedGrades.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                  {flaggedGrades.map((g) => (
                    <div key={g.grade_id} className="passage-card" style={{ fontStyle: "normal", borderLeftColor: "var(--color-warning)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "0.75rem" }}>
                        <span><strong>Evaluation ID:</strong> {g.grade_id}</span>
                        <span><strong>Timestamp:</strong> {new Date(g.created_at).toLocaleString()}</span>
                      </div>
                      <p style={{ marginBottom: "0.75rem" }}><strong>Student Answer:</strong> "{g.student_answer}"</p>
                      <p style={{ marginBottom: "1rem" }}>
                        <strong>Overall Score:</strong> <span style={{ color: "var(--color-warning)", fontWeight: 500 }}>{(g.overall_score * 100).toFixed(0)}%</span>
                      </p>
                      <div className="rubric-table-wrapper">
                        <table className="rubric-table">
                          <thead>
                            <tr>
                              <th>Rubric Point</th>
                              <th>Fact Score</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {g.rubric_breakdown.map((b, bIdx) => (
                              <tr key={bIdx}>
                                <td>{b.point}</td>
                                <td style={{ fontFamily: "var(--font-mono)" }}>{(b.score * 100).toFixed(0)}%</td>
                                <td className={b.passed ? "pass" : b.needs_review ? "review" : "fail"}>
                                  {b.passed ? "Pass" : b.needs_review ? "Review" : "Fail"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                dashboardStatus.includes("Done") && (
                  <div className="status-message success">No evaluations require manual audit at this time.</div>
                )
              )}
            </div>
          </div>
        ) : (
          /* CHAT STREAM INTERFACE */
          <>
            {/* Header bar (44px) */}
            <header className="chat-header-bar">
              <div className="chat-header-left">
                <span className="active-mode-title">
                  {activeTool === "grounding" ? "Solver" :
                   activeTool === "challenge" ? "Quiz me" :
                   activeTool === "selfcheck" ? "Check" :
                   activeTool === "source" ? "Find" :
                   activeTool === "summary" ? "Summarise" :
                   activeTool === "grader" ? "Grade an answer" :
                   activeTool === "explainer" ? "Explain a concept" :
                   activeTool === "generator" ? "Generate a test" :
                   "Student insights"}
                </span>
              </div>
              <div className="chat-header-right">
                <div className="pipeline-dots-container">
                  <span className="pipeline-dot-wrapper">
                    <span className="pipeline-dot green" />
                    <span className="pipeline-dot-label">Pass</span>
                  </span>
                  <span className="pipeline-dot-wrapper">
                    <span className="pipeline-dot amber" />
                    <span className="pipeline-dot-label">Warning</span>
                  </span>
                  <span className="pipeline-dot-wrapper">
                    <span className="pipeline-dot red" />
                    <span className="pipeline-dot-label">Fail</span>
                  </span>
                </div>
              </div>
            </header>

            {/* Scrollable Message List */}
            <div className="message-stream" ref={messageStreamRef} onScroll={handleScroll}>
              
              {/* ─── Empty Chat State (three context-aware branches) ──────── */}
              {activeLogs.length <= 1 && activeLogs[0]?.id === "welcome" ? (
                (() => {
                  const hasDoc = activeDocIds.length > 0 && documents.length > 0;

                  if (!hasDoc) {
                    // STATE 1 — No document uploaded
                    return (
                      <div className="empty-chat-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="empty-shield-icon">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        <h2 className="empty-chat-title">FactShield Edu</h2>
                        <p className="empty-chat-subtitle">
                          Upload your course document to get started
                        </p>
                        <label
                          htmlFor="chat-file-upload"
                          className="empty-upload-btn"
                          title="Upload document"
                        >
                          📎 Upload document
                        </label>
                      </div>
                    );
                  }

                  const heading = role === "student" ? "What do you need help with?" : "What would you like to do?";

                  return (
                    <div className="empty-chat-state">
                      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="empty-shield-icon">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      </svg>
                      <h2 className="empty-chat-title">{heading}</h2>
                      <p className="empty-chat-subtitle">Sources: ArXiv · Active Knowledge Base · Web Search</p>
                    </div>
                  );
                })()
              ) : (
                /* Regular messages bubble list */
                activeLogs.map((msg) => (
                  <div key={msg.id} className={`message-row ${msg.sender}`}>
                    {msg.sender === "ai" ? (
                      <div className="message-ai-wrapper">
                        <div className="message-ai-header">
                          <div className="avatar-container avatar-ai">FS</div>
                          <span className="message-ai-name">FactShield Edu</span>
                        </div>
                        <div className="message-ai-content">
                          {(() => {
                            const scores = msg.data?.scores || msg.data?.explainer?.scores || msg.data?.summary?.scores || msg.data?.grounding?.scores;
                            if (scores?.fallback_type === 'general') {
                              return (
                                <div className="fallback-banner general-knowledge">
                                  <span className="fallback-icon">🧠</span>
                                  <strong>General Knowledge</strong> (Not found in uploaded document)
                                </div>
                              );
                            } else if (scores?.fallback_type === 'academic') {
                              return (
                                <div className="fallback-banner academic-search" style={{ backgroundColor: "#e8f4fd", color: "#1a5e9a", padding: "8px 12px", borderRadius: "6px", marginBottom: "8px", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px" }}>
                                  <span className="fallback-icon">📚</span>
                                  <strong>Academic Search</strong> (Sourced from ArXiv research papers)
                                </div>
                              );
                            } else if (scores?.fallback_type === 'copilot') {
                              return (
                                <div className="fallback-banner copilot" style={{ backgroundColor: "#fdf4ff", color: "#86198f", padding: "8px 12px", borderRadius: "6px", marginBottom: "8px", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px", border: "1px solid #f0abfc" }}>
                                  <span className="fallback-icon">🤖</span>
                                  <strong>AI Knowledge Base</strong>
                                </div>
                              );
                            } else if (scores?.fallback_type === 'web') {
                              return (
                                <div className="fallback-banner web-search">
                                  <span className="fallback-icon">🌐</span>
                                  <strong>Web Search</strong> (Sourced from live internet)
                                </div>
                              );
                            } else if (scores?.fallback_type === 'refusal') {
                              return (
                                <div className="fallback-banner refusal" style={{ backgroundColor: "#f3f4f6", color: "#4b5563", padding: "8px 12px", borderRadius: "6px", marginBottom: "8px", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px", border: "1px solid #d1d5db" }}>
                                  <span className="fallback-icon">🛡️</span>
                                  <strong>Strict Mode</strong> (No Verifiable Sources Found)
                                </div>
                              );
                            }
                            return null;
                          })()}
                          {msg.data?.quiz && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <QuizGeneratorPanel quiz={msg.data.quiz} />
                            </div>
                          )}
                          <div className="message-text-content">
                            {!msg.data?.exam && !msg.data?.quiz && (
                              msg.data?.apiResponse?.mode === "submission-validator" || msg.text.includes("Submission Audit")
                                ? <div style={{ marginTop: "0.5rem" }}><SubmissionAuditPanel text={msg.text} /></div>
                                : <div className="markdown-body">
                                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{msg.text}</ReactMarkdown>
                                  </div>
                            )}
                          </div>

                          {/* Rich Data Display Blocks */}

                          {msg.data?.challenge && msg.text !== msg.data.challenge.feedback && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="feedback-text">
                                <div className="markdown-body">
                                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{msg.data.challenge.feedback}</ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          )}

                          {msg.data?.selfcheck && (
                            <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                              {(msg.data.selfcheck.sentence_checks || []).map((item: any, idx: number) => (
                                <div key={idx} className="sentence-audit-row">
                                  <span className={`sentence-audit-dot ${item.supported ? "pass" : "fail"}`} />
                                  <div className="sentence-audit-text">
                                    <span className="sentence-body">"{item.sentence}."</span>
                                    <span className="sentence-meta"> ({item.supported ? "Supported" : "Inconsistent"})</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {msg.data?.sourceHunter?.cited_passage && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="cited-passage-card">"{msg.data.sourceHunter.cited_passage}"</div>
                            </div>
                          )}

                          {msg.data?.summary && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="winning-summary-text">
                                <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", color: "#333" }}>Optimal Summary</h4>
                                <div className="markdown-body">
                                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{msg.data.summary.winner.text}</ReactMarkdown>
                                </div>
                              </div>
                              {msg.data.summary.all_candidates?.length > 1 && (
                                <div className="alternative-summaries" style={{ marginTop: "1rem", borderTop: "1px solid #eee", paddingTop: "0.5rem" }}>
                                  <h5 style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "#666" }}>Alternative Candidates:</h5>
                                  {msg.data.summary.all_candidates.slice(1).map((cand: any, idx: number) => (
                                    <div key={idx} style={{ marginBottom: "0.5rem", padding: "0.5rem", background: "#f8f9fa", borderRadius: "4px", border: "1px solid #e9ecef" }}>
                                      <div style={{ display: "flex", gap: "12px", marginBottom: "6px", fontSize: "0.75rem", fontWeight: "600" }}>
                                        <span style={{ color: cand.grounding >= 0.5 ? "#2e7d32" : "#d32f2f" }}>Entailment: {cand.grounding >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: cand.consistency >= 0.5 ? "#2e7d32" : "#d32f2f" }}>SelfCheck: {cand.consistency >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: "#1976d2" }}>Token Prob: {(cand.confidence * 100).toFixed(0)}%</span>
                                      </div>
                                      <div className="markdown-body" style={{ fontSize: "0.8rem", color: "#555" }}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{cand.text}</ReactMarkdown>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {msg.data?.grade && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="rubric-table-wrapper">
                                <table className="rubric-table">
                                  <thead>
                                    <tr>
                                      <th>Rubric Fact</th>
                                      <th>Score</th>
                                      <th>Status</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {msg.data.grade.breakdown.map((b: any, bIdx: number) => (
                                      <tr key={bIdx}>
                                        <td>{b.point}</td>
                                        <td>{(b.score * 100).toFixed(0)}%</td>
                                        <td className={b.passed ? "pass" : b.needs_review ? "review" : "fail"}>
                                          {b.passed ? "Pass" : b.needs_review ? "Review" : "Fail"}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {msg.data?.explainer && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="explanation-text">
                                <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", color: "#333" }}>Optimal Explanation</h4>
                                <div className="markdown-body">
                                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{msg.data.explainer.winner.text}</ReactMarkdown>
                                </div>
                              </div>
                              {msg.data.explainer.all_candidates?.length > 1 && (
                                <div className="alternative-summaries" style={{ marginTop: "1rem", borderTop: "1px solid #eee", paddingTop: "0.5rem" }}>
                                  <h5 style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "#666" }}>Alternative Explanations:</h5>
                                  {msg.data.explainer.all_candidates.slice(1).map((cand: any, idx: number) => (
                                    <div key={idx} style={{ marginBottom: "0.5rem", padding: "0.5rem", background: "#f8f9fa", borderRadius: "4px", border: "1px solid #e9ecef" }}>
                                      <div style={{ display: "flex", gap: "12px", marginBottom: "6px", fontSize: "0.75rem", fontWeight: "600" }}>
                                        <span style={{ color: cand.grounding >= 0.5 ? "#2e7d32" : "#d32f2f" }}>Entailment: {cand.grounding >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: cand.consistency >= 0.5 ? "#2e7d32" : "#d32f2f" }}>SelfCheck: {cand.consistency >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: "#1976d2" }}>Token Prob: {(cand.confidence * 100).toFixed(0)}%</span>
                                      </div>
                                      <div className="markdown-body" style={{ fontSize: "0.8rem", color: "#555" }}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={MD_COMPONENTS}>{cand.text}</ReactMarkdown>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {msg.data?.testItems && (
                            <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                              {(msg.data.testItems.test_items || []).map((item: any, idx: number) => (
                                <div key={idx} className="practice-question-row">
                                  <div className="question-title">Question {idx + 1}: {item.question}</div>
                                  <div className="answer-text">Correct Answer: {item.correct_answer}</div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Reusable FactShield segmented score block */}
                          {renderScoreBlock(msg)}
                        </div>
                      </div>
                    ) : (
                      <div className="message-user-wrapper">
                        <div className="message-user-bubble">
                          {msg.text}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}

              {isTyping && (
                <div className="message-row ai">
                  <div className="message-ai-wrapper">
                    <div className="message-ai-header">
                      <div className="avatar-container avatar-ai">FS</div>
                      <span className="message-ai-name">FactShield Edu</span>
                    </div>
                    <div className="message-ai-content" style={{ paddingTop: "0.25rem" }}>
                      {/* Stage label */}
                      <div style={{
                        fontSize: "12px", color: "var(--color-text-secondary)",
                        marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.4rem",
                      }}>
                        <span style={{
                          width: 7, height: 7, borderRadius: "50%", background: "#3b82f6",
                          display: "inline-block", animation: "pulse 1.2s ease-in-out infinite",
                        }} />
                        {loadingStage}
                      </div>
                      <div className="skeleton-loader">
                        <div />
                        <div />
                        <div />
                        <div />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messageEndRef} />
            </div>

            {/* Scroll bottom floating button */}
            {showScrollBottom && (
              <button
                type="button"
                className="scroll-bottom-floating-btn"
                onClick={scrollToBottom}
              >
                ↓ scroll to bottom
              </button>
            )}

            {/* Fixed Chat Input form at bottom */}
            <div className="chat-input-panel">
              {/* Quick Reply Chips */}
              <div className="quick-reply-chips-row">
                {getQuickReplies(activeTool).map((chipText) => (
                  <button
                    key={chipText}
                    type="button"
                    className="quick-reply-chip"
                    onClick={() => {
                      setCurrentInput(chipText + " ");
                      setTimeout(() => inputRef.current?.focus(), 0);
                    }}
                    disabled={!hasActiveDocs || isTyping}
                  >
                    {chipText}
                  </button>
                ))}
              </div>

              {/* Student answer text extraction banner */}
              {uploadedStudentFileName && (
                <div className="teacher-extraction-banner">
                  <span>Student answer loaded from <strong>{uploadedStudentFileName}</strong> — review below before grading:</span>
                  <button
                    type="button"
                    className="banner-close-btn"
                    onClick={() => setUploadedStudentFileName("")}
                  >
                    ×
                  </button>
                </div>
              )}

              <form onSubmit={handleChatSubmit} className={`chat-input-wrapper ${!hasActiveDocs ? "disabled" : ""}`}>
                <label htmlFor="chat-file-upload" className="chat-attach-btn" title="Attach document">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </label>
                <input
                  id="chat-file-upload"
                  type="file"
                  style={{ display: "none" }}
                  accept=".pdf,.ppt,.pptx,.doc,.docx,.txt,.csv,.xls,.xlsx"
                  onChange={async (e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      const file = e.target.files[0];
                      if (role === "teacher" && activeTool === "grader") {
                        await handleStudentAnswerUpload(file);
                      } else {
                        await uploadFileDirectly(file);
                      }
                      e.target.value = "";
                    }
                  }}
                />
                <textarea
                  ref={inputRef}
                  className="chat-input-textarea"
                  value={currentInput}
                  disabled={!hasActiveDocs || isTyping}
                  onChange={(e) => setCurrentInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleChatSubmit(e);
                    }
                  }}
                  placeholder={
                    !hasActiveDocs
                      ? "Upload a document first…"
                      : role === "teacher"
                      ? "Type or paste a student's answer to grade…"
                      : "Ask anything about your document…"
                  }
                />
                <button type="submit" className="chat-action-btn chat-send-btn" disabled={!currentInput.trim() || !hasActiveDocs || isTyping}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5" />
                    <polyline points="5 12 12 5 19 12" />
                  </svg>
                </button>
              </form>
              <div className="chat-footer-text">
                FactShield leverages MiniCheck, SelfCheckGPT, and Token Probability Analysis to detect hallucinations.
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
