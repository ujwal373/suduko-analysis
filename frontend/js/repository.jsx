/* Page 2 — Repository table + detail view + modular analytics dashboard.
   Exports RepositoryPage. Operates on the Technique-Tier record model:
   { id, publisher, publisherShort, claimed, claimedScore, measuredScore,
     mismatch, verdict, tech, clues, grid, date, ts, source }.            */

const MIN_FOR_ANALYTICS = 5;

// ---- Verdict / mismatch presentation --------------------------------------
// mismatch = measured − claimed.  >0 under-rated, <0 over-rated, 0 accurate.
function verdictMeta(mismatch) {
  const sig = Math.abs(mismatch) >= 3;
  if (mismatch === 0)
    return { tone: "accurate", sig: false, badge: "bg-emerald-50 text-emerald-700 ring-emerald-600/30 dark:bg-emerald-500/10 dark:text-emerald-300", num: "text-emerald-600 dark:text-emerald-400", dot: "#059669" };
  if (mismatch > 0)
    return { tone: "under", sig, badge: "bg-amber-50 text-amber-700 ring-amber-600/30 dark:bg-amber-500/10 dark:text-amber-300", num: "text-amber-600 dark:text-amber-400", dot: "#d97706" };
  return   { tone: "over",  sig, badge: "bg-sky-50 text-sky-700 ring-sky-600/30 dark:bg-sky-500/10 dark:text-sky-300",     num: "text-sky-600 dark:text-sky-400",     dot: "#0284c7" };
}

