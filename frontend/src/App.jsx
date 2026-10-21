import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

const SUGGESTIONS = [
  "Which are the 3 riskiest journals?",
  "Who posted the most high-risk journals?",
  "What does the Benford analysis show?",
];

const STEPS = [
  { n: "01", tag: "ISA 500", title: "Completeness first",
    text: "The ledger is rolled forward to the trial balance. If they do not reconcile, the run stops. Invalid lines are quarantined, never deleted or auto-corrected." },
  { n: "02", tag: "ISA 240", title: "Risk indicators",
    text: "Every line is tagged with fraud-risk characteristics: weekend, holiday and after-hours posting, proximity to year-end, round amounts, manual entry." },
  { n: "03", tag: "Known risks", title: "Ten SQL rules",
    text: "Unauthorised posters, the same user creating and approving, manual entries in the final days of the year, and other established red flags." },
  { n: "04", tag: "Unknown risks", title: "Statistics and machine learning",
    text: "Robust z-scores find amounts unusual for their account. An Isolation Forest finds journals unusual in combination, patterns no rule anticipated." },
  { n: "05", tag: "Evidence", title: "Scored, explained, logged",
    text: "Weighted rules produce one score per journal with its reasons. Every run is logged with SHA-256 hashes so results can be reproduced." },
];

const SAFEGUARDS = [
  ["Read-only tools", "The assistant can only call get_stats, get_anomalies and get_benford. Nothing can be changed or deleted."],
  ["Data minimisation", "It receives aggregates and the high-risk list, never the full general ledger."],
  ["Controlled execution", "Tools are executed by application code, not by the model. Unknown tools are refused and result sizes are capped."],
  ["Traceability", "Every answer records which tools were used to produce it."],
  ["Judgement stays human", "The assistant flags risks for review. It is instructed never to conclude that fraud has occurred."],
  ["EU hosting", "The application runs on Azure in France Central. Keys live in cloud configuration, never in code."],
];

const fmt = (v) => (v === undefined || v === null ? "…" : Number(v).toLocaleString("el-GR"));
const clean = (t = "") => t.replace(/\*\*(.*?)\*\*/g, "$1").replace(/^\s*\*\s+/gm, "• ");
const human = (r) => r.replace(/_/g, " ");

function useInView(threshold = 0.15) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setSeen(true); io.disconnect(); }
    }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [seen, threshold]);
  return [ref, seen];
}

function Reveal({ children, delay = 0, className = "" }) {
  const [ref, seen] = useInView();
  return (
    <div ref={ref} className={`reveal ${seen ? "in" : ""} ${className}`} style={{ transitionDelay: `${delay}s` }}>
      {children}
    </div>
  );
}

function useCountUp(target, active, ms = 1800) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!active || target === undefined || target === null) return;
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / ms, 1);
      setV(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active, ms]);
  return v;
}

function LedgerCanvas() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas.getContext("2d");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const colW = 120, lineH = 22;
    let w = 0, h = 0, drops = [], raf;
    const amount = () =>
      Math.floor(10 ** (1 + Math.random() * 4.6)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      drops = Array.from({ length: Math.ceil(w / colW) }, () => ({ y: Math.random() * h, speed: 0.3 + Math.random(), acc: 0 }));
    }

    function frame() {
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = "rgba(0,0,0,0.10)";
      ctx.fillRect(0, 0, w, h);
      ctx.globalCompositeOperation = "source-over";
      ctx.font = '12px ui-monospace, "SF Mono", Menlo, monospace';
      drops.forEach((d, i) => {
        d.acc += d.speed;
        if (d.acc < 5) return;
        d.acc = 0;
        d.y += lineH;
        const x = i * colW + 10;
        const flagged = Math.random() < 0.012;
        ctx.fillStyle = flagged ? "rgba(255,93,108,0.95)" : `rgba(150,190,255,${0.25 + Math.random() * 0.35})`;
        ctx.fillText(amount(), x, d.y);
        if (flagged) {
          ctx.strokeStyle = "rgba(255,93,108,0.75)";
          ctx.strokeRect(x - 6, d.y - 15, colW - 16, 21);
        }
        if (d.y > h + 30) { d.y = -20; d.speed = 0.3 + Math.random(); }
      });
      raf = requestAnimationFrame(frame);
    }

    resize();
    if (!reduce) frame();
    window.addEventListener("resize", resize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={ref} className="ledger-canvas" aria-hidden="true" />;
}

