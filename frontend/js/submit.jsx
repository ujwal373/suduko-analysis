/* Page 1 — Puzzle submission + live analysis results. Exports SubmitPage.
   Difficulty is graded with the Technique-Tier Classification model:
   measured score = the highest-tier technique the solver was forced to use. */
function emptyBoard() { return new Array(81).fill(0); }

// Visual treatment for a mismatch value (measured − claimed).
function verdictTone(mismatch) {
  if (mismatch === 0) return { tone: "accurate", cls: "text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-500/10 ring-emerald-600/20", glyph: <Icon.check />, dot: "#059669" };
  if (mismatch > 0)   return { tone: "under",    cls: "text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-500/10 ring-amber-600/20",       glyph: <Icon.warn width="13" height="13" />, dot: "#d97706" };
  return                     { tone: "over",     cls: "text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-500/10 ring-rose-600/20",          glyph: <Icon.warn width="13" height="13" />, dot: "#e11d48" };
}

function ScoreTile({ kicker, score, caption, accent }) {
  const ring = accent === "measured"
    ? "border-accent-300 dark:border-accent-500/40"
    : "border-slate-200 dark:border-slate-800";
  return (
    <div className={`rounded-lg border bg-white p-4 dark:bg-slate-950/20 ${ring}`}>
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-400">{kicker}</div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="font-mono text-3xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">{score}</span>
        <span className="font-mono text-sm text-slate-400">/ 10</span>
      </div>
      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{caption}</div>
    </div>
  );
}

// One label / value line inside a labelled panel section.
function DefRow({ label, children }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-right text-sm font-medium text-slate-800 dark:text-slate-100">{children}</span>
    </div>
  );
}

function PanelSection({ kicker, children }) {
  return (
    <div>
      <h4 className="mb-1 font-mono text-[10px] uppercase tracking-widest text-slate-400">{kicker}</h4>
      <div className="divide-y divide-slate-100 dark:divide-slate-800">{children}</div>
    </div>
  );
}

// Builds the automatically-generated, plain-language explanation.
function buildExplanation({ result, publisher, claimed, claimedScore, mismatch, verdict }) {
  const tech = result.hardestTech.name;
  const ms = result.measuredScore;
  const techPhrase = result.outOfScope
    ? `required an advanced technique beyond the standard scale, capping its measured difficulty score at ${ms}`
    : `required ${/^[aeiou]/i.test(tech) ? "an" : "a"} ${tech} technique, giving it a measured difficulty score of ${ms}`;

  const claimPhrase = `${publisher} classified the puzzle as ${claimed} (claimed score ${claimedScore})`;

  let conclusion;
  if (mismatch === 0) conclusion = "The two scores agree, so the publisher's rating is accurate.";
  else conclusion = `The mismatch of ${mismatch > 0 ? "+" : ""}${mismatch} means the puzzle is ${verdict.toLowerCase()}.`;

  return `The puzzle ${techPhrase}. ${claimPhrase}. ${conclusion}`;
}