function VerdictBadge({ verdict, mismatch, size = "sm" }) {
  const m = verdictMeta(mismatch);
  const pad = size === "lg" ? "px-2.5 py-1 text-xs" : "px-2 py-0.5 text-[11px]";
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md font-medium ring-1 ring-inset ${pad} ${m.badge} ${m.sig ? "ring-2 font-semibold" : ""}`}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.dot }}></span>
      {verdict}
    </span>
  );
}

function MismatchCell({ mismatch, align = "right" }) {
  const m = verdictMeta(mismatch);
  const txt = mismatch > 0 ? `+${mismatch}` : `${mismatch}`;
  return (
    <span className={`inline-flex items-center justify-${align === "right" ? "end" : "start"} font-mono tabular-nums ${m.num} ${m.sig ? "font-bold" : "font-medium"}`}>
      {txt}{m.sig ? <span className="ml-1 text-[9px]">{mismatch > 0 ? "▲▲" : "▼▼"}</span> : null}
    </span>
  );
}

function MetricCard({ label, value, sub, tone }) {
  const toneCls = {
    accent: "text-accent-600 dark:text-accent-400",
    emerald: "text-emerald-600 dark:text-emerald-400",
    amber: "text-amber-600 dark:text-amber-400",
    sky: "text-sky-600 dark:text-sky-400",
    slate: "text-slate-900 dark:text-white",
  }[tone || "slate"];
  return (
    <Card className="p-4">
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`mt-1.5 font-mono text-2xl font-semibold tnum ${toneCls}`}>{value}</div>
      {sub ? <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{sub}</div> : null}
    </Card>
  );
}

function SortHead({ children, col, sort, setSort, align = "left" }) {
  const active = sort.col === col;
  return (
    <th
      className={`cursor-pointer select-none whitespace-nowrap px-3.5 py-2.5 font-medium transition hover:text-slate-700 dark:hover:text-slate-200 ${align === "right" ? "text-right" : "text-left"}`}
      onClick={() => setSort({ col, dir: active && sort.dir === "asc" ? "desc" : "asc" })}
    >
      <span className={`inline-flex items-center gap-1 ${align === "right" ? "flex-row-reverse" : ""}`}>
        {children}
        <span className={`text-[9px] transition ${active ? "text-accent-500 opacity-100" : "opacity-30"}`}>
          {active && sort.dir === "asc" ? "▲" : "▼"}
        </span>
      </span>
    </th>
  );
}

// ---- Analytics placeholder (extensible dashboard slots) --------------------
const stripeBg = {
  backgroundImage:
    "repeating-linear-gradient(45deg, transparent, transparent 7px, rgba(100,116,139,0.07) 7px, rgba(100,116,139,0.07) 8px)",
};

function PlaceholderPanel({ title, sub, purpose, height = 150 }) {
  return (
    <Card>
      <CardHead
        title={title}
        sub={sub}
        icon={<Icon.chart />}
        right={<span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-500 dark:bg-slate-800 dark:text-slate-400">Planned</span>}
      />
      <div className="p-4">
        <div
          className="grid place-items-center rounded-lg border border-dashed border-slate-300 text-center dark:border-slate-700"
          style={{ height, ...stripeBg }}
        >
          <div className="px-6">
            <div className="mx-auto mb-2 grid h-9 w-9 place-items-center rounded-lg bg-white/70 text-slate-400 ring-1 ring-slate-200 dark:bg-slate-900/70 dark:ring-slate-700">
              <Icon.chart width="17" height="17" />
            </div>
            <p className="font-mono text-[10px] leading-relaxed text-slate-500 dark:text-slate-400">{purpose}</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ---- Puzzle detail modal ---------------------------------------------------
function DetailRow({ label, children }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-right text-sm font-medium text-slate-800 dark:text-slate-100">{children}</span>
    </div>
  );
}

function FuturePill({ children }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-dashed border-slate-300 px-3 py-2 dark:border-slate-700" style={stripeBg}>
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{children}</span>
      <span className="font-mono text-[9px] uppercase tracking-wider text-slate-400">Planned</span>
    </div>
  );
}

function DetailModal({ record, onClose }) {
  const E = window.SudokuEngine;
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!record) return null;
  const board = E.parse(record.grid || "");
  const givens = board.map((v) => v !== 0);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-slate-900/40 p-4 backdrop-blur-sm dark:bg-black/60" onClick={onClose}>
      <div
        className="animate-fade my-6 w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-cardlg dark:border-slate-800 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold text-slate-900 dark:text-white">{record.id}</span>
              {record.source === "user" ? <span className="rounded bg-accent-50 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-accent-600 dark:bg-accent-500/10 dark:text-accent-300">new</span> : null}
            </div>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Puzzle detail · {record.publisher}</p>
          </div>
          <button onClick={onClose} className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200" aria-label="Close">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" /></svg>
          </button>
        </div>

        <div className="grid gap-5 p-5 sm:grid-cols-[auto_1fr]">
          <div className="flex flex-col items-center">
            <SudokuGrid board={board} givens={givens} conflicts={[]} readOnly />
            <p className="mt-2 font-mono text-[10px] text-slate-400">{record.clues} clues given</p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <VerdictBadge verdict={record.verdict} mismatch={record.mismatch} size="lg" />
              <MismatchCell mismatch={record.mismatch} />
            </div>
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              <DetailRow label="Publisher">{record.publisher}</DetailRow>
              <DetailRow label="Claimed difficulty">{record.claimed}</DetailRow>
              <DetailRow label="Claimed score"><span className="font-mono tabular-nums">{record.claimedScore}</span></DetailRow>
              <DetailRow label="Measured score"><span className="font-mono tabular-nums">{record.measuredScore}</span></DetailRow>
              <DetailRow label="Hardest technique">{record.tech}</DetailRow>
              <DetailRow label="Saved"><span className="font-mono text-xs text-slate-500">{(record.ts || record.date || "").slice(0, 16).replace("T", " ")}</span></DetailRow>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 px-5 pb-5 pt-4 dark:border-slate-800">
          <h4 className="mb-2 font-mono text-[10px] uppercase tracking-widest text-slate-400">Solver detail · coming soon</h4>
          <div className="grid gap-2 sm:grid-cols-3">
            <FuturePill>Full solving path</FuturePill>
            <FuturePill>Technique usage log</FuturePill>
            <FuturePill>Solver trace</FuturePill>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Page ------------------------------------------------------------------
function RepositoryPage({ repo }) {
  const D = window.SudokuData;
  const { user, analyticsUnlocked, puzzleCount } = useUser();
  const [query, setQuery] = useState("");
  const [pubFilter, setPubFilter] = useState("");
  const [diffFilter, setDiffFilter] = useState("");
  const [sort, setSort] = useState({ col: "id", dir: "asc" });
  const [selected, setSelected] = useState(null);
  const [moreOpen, setMoreOpen] = useState(false);

  // Difficulty options adapt to the chosen publisher (else union of all).
  const diffOptions = useMemo(() => {
    if (pubFilter) return D.diffsFor(pubFilter);
    const seen = [];
    D.SUBMIT_PUBLISHERS.forEach((p) => D.diffsFor(p).forEach((d) => { if (!seen.includes(d)) seen.push(d); }));
    return seen;
  }, [pubFilter]);

  const onPubFilter = (p) => {
    setPubFilter(p);
    if (p && !D.diffsFor(p).includes(diffFilter)) setDiffFilter("");
  };

  const filtered = useMemo(() => {
    let rows = repo.filter((r) => {
      if (pubFilter && r.publisher !== pubFilter) return false;
      if (diffFilter && r.claimed !== diffFilter) return false;
      if (query) {
        const q = query.toLowerCase();
        const hay = `${r.id} ${r.publisher} ${r.publisherShort} ${r.tech}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const dir = sort.dir === "asc" ? 1 : -1;
    rows = rows.slice().sort((a, b) => {
      let av, bv;
      switch (sort.col) {
        case "publisher": av = a.publisher; bv = b.publisher; break;
        case "claimed": av = a.claimedScore; bv = b.claimedScore; break;
        case "claimedScore": av = a.claimedScore; bv = b.claimedScore; break;
        case "measuredScore": av = a.measuredScore; bv = b.measuredScore; break;
        case "mismatch": case "verdict": av = a.mismatch; bv = b.mismatch; break;
        case "tech": av = a.tech; bv = b.tech; break;
        default: av = a.id; bv = b.id;
      }
      return av < bv ? -dir : av > bv ? dir : 0;
    });
    return rows;
  }, [repo, query, pubFilter, diffFilter, sort]);

  const stats = useMemo(() => D.analytics(filtered), [filtered]);
  // Use user context for analytics unlock (based on total saved puzzles, not just filtered)

  const exportCSV = () => {
    const head = ["Puzzle ID", "Publisher", "Claimed Difficulty", "Claimed Score", "Measured Score", "Mismatch", "Verdict", "Hardest Technique", "Clues", "Date"];
    const lines = [head.join(",")].concat(filtered.map((r) =>
      [r.id, `"${r.publisher}"`, r.claimed, r.claimedScore, r.measuredScore, r.mismatch, `"${r.verdict}"`, `"${r.tech}"`, r.clues, r.date].join(",")
    ));
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "sudoku-repository.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-[1180px] px-5 py-8 lg:px-8">
      <div className="mb-6">
        <div className="mb-1.5 font-mono text-[11px] uppercase tracking-widest text-accent-600 dark:text-accent-400">Repository · Page 2</div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Puzzle repository &amp; analytics</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          {repo.length} analyzed puzzles across {D.SUBMIT_PUBLISHERS.length} publishers. Filter the corpus and compare each publisher's claimed difficulty against the engine-measured technique-tier score.
        </p>
      </div>

      {/* toolbar */}
      <Card className="mb-5 p-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[200px] flex-1">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"><Icon.search /></span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search ID, publisher, or technique…"
              className={`${inputCls} pl-9`}
            />
          </div>
          <div className="w-44"><Select value={pubFilter} onChange={onPubFilter} options={D.SUBMIT_PUBLISHERS} placeholder="All publishers" /></div>
          <div className="w-40"><Select value={diffFilter} onChange={setDiffFilter} options={diffOptions} placeholder="All difficulties" /></div>
          <Button variant="outline" onClick={exportCSV}><Icon.download />Export CSV</Button>
        </div>
      </Card>

      {/* data table */}
      <Card className="mb-9 overflow-hidden">
        <CardHead title="Analyzed puzzles" sub={`${filtered.length} of ${repo.length} records · click a row for detail`} icon={<Icon.grid />} />
        <div className="thin-scroll max-h-[460px] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-slate-50 font-mono text-[10px] uppercase tracking-wider text-slate-400 shadow-[0_1px_0_0_rgba(0,0,0,0.05)] dark:bg-slate-950/60">
              <tr>
                <SortHead col="id" sort={sort} setSort={setSort}>Puzzle ID</SortHead>
                <SortHead col="publisher" sort={sort} setSort={setSort}>Publisher</SortHead>
                <SortHead col="claimed" sort={sort} setSort={setSort}>Claimed</SortHead>
                <SortHead col="claimedScore" sort={sort} setSort={setSort} align="right">Claim</SortHead>
                <SortHead col="measuredScore" sort={sort} setSort={setSort} align="right">Measured</SortHead>
                <SortHead col="mismatch" sort={sort} setSort={setSort} align="right">Mismatch</SortHead>
                <SortHead col="verdict" sort={sort} setSort={setSort}>Verdict</SortHead>
                <SortHead col="tech" sort={sort} setSort={setSort}>Hardest technique</SortHead>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className="cursor-pointer transition hover:bg-slate-50 dark:hover:bg-slate-800/40"
                >
                  <td className="px-3.5 py-2.5 font-mono text-[13px] text-slate-500 dark:text-slate-400">{r.id}</td>
                  <td className="px-3.5 py-2.5">
                    <span className="font-medium text-slate-800 dark:text-slate-100">{r.publisherShort}</span>
                    {r.source === "user" ? <span className="ml-1.5 font-mono text-[10px] text-accent-500">·new</span> : null}
                  </td>
                  <td className="px-3.5 py-2.5 text-slate-600 dark:text-slate-300">{r.claimed}</td>
                  <td className="px-3.5 py-2.5 text-right font-mono tnum text-slate-500 dark:text-slate-400">{r.claimedScore}</td>
                  <td className="px-3.5 py-2.5 text-right font-mono tnum font-semibold text-slate-800 dark:text-slate-100">{r.measuredScore}</td>
                  <td className="px-3.5 py-2.5 text-right"><MismatchCell mismatch={r.mismatch} /></td>
                  <td className="px-3.5 py-2.5"><VerdictBadge verdict={r.verdict} mismatch={r.mismatch} /></td>
                  <td className="px-3.5 py-2.5 text-slate-600 dark:text-slate-300">{r.tech}</td>
                </tr>
              ))}
              {filtered.length === 0 ? (
                <tr><td colSpan="8" className="px-3.5 py-12 text-center text-sm text-slate-400">No puzzles match these filters.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>

      {/* analytics */}
      <SectionTitle kicker="Analytics" title="Difficulty calibration" sub="How accurately publishers label their puzzles, measured against the engine's technique-tier verdict on the current selection." />

      {/* counters — update automatically as puzzles are saved */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Saved puzzles" value={repo.length} sub={`${filtered.length} in selection`} tone="accent" />
        <MetricCard label="Claim accuracy" value={`${Math.round(stats.agreement * 100)}%`} sub={`${stats.accurate} exact matches`} tone={stats.agreement > 0.5 ? "emerald" : "amber"} />
        <MetricCard label="Misclassified" value={stats.over + stats.under} sub={`${stats.under} under · ${stats.over} over`} tone="amber" />
        <MetricCard label="Mean |mismatch|" value={stats.meanAbsMismatch.toFixed(1)} sub="scale points off" tone={stats.meanAbsMismatch < 1.5 ? "emerald" : "sky"} />
      </div>

      {!analyticsUnlocked ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
            <Icon.chart width="22" height="22" />
          </div>
          <h3 className="mt-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Analytics locked</h3>
          <p className="mt-1.5 max-w-sm text-sm text-slate-500 dark:text-slate-400">
            Save {MIN_FOR_ANALYTICS - puzzleCount} more puzzle{MIN_FOR_ANALYTICS - puzzleCount !== 1 ? 's' : ''} to unlock analytics dashboards.
          </p>
          <div className="mt-4 flex items-center gap-3">
            <div className="h-2 w-32 rounded-full bg-slate-200 dark:bg-slate-700">
              <div className="h-2 rounded-full bg-accent-500 transition-all" style={{ width: `${Math.min(100, (puzzleCount / MIN_FOR_ANALYTICS) * 100)}%` }}></div>
            </div>
            <span className="font-mono text-[11px] text-slate-400">{puzzleCount} / {MIN_FOR_ANALYTICS}</span>
          </div>
        </Card>
      ) : (
        <div className="space-y-5">
          {/* priority chart — full width */}
          <Card>
            <CardHead title="Publisher comparison" sub="Measured difficulty score distribution per publisher (highest priority)" icon={<Icon.chart />} />
            <div className="p-4"><BoxPlot rows={filtered} publishers={D.SUBMIT_PUBLISHERS} /></div>
          </Card>

          {/* extensible placeholder slots */}
          <div className="grid gap-5 lg:grid-cols-2">
            <PlaceholderPanel
              title="Publisher consistency"
              sub="Within-publisher variance"
              purpose="FUTURE: evaluate how consistently each publisher rates puzzles of similar measured difficulty."
            />
            <PlaceholderPanel
              title="Cluster analysis"
              sub="Publisher grouping patterns"
              purpose="FUTURE: group publishers by shared mis-classification signatures across the corpus."
            />
          </div>

          {/* additional visualization area — expandable */}
          <Card>
            <button
              onClick={() => setMoreOpen((v) => !v)}
              className="flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/40"
            >
              <div className="flex items-center gap-2.5">
                <span className="text-slate-400 dark:text-slate-500"><Icon.chart /></span>
                <div>
                  <h3 className="text-sm font-semibold tracking-tight text-slate-900 dark:text-slate-100">Additional visualizations</h3>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Reserved area for future statistical charts</p>
                </div>
              </div>
              <span className={`text-slate-400 transition-transform ${moreOpen ? "rotate-180" : ""}`}>
                <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M6 8l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </span>
            </button>
            {moreOpen ? (
              <div className="grid gap-3 border-t border-slate-100 p-4 dark:border-slate-800 sm:grid-cols-2 lg:grid-cols-3">
                {["Scatter plot", "Correlation analysis", "Residual analysis", "Heat map", "Distribution charts"].map((t) => (
                  <div key={t} className="grid h-24 place-items-center rounded-lg border border-dashed border-slate-300 text-center dark:border-slate-700" style={stripeBg}>
                    <div>
                      <div className="font-mono text-[11px] font-medium text-slate-500 dark:text-slate-400">{t}</div>
                      <div className="mt-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-400">Planned</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </Card>
        </div>
      )}

      {selected ? <DetailModal record={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}

Object.assign(window, { RepositoryPage });