function Stat({ value, label, accent, active, delay }) {
  const v = useCountUp(value, active);
  return (
    <div className={`stat ${accent || ""}`} style={{ transitionDelay: `${delay}s` }}>
      <strong>{value === undefined ? "…" : fmt(Math.round(v))}</strong>
      <span>{label}</span>
    </div>
  );
}

function StatBand({ stats }) {
  const [ref, seen] = useInView(0.3);
  const active = seen && !!stats;
  return (
    <div ref={ref} className={`stat-band reveal ${seen ? "in" : ""}`}>
      <Stat value={stats?.total_lines} label="Ledger lines tested" active={active} delay={0} />
      <Stat value={stats?.total_journals} label="Journals scored" active={active} delay={0.1} />
      <Stat value={stats?.high_risk_journals} label="Flagged for review" accent="danger" active={active} delay={0.2} />
      <Stat value={stats?.gl_vs_tb_difference} label="GL vs TB difference" accent="ok" active={active} delay={0.3} />
    </div>
  );
}

function FragmentRow({ r, maxScore, open, onToggle }) {
  return (
    <>
      <tr className={`row ${open ? "open" : ""}`} onClick={onToggle}>
        <td className="mono">{r.journal_id}</td>
        <td>{r.created_by}</td>
        <td className="mono">{r.posting_date}</td>
        <td><div className="risk"><i style={{ width: `${(r.risk_score / maxScore) * 100}%` }} /><b>{r.risk_score}</b></div></td>
        <td className="num mono">{fmt(r.amount)}</td>
      </tr>
      {open && (
        <tr className="why">
          <td colSpan={5}>
            <span>Why flagged:</span>
            {(r.rules || []).map((x) => <em key={x}>{human(x)}</em>)}
          </td>
        </tr>
      )}
    </>
  );
}

