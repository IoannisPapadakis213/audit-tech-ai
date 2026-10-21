import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");
const SUGGESTIONS = [
  "Which are the 3 riskiest journals?",
  "How many journals are high risk?",
  "What does the Benford analysis show?",
];

const fmt = (v) => (v === undefined || v === null ? "…" : Number(v).toLocaleString("el-GR"));
const clean = (t = "") => t.replace(/\*\*(.*?)\*\*/g, "$1").replace(/^\s*\*\s+/gm, "• ");

function useCountUp(target, ms = 1600, delay = 0) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (target === undefined || target === null) return;
    let raf;
    const start = performance.now() + delay;
    const tick = (now) => {
      const p = Math.min(Math.max((now - start) / ms, 0), 1);
      setV(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms, delay]);
  return v;
}

export default function App() {
  const [intro, setIntro] = useState(true);
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(false);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => setIntro(false), 5600);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/stats`).then((r) => r.json()),
      fetch(`${API}/anomalies?limit=19`).then((r) => r.json()),
    ])
      .then(([s, a]) => { setStats(s); setRows(a); })
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
  }, [chat, loading]);

  async function ask(q) {
    if (!q.trim() || loading) return;
    setQuestion("");
    setLoading(true);
    setChat((c) => [...c, { role: "user", text: q }]);
    try {
      const r = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await r.json();
      setChat((c) => [...c, { role: "agent", text: clean(data.answer), tools: data.tools_used }]);
    } catch {
      setChat((c) => [...c, { role: "agent", text: "The API is not reachable." }]);
    }
    setLoading(false);
  }

  const maxScore = Math.max(1, ...rows.map((r) => r.risk_score));
  const reconciled = stats && stats.gl_vs_tb_difference === 0;

  return (
    <>
      <div className="backdrop"><div className="orb o1" /><div className="orb o2" /><div className="grid-bg" /></div>

      {intro && (
        <div className="intro" onClick={() => setIntro(false)}>
          <div className="intro-line l1">Ioannis Papadakis presents</div>
          <div className="intro-title">AUDIT <span>TECH</span> AI</div>
          <div className="intro-line l2">Prepared for <b>Deloitte Greece</b> · Assurance · Data Analyst</div>
          <div className="intro-scan" />
          <div className="intro-skip">click to skip</div>
        </div>
      )}

      <main className={`app ${intro ? "waiting" : "reveal"}`}>
        <header className="hero rise" style={{ "--d": "0s" }}>
          <div>
            <div className="eyebrow"><span className="dot" /> Journal Entry Testing · ISA 240 · FY2025</div>
            <h1>Every journal tested.<br /><em>Only the ones that matter</em> surfaced.</h1>
          </div>
          <div className="badge">Prepared for Deloitte Greece<br /><small>Assurance · Data Analyst</small></div>
        </header>

        {error && <div className="alert">Start the backend: <code>uvicorn audit_ai.api:app --reload</code></div>}

        <section className="kpis">
          <Kpi i={0} label="Journals tested" value={stats?.total_journals} />
          <Kpi i={1} label="High-risk journals" value={stats?.high_risk_journals} danger />
          <Kpi i={2} label="Ledger lines" value={stats?.total_lines} />
          <Kpi i={3} label="GL ↔ TB difference" value={stats?.gl_vs_tb_difference}
               sub={reconciled ? "reconciled ✓" : stats ? "investigate" : ""} ok={reconciled} />
        </section>

        <div className="layout">
          <div className="col">
            <section className="panel rise" style={{ "--d": ".5s" }}>
              <h2>Detection funnel</h2>
              {[
                ["Ledger lines tested", stats?.total_lines, 100],
                ["Journals scored by rules + ML", stats?.total_journals, 70],
                ["Flagged for auditor review", stats?.high_risk_journals, 24],
              ].map(([label, v, w], i) => (
                <div className="stage" key={label}>
                  <div className={`bar ${i === 2 ? "hot" : ""}`} style={{ "--w": `${w}%`, "--d": `${0.8 + i * 0.3}s` }}>
                    <span>{label}</span><b>{fmt(v)}</b>
                  </div>
                </div>
              ))}
            </section>

            <section className="panel rise" style={{ "--d": ".7s" }}>
              <h2>High-risk journals <small>ranked by risk score</small></h2>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Journal</th><th>Posted by</th><th>Date</th><th>Risk</th><th className="num">Amount €</th></tr></thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={r.journal_id} style={{ "--d": `${1 + i * 0.05}s` }}>
                        <td className="mono">{r.journal_id}</td>
                        <td>{r.created_by}</td>
                        <td className="mono">{r.posting_date}</td>
                        <td>
                          <div className="risk"><i style={{ "--w": `${(r.risk_score / maxScore) * 100}%` }} /><b>{r.risk_score}</b></div>
                        </td>
                        <td className="num mono">{fmt(r.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <section className="panel chat rise" style={{ "--d": ".9s" }}>
            <h2><span className="pulse" /> Audit agent</h2>
            <div className="messages" ref={boxRef}>
              {chat.length === 0 && (
                <div className="empty">
                  <p>Ask about the results. The agent calls read-only tools — it never guesses.</p>
                  <div className="chips">
                    {SUGGESTIONS.map((s) => <button key={s} onClick={() => ask(s)}>{s}</button>)}
                  </div>
                </div>
              )}
              {chat.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <div>{m.text}</div>
                  {m.tools?.length > 0 && <small>🔧 {m.tools.join(", ")}</small>}
                </div>
              ))}
              {loading && <div className="msg agent typing"><i /><i /><i /></div>}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); ask(question); }}>
              <input value={question} onChange={(e) => setQuestion(e.target.value)}
                     placeholder="Ask the audit agent…" maxLength={500} />
              <button disabled={loading}>Send</button>
            </form>
            <p className="fine">Read-only tools · aggregates only · conclusions stay with the auditor</p>
          </section>
        </div>

        <footer>Independent portfolio project by Ioannis Papadakis · synthetic data · not affiliated with or endorsed by Deloitte</footer>
      </main>
    </>
  );
}

function Kpi({ i, label, value, danger, ok, sub }) {
  const v = useCountUp(value, 1600, 300 + i * 150);
  return (
    <div className={`kpi rise ${danger ? "danger" : ""} ${ok ? "ok" : ""}`} style={{ "--d": `${0.15 + i * 0.1}s` }}>
      <span>{label}</span>
      <strong>{value === undefined ? "…" : fmt(Math.round(v))}</strong>
      {sub && <small>{sub}</small>}
    </div>
  );
}