function ResultsCard({ result, publisher, claimed }) {
  const D = window.SudokuData;

  if (!result) {
    return (
      <Card className="flex h-full min-h-[440px] flex-col items-center justify-center p-10 text-center">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
          <Icon.flask width="24" height="24" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-slate-700 dark:text-slate-200">No analysis yet</h3>
        <p className="mt-1.5 max-w-xs text-sm text-slate-500 dark:text-slate-400">
          Select a publisher and claimed difficulty, enter the puzzle, then run the solver. The engine applies human techniques in order and grades by the most advanced one required.
        </p>
      </Card>
    );
  }

  if (!result.ok) {
    return (
      <Card className="flex h-full min-h-[440px] flex-col items-center justify-center p-10 text-center animate-fade">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-rose-50 text-rose-500 dark:bg-rose-500/10">
          <Icon.warn width="26" height="26" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-slate-800 dark:text-slate-100">Cannot analyze this grid</h3>
        <p className="mt-1.5 max-w-xs text-sm text-slate-500 dark:text-slate-400">{result.message}</p>
      </Card>
    );
  }

  const claimedScore = D.claimedScore(publisher, claimed);
  const measured = result.measuredScore;
  const mismatch = claimedScore != null ? measured - claimedScore : null;
  const verdict = mismatch != null ? D.verdict(mismatch) : null;
  const vt = mismatch != null ? verdictTone(mismatch) : null;
  const explanation = mismatch != null
    ? buildExplanation({ result, publisher, claimed, claimedScore, mismatch, verdict })
    : null;

  return (
    <Card className="h-full animate-fade">
      <CardHead
        title="Analysis results"
        sub="Technique-Tier Classification"
        right={verdict ? (
          <div className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${vt.cls}`}>
            {vt.glyph}{verdict}
          </div>
        ) : null}
      />

      <div className="space-y-5 p-5">
        {/* Score comparison hero */}
        <div className="grid grid-cols-3 gap-3">
          <ScoreTile kicker="Claimed" score={claimedScore != null ? claimedScore : "—"} caption={claimed ? `${publisher} · ${claimed}` : "No claim set"} />
          <ScoreTile kicker="Measured" score={measured} caption={result.hardestTech.name} accent="measured" />
          <div className={`flex flex-col justify-center rounded-lg border p-4 ${mismatch != null ? "border-transparent " + vt.cls : "border-slate-200 dark:border-slate-800"}`}>
            <div className="font-mono text-[10px] uppercase tracking-wider opacity-70">Mismatch</div>
            <div className="mt-1 font-mono text-3xl font-semibold tabular-nums">
              {mismatch != null ? (mismatch > 0 ? "+" : "") + mismatch : "—"}
            </div>
            <div className="mt-1 text-xs font-medium">{verdict || "Set a claim"}</div>
          </div>
        </div>

        {/* Detail panels */}
        <div className="grid gap-5 sm:grid-cols-2">
          <PanelSection kicker="Publisher information">
            <DefRow label="Publisher">{publisher || "—"}</DefRow>
            <DefRow label="Claimed difficulty">{claimed || "—"}</DefRow>
            <DefRow label="Claimed score"><span className="font-mono tabular-nums">{claimedScore != null ? claimedScore : "—"}</span></DefRow>
          </PanelSection>
          <PanelSection kicker="Measured assessment">
            <DefRow label="Highest technique found">
              {result.hardestTech.name}
              {result.outOfScope ? <span className="ml-1 align-top font-mono text-[9px] text-rose-500">★</span> : null}
            </DefRow>
            <DefRow label="Measured score"><span className="font-mono tabular-nums">{measured}</span></DefRow>
            <DefRow label="Clues given"><span className="font-mono tabular-nums">{result.clues}</span></DefRow>
          </PanelSection>
        </div>

        {result.outOfScope ? (
          <div className="flex items-start gap-2 rounded-lg bg-rose-50 px-3 py-2.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300">
            <Icon.warn width="14" height="14" className="mt-0.5 shrink-0" />
            Advanced Out-of-Scope Technique Detected — graded at the scale maximum (10).
          </div>
        ) : null}

        {/* Explanation */}
        {explanation ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/30">
            <h4 className="mb-1.5 font-mono text-[10px] uppercase tracking-widest text-slate-400">Explanation</h4>
            <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-200" style={{ textWrap: "pretty" }}>{explanation}</p>
          </div>
        ) : null}
      </div>

      {/* Technique breakdown — methodological transparency */}
      <div className="border-t border-slate-100 px-5 pb-5 pt-4 dark:border-slate-800">
        <div className="mb-2 flex items-center justify-between">
          <h4 className="font-mono text-[11px] uppercase tracking-widest text-slate-500 dark:text-slate-400">Techniques applied</h4>
          <span className="font-mono text-[11px] text-slate-400">{result.breakdown.length} distinct</span>
        </div>
        <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-left font-mono text-[10px] uppercase tracking-wider text-slate-400 dark:bg-slate-950/40">
                <th className="px-3 py-2 font-medium">Technique</th>
                <th className="px-3 py-2 text-right font-medium">Tier score</th>
                <th className="px-3 py-2 text-right font-medium">Times used</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {result.breakdown.map((b) => {
                const top = b.score === result.measuredScore;
                return (
                  <tr key={b.key} className={top ? "bg-accent-50/50 dark:bg-accent-500/5" : ""}>
                    <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                      {b.name}
                      {top ? <span className="ml-1.5 font-mono text-[9px] uppercase tracking-wide text-accent-600 dark:text-accent-400">peak</span> : null}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">{b.score}</td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-500 dark:text-slate-400">{b.count}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-2.5 font-mono text-[10px] leading-relaxed text-slate-400" style={{ textWrap: "pretty" }}>
          Measured difficulty = the highest tier score among all techniques the solver was forced to use. Mismatch = measured score − claimed score.
        </p>
      </div>
    </Card>
  );
}

function SubmitPage({ addRecord }) {
  const D = window.SudokuData, E = window.SudokuEngine;
  const [board, setBoard] = useState(emptyBoard);
  const [givens, setGivens] = useState(() => new Array(81).fill(false));
  const [publisher, setPublisher] = useState("");
  const [claimed, setClaimed] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const conflicts = useMemo(() => [...E.findConflicts(board)], [board]);
  const filled = board.filter((v) => v).length;
  const diffOptions = publisher ? D.diffsFor(publisher) : [];

  const onPublisherChange = (p) => {
    setPublisher(p);
    setClaimed("");          // reset difficulty when publisher changes
    setResult(null); setSaved(false);
  };

  const clearAll = () => {
    setBoard(emptyBoard()); setGivens(new Array(81).fill(false));
    setResult(null); setSaved(false);
  };

  const onGridChange = (next) => { setBoard(next); setResult(null); setSaved(false); };

  const analyze = () => {
    setBusy(true); setResult(null); setSaved(false);
    setTimeout(() => {
      const r = E.analyze(board);
      setResult(r);
      setBusy(false);
    }, 560);
  };

  // Persist a full Technique-Tier record. The repository table, analytics
  // counters, puzzle count and analytics unlock all update automatically via
  // shared React state — no manual refresh required.
  const submitToRepo = () => {
    if (!result || !result.ok) return;
    const cScore = D.claimedScore(publisher, claimed);
    const mismatch = result.measuredScore - cScore;
    addRecord({
      publisher,
      publisherShort: D.SUBMIT_PUBLISHER_SHORT[publisher] || publisher,
      claimed,
      claimedScore: cScore,
      measuredScore: result.measuredScore,
      mismatch,
      verdict: D.verdict(mismatch),
      tech: result.hardestTech.name,
      clues: result.clues,
      grid: board.map((v) => v || 0).join(""),
      date: new Date().toISOString().slice(0, 10),
      ts: new Date().toISOString(),
      source: "user",
    });
    setSaved(true);
  };

  const canAnalyze = !busy && publisher && claimed && filled >= 17 && conflicts.length === 0;

  return (
    <div className="mx-auto max-w-[1180px] px-5 py-8 lg:px-8">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-1.5 font-mono text-[11px] uppercase tracking-widest text-accent-600 dark:text-accent-400">Submission · Page 1</div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Analyze a puzzle</h1>
          <p className="mt-1.5 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
            Enter a 9×9 puzzle and the publisher's claimed difficulty. The engine solves it with human techniques, measures the true difficulty from the most advanced technique required, and flags any mismatch with the claim.
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
        {/* LEFT — form + grid */}
        <div className="flex flex-col gap-5">
          <Card className="p-5">
            <h3 className="mb-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Puzzle metadata</h3>
            <div className="grid grid-cols-2 gap-3.5">
              <Field label="Publisher" hint="required">
                <Select value={publisher} onChange={onPublisherChange} options={D.SUBMIT_PUBLISHERS} placeholder="Select…" />
              </Field>
              <Field label="Claimed difficulty" hint={publisher ? "required" : "pick publisher"}>
                <Select
                  value={claimed}
                  onChange={(v) => { setClaimed(v); setResult(null); setSaved(false); }}
                  options={diffOptions}
                  placeholder={publisher ? "Select…" : "—"}
                  className={!publisher ? "cursor-not-allowed opacity-50" : ""}
                />
              </Field>
            </div>
          </Card>

          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                <Icon.grid /><span className="text-xs font-medium">Puzzle grid</span>
              </div>
              <span className="font-mono text-[11px] text-slate-400 tnum">{filled}/81 filled</span>
            </div>
            <div className="flex justify-center">
              <SudokuGrid board={board} givens={givens} conflicts={conflicts} onChange={onGridChange} />
            </div>
            <div className="mt-4 flex items-center justify-end">
              <Button variant="ghost" onClick={clearAll}>Clear grid</Button>
            </div>
            {conflicts.length ? (
              <div className="mt-3 flex items-center gap-1.5 rounded-md bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-600 dark:bg-rose-500/10 dark:text-rose-400">
                <Icon.warn width="13" height="13" />{conflicts.length} cells conflict — duplicate in a row, column, or box.
              </div>
            ) : (
              <p className="mt-3 font-mono text-[10px] text-slate-400">Click a cell, type 1–9, arrows to move, 0/⌫ to clear.</p>
            )}
            <Button className="mt-4 w-full" onClick={analyze} disabled={!canAnalyze}>
              {busy ? <><Icon.spin className="animate-spin" />Analyzing…</> : <><Icon.play />Analyze puzzle</>}
            </Button>
            {!publisher || !claimed ? (
              <p className="mt-2 text-center font-mono text-[10px] text-slate-400">Select a publisher and claimed difficulty to enable analysis.</p>
            ) : null}
            {result && result.ok ? (
              <button
                onClick={submitToRepo}
                disabled={saved}
                className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium text-accent-700 transition hover:bg-accent-50 disabled:opacity-60 dark:text-accent-300 dark:hover:bg-accent-500/10"
              >
                {saved ? <><Icon.check />Saved to repository</> : <>Save puzzle to repository<Icon.arrow /></>}
              </button>
            ) : null}
          </Card>
        </div>

        {/* RIGHT — results */}
        <ResultsCard result={busy ? null : result} publisher={publisher} claimed={claimed} />
      </div>
    </div>
  );
}

Object.assign(window, { SubmitPage });