export default function App() {
  const [intro, setIntro] = useState(true);
  const [scrolled, setScrolled] = useState(false);
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(false);
  const [openRow, setOpenRow] = useState(null);
  const [openSafe, setOpenSafe] = useState(0);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => setIntro(false), 4800);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
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

  function goToAgent() {
    document.getElementById("agent")?.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => inputRef.current?.focus(), 700);
  }

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
      setChat((c) => [...c, { role: "agent", text: "The service is waking up. Please try again in a few seconds." }]);
    }
    setLoading(false);
  }

  const maxScore = Math.max(1, ...rows.map((r) => r.risk_score));

  return (
    <>
      {intro && (
        <div className="intro" onClick={() => setIntro(false)}>
          <div className="intro-line l1">Ioannis Papadakis presents</div>
          <div className="intro-title">AUDIT <span>TECH</span> AI</div>
          <div className="intro-line l2">Prepared for <b>Deloitte Greece</b> · Assurance · Data Analyst</div>
          <div className="intro-scan" />
          <div className="intro-skip">click to skip</div>
        </div>
      )}

      <nav className={`nav ${scrolled ? "solid" : ""}`}>
        <a href="#top" className="brand">Audit<span>Tech</span>AI</a>
        <div className="links">
          <a href="#approach">Approach</a>
          <a href="#results">Results</a>
          <a href="#agent">Agent</a>
          <a href="#safeguards">Safeguards</a>
        </div>
        <button className="btn small" onClick={goToAgent}>Ask the agent</button>
      </nav>

      <header id="top" className={`hero ${intro ? "" : "go"}`}>
        <video className="hero-video" src="/hero.mp4" autoPlay muted loop playsInline preload="auto" aria-hidden="true" />
        <LedgerCanvas />
        <div className="hero-shade" />
        <div className="hero-content">
          <div className="eyebrow">Journal Entry Testing · ISA 240 · FY2025</div>
          <h1>Every journal tested.<br /><em>Only the ones that matter</em> surfaced.</h1>
          <p className="lead">
            Rules, statistics and machine learning test 100% of the ledger, then an AI assistant explains the results
            to the auditor, using verified data only.
          </p>
          <div className="ctas">
            <a href="#results" className="btn">See the results</a>
            <button className="btn ghost" onClick={goToAgent}>Ask the audit agent</button>
          </div>
          <div className="trust">
            <span>100% of journals tested</span>
            <span>80 automated tests</span>
            <span>EU-hosted on Azure</span>
          </div>
        </div>
        <a href="#problem" className="scroll-cue">Scroll</a>
      </header>

      <main>
        <section id="problem" className="section">
          <Reveal><div className="label">The problem</div></Reveal>
          <Reveal delay={0.1}>
            <h2>Thousands of entries. <em>One override</em> is enough.</h2>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="body">
              Management can override controls through journal entries, and sampling sees only a fraction of them.
              This engine reviews the full population and hands the team a short, ranked and explained list.
            </p>
          </Reveal>
          <StatBand stats={stats} />
          {error && <p className="alert">The service is waking up. Refresh in a few seconds.</p>}
        </section>

        <section id="approach" className="section">
          <Reveal><div className="label">The approach</div></Reveal>
          <Reveal delay={0.1}><h2>Five layers. <em>Each one</em> answers a different risk.</h2></Reveal>
          <div className="steps">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 0.08} className="step">
                <div className="step-n">{s.n}</div>
                <div className="step-tag">{s.tag}</div>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </Reveal>
            ))}
          </div>
        </section>

        <section id="results" className="section">
          <Reveal><div className="label">The results</div></Reveal>
          <Reveal delay={0.1}>
            <h2>From <em>{fmt(stats?.total_journals)}</em> journals to <em className="red">{fmt(stats?.high_risk_journals)}</em>.</h2>
          </Reveal>

          <Reveal className="funnel" delay={0.2}>
            {[
              ["Ledger lines tested", stats?.total_lines, 100],
              ["Journals scored by rules and ML", stats?.total_journals, 68],
              ["Flagged for auditor review", stats?.high_risk_journals, 22],
            ].map(([lbl, v, w], i) => (
              <div key={lbl} className={`bar ${i === 2 ? "hot" : ""}`} style={{ "--w": `${w}%`, transitionDelay: `${0.3 + i * 0.25}s` }}>
                <span>{lbl}</span><b>{fmt(v)}</b>
              </div>
            ))}
          </Reveal>

          <Reveal className="panel" delay={0.1}>
            <div className="panel-head">
              <h3>High-risk journals</h3>
              <span>Ranked by risk score · click a row to see why</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Journal</th><th>Posted by</th><th>Date</th><th>Risk</th><th className="num">Amount €</th></tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <FragmentRow key={r.journal_id} r={r} maxScore={maxScore}
                                 open={openRow === r.journal_id}
                                 onToggle={() => setOpenRow(openRow === r.journal_id ? null : r.journal_id)} />
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </section>

        <section id="agent" className="section">
          <Reveal><div className="label">The audit agent</div></Reveal>
          <Reveal delay={0.1}><h2>Ask in plain language. <em>Get verified answers.</em></h2></Reveal>
          <Reveal className="panel chat" delay={0.2}>
            <div className="messages" ref={boxRef}>
              {chat.length === 0 && (
                <div className="empty">
                  <p>The agent selects a tool, reads the verified results and answers. It never guesses.</p>
                  <div className="chips">
                    {SUGGESTIONS.map((s) => <button key={s} onClick={() => ask(s)}>{s}</button>)}
                  </div>
                </div>
              )}
              {chat.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <div>{m.text}</div>
                  {m.tools?.length > 0 && <small>tools used: {m.tools.join(", ")}</small>}
                </div>
              ))}
              {loading && <div className="msg agent typing"><i /><i /><i /></div>}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); ask(question); }}>
              <input ref={inputRef} value={question} onChange={(e) => setQuestion(e.target.value)}
                     placeholder="Ask about the results…" maxLength={500} />
              <button className="btn" disabled={loading}>Send</button>
            </form>
          </Reveal>
        </section>

        <section id="safeguards" className="section">
          <Reveal><div className="label">Safeguards</div></Reveal>
          <Reveal delay={0.1}><h2>Built for audit, <em>not just for demos.</em></h2></Reveal>
          <div className="accordion">
            {SAFEGUARDS.map(([t, d], i) => (
              <Reveal key={t} delay={i * 0.05}>
                <button className={`acc ${openSafe === i ? "open" : ""}`} onClick={() => setOpenSafe(openSafe === i ? -1 : i)}>
                  <span>{t}</span><i>+</i>
                </button>
                <div className={`acc-body ${openSafe === i ? "open" : ""}`}><p>{d}</p></div>
              </Reveal>
            ))}
          </div>
        </section>

        <section className="section cta-final">
          <Reveal><h2>See it <em>work on the results.</em></h2></Reveal>
          <Reveal delay={0.1}><button className="btn" onClick={goToAgent}>Ask the audit agent</button></Reveal>
        </section>
      </main>

      <footer>
        <div>Audit Tech AI · Independent portfolio project by Ioannis Papadakis</div>
        <div>Synthetic data · Not affiliated with or endorsed by Deloitte</div>
      </footer>
    </>
  );
}