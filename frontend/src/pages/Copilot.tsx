import { useState } from "react";
import { api } from "../lib/api";
import { Card } from "../components/ui";

const SUGGESTIONS = [
  "What is most at risk right now?",
  "Why might checkout be failing?",
  "Summarize all active incidents and their business impact.",
  "What should I do first?",
];

export default function Copilot() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = async (question: string) => {
    if (!question.trim()) return;
    setQ(question);
    setBusy(true);
    setAnswer(null);
    try {
      setAnswer(await api.copilot(question));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-slate-100">Ops Copilot</h1>
      <p className="mb-6 text-sm text-slate-400">
        Ask anything about the live system — answered from current telemetry, predictions,
        and incidents.
      </p>

      <Card className="mb-4">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask(q)}
            placeholder="Ask the copilot…"
            className="flex-1 rounded-lg border border-ink-600 bg-ink-700 px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent"
          />
          <button
            onClick={() => ask(q)}
            disabled={busy}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink-900 hover:bg-accent/90 disabled:opacity-50"
          >
            {busy ? "Thinking…" : "Ask"}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="rounded-full border border-ink-600 bg-ink-700 px-3 py-1 text-xs text-slate-300 hover:border-accent/50"
            >
              {s}
            </button>
          ))}
        </div>
      </Card>

      {answer && (
        <Card title="Answer">
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">
            {answer}
          </pre>
        </Card>
      )}
    </div>
  );
}
