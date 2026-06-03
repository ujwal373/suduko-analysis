/* Hand-built SVG charts — academic, minimal. Exports to window.
   Each chart uses a fixed viewBox and scales to its container width.

   Color Palette (Research Theme):
   - Frozen Water: #CFFCFF (cool/light - overrated)
   - Pearl Aqua: #AAEFDF (cool mid)
   - Light Green: #9EE37D (accurate/neutral)
   - Bright Fern: #63C132 (warm mid - underrated)
   - India Green: #358600 (warm/strong - very underrated)
*/

// ---- Color Palette ----
const PALETTE = {
  frozenWater: "#CFFCFF",
  pearlAqua: "#AAEFDF",
  lightGreen: "#9EE37D",
  brightFern: "#63C132",
  indiaGreen: "#358600",
};

// ---- Publisher Colors (consistent across all charts) ----
const PUBLISHER_COLORS = {
  "NYT": PALETTE.indiaGreen,
  "Sudoku.com": PALETTE.brightFern,
  "The Guardian": PALETTE.pearlAqua,
  "Times Sudoku": PALETTE.lightGreen,
};

// ---- Primary Publishers (excludes "Others" for analytics) ----
const PRIMARY_PUBLISHERS = ["NYT", "Sudoku.com", "The Guardian", "Times Sudoku"];

// ---- Unified Difficulty Ordering (easiest to hardest) ----
const UNIFIED_DIFFICULTY_ORDER = [
  "Easy",
  "Mild",
  "Medium",
  "Moderate",
  "Hard",
  "Difficult",
  "Expert",
  "Master",
  "Fiendish",
  "Extreme",
  "Super Fiendish"
];

// shared axis/grid colors via Tailwind text-* + currentColor
const axisStroke = "text-slate-300 dark:text-slate-700";
const tickText = "fill-slate-400 dark:fill-slate-500";
const labelText = "fill-slate-500 dark:fill-slate-400";

function polar(cx, cy, r, deg) {
  const a = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}
function arcPath(cx, cy, r, startDeg, endDeg) {
  const [x1, y1] = polar(cx, cy, r, startDeg);
  const [x2, y2] = polar(cx, cy, r, endDeg);
  const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  const sweep = endDeg > startDeg ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} ${sweep} ${x2} ${y2}`;
}

// ====== Difficulty gauge ====================================================
function DifficultyGauge({ value, max = 1000, difficulty }) {
  const W = 320, H = 188, cx = W / 2, cy = 162, r = 128, sw = 16;
  const frac = Math.max(0, Math.min(1, value / max));
  const ang = 180 + frac * 180;
  const bands = [
    { from: 0, to: 0.255, color: PALETTE.lightGreen },
    { from: 0.255, to: 0.515, color: PALETTE.brightFern },
    { from: 0.515, to: 1, color: PALETTE.indiaGreen },
  ];
  const [nx, ny] = polar(cx, cy, r - 26, ang);
  const dColor = { Easy: PALETTE.lightGreen, Medium: PALETTE.brightFern, Hard: PALETTE.indiaGreen }[difficulty] || PALETTE.pearlAqua;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: W }} className="mx-auto block">
      {/* track */}
      <path d={arcPath(cx, cy, r, 180, 360)} fill="none" className="stroke-slate-100 dark:stroke-slate-800" strokeWidth={sw} strokeLinecap="round" />
      {/* bands */}
      {bands.map((b, k) => (
        <path key={k} d={arcPath(cx, cy, r, 180 + b.from * 180, 180 + b.to * 180)} fill="none" stroke={b.color} strokeWidth={sw} strokeLinecap="butt" opacity="0.92" />
      ))}
      {/* ticks */}
      {[0, 0.25, 0.5, 0.75, 1].map((t, k) => {
        const a = 180 + t * 180;
        const [x1, y1] = polar(cx, cy, r - sw / 2 - 3, a);
        const [x2, y2] = polar(cx, cy, r - sw / 2 - 10, a);
        const [lx, ly] = polar(cx, cy, r - sw / 2 - 22, a);
        return (
          <g key={k}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} className="stroke-slate-300 dark:stroke-slate-600" strokeWidth="1" />
            <text x={lx} y={ly + 3} textAnchor="middle" className={`${tickText} font-mono`} fontSize="9">{Math.round(t * max)}</text>
          </g>
        );
      })}
      {/* needle */}
      <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={dColor} strokeWidth="3" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="6" fill={dColor} />
      <circle cx={cx} cy={cy} r="11" fill="none" stroke={dColor} strokeWidth="1.5" opacity="0.35" />
      {/* value */}
      <text x={cx} y={cy - 34} textAnchor="middle" className="fill-slate-900 dark:fill-white font-mono" fontSize="34" fontWeight="600">{value}</text>
      <text x={cx} y={cy - 16} textAnchor="middle" className={`${labelText} font-mono`} fontSize="10" letterSpacing="1">/ {max} COMPOSITE</text>
    </svg>
  );
}

// ====== Histogram ===========================================================
function Histogram({ rows }) {
  const W = 520, H = 240, m = { t: 14, r: 14, b: 40, l: 36 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const binW = 100, bins = [];
  for (let lo = 100; lo < 1000; lo += binW) bins.push({ lo, hi: lo + binW, n: 0 });
  rows.forEach((row) => {
    const idx = Math.min(bins.length - 1, Math.floor((row.score - 100) / binW));
    if (idx >= 0) bins[idx].n++;
  });
  const maxN = Math.max(1, ...bins.map((b) => b.n));
  const yticks = niceTicks(maxN, 4);
  const bandColor = (lo) => (lo < 255 ? PALETTE.lightGreen : lo < 515 ? PALETTE.brightFern : PALETTE.indiaGreen);
  const bw = iw / bins.length;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block">
      {/* y grid + ticks */}
      {yticks.map((t, k) => {
        const y = m.t + ih - (t / yticks[yticks.length - 1]) * ih;
        return (
          <g key={k}>
            <line x1={m.l} y1={y} x2={W - m.r} y2={y} className={axisStroke} strokeWidth="1" strokeDasharray={t === 0 ? "0" : "2 3"} opacity={t === 0 ? 1 : 0.6} />
            <text x={m.l - 6} y={y + 3} textAnchor="end" className={`${tickText} font-mono`} fontSize="9">{t}</text>
          </g>
        );
      })}
      {/* bars */}
      {bins.map((b, k) => {
        const h = (b.n / yticks[yticks.length - 1]) * ih;
        const x = m.l + k * bw;
        const y = m.t + ih - h;
        return (
          <g key={k}>
            <rect x={x + bw * 0.12} y={y} width={bw * 0.76} height={Math.max(0, h)} rx="2" fill={bandColor(b.lo)} opacity="0.88" />
            {b.n > 0 ? <text x={x + bw / 2} y={y - 4} textAnchor="middle" className="fill-slate-500 dark:fill-slate-400 font-mono" fontSize="9">{b.n}</text> : null}
            {k % 2 === 0 ? <text x={x + bw / 2} y={H - m.b + 14} textAnchor="middle" className={`${tickText} font-mono`} fontSize="8">{b.lo}</text> : null}
          </g>
        );
      })}
      <text x={m.l + iw / 2} y={H - 4} textAnchor="middle" className={`${labelText} font-mono`} fontSize="9" letterSpacing="0.5">COMPOSITE SCORE</text>
    </svg>
  );
}

// ====== Box plot (per publisher) ============================================
function quantiles(arr) {
  const s = arr.slice().sort((a, b) => a - b);
  const q = (p) => {
    if (s.length === 1) return s[0];
    const idx = p * (s.length - 1), lo = Math.floor(idx), hi = Math.ceil(idx);
    return s[lo] + (s[hi] - s[lo]) * (idx - lo);
  };
  return { min: s[0], q1: q(0.25), med: q(0.5), q3: q(0.75), max: s[s.length - 1] };
}

function BoxPlot({ rows, publishers }) {
  const W = 520, H = 260, m = { t: 16, r: 16, b: 52, l: 40 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const maxScore = 10;

  // Filter to primary publishers only
  const filteredPubs = publishers.filter(p => PRIMARY_PUBLISHERS.includes(p));

  const groups = filteredPubs.map((p) => {
    const scores = rows.filter((r) => r.publisher === p).map((r) => r.measuredScore);
    return { p, short: window.SudokuData.SUBMIT_PUBLISHER_SHORT[p] || p, scores, color: PUBLISHER_COLORS[p] || PALETTE.pearlAqua };
  }).filter((g) => g.scores.length);

  const y = (v) => m.t + ih - (v / maxScore) * ih;
  const slot = iw / Math.max(1, groups.length);
  const boxW = Math.min(54, slot * 0.5);
  const yticks = [0, 2, 4, 6, 8, 10];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block">
      {yticks.map((t, k) => (
        <g key={k}>
          <line x1={m.l} y1={y(t)} x2={W - m.r} y2={y(t)} className={axisStroke} strokeWidth="1" strokeDasharray={t === 0 ? "0" : "2 3"} opacity={t === 0 ? 1 : 0.55} />
          <text x={m.l - 6} y={y(t) + 3} textAnchor="end" className={`${tickText} font-mono`} fontSize="9">{t}</text>
        </g>
      ))}
      {groups.map((g, k) => {
        const cx = m.l + slot * (k + 0.5);
        const Q = quantiles(g.scores);
        const col = g.color;
        return (
          <g key={g.p}>
            {/* whiskers */}
            <line x1={cx} y1={y(Q.min)} x2={cx} y2={y(Q.max)} stroke={col} strokeWidth="1.5" opacity="0.6" />
            <line x1={cx - 8} y1={y(Q.min)} x2={cx + 8} y2={y(Q.min)} stroke={col} strokeWidth="1.5" opacity="0.6" />
            <line x1={cx - 8} y1={y(Q.max)} x2={cx + 8} y2={y(Q.max)} stroke={col} strokeWidth="1.5" opacity="0.6" />
            {/* box */}
            <rect x={cx - boxW / 2} y={y(Q.q3)} width={boxW} height={Math.max(1, y(Q.q1) - y(Q.q3))} rx="2" fill={col} fillOpacity="0.2" stroke={col} strokeWidth="1.4" />
            {/* median */}
            <line x1={cx - boxW / 2} y1={y(Q.med)} x2={cx + boxW / 2} y2={y(Q.med)} stroke={col} strokeWidth="2.2" />
            {/* points (jittered) */}
            {g.scores.map((s, j) => {
              const jx = cx + ((j % 5) - 2) * 3.2;
              return <circle key={j} cx={jx} cy={y(s)} r="1.5" fill={col} fillOpacity="0.5" />;
            })}
            <text x={cx} y={H - m.b + 16} textAnchor="middle" className={`${labelText} font-mono`} fontSize="9">{g.short}</text>
            <text x={cx} y={H - m.b + 28} textAnchor="middle" className={`${tickText} font-mono`} fontSize="8">n={g.scores.length}</text>
          </g>
        );
      })}
      <text x={12} y={m.t + ih / 2} textAnchor="middle" transform={`rotate(-90 12 ${m.t + ih / 2})`} className={`${labelText} font-mono`} fontSize="9" letterSpacing="0.5">MEASURED SCORE</text>
    </svg>
  );
}

// ====== Scatter: claimed vs measured (1-10 scale) ==========================
function ScatterPlot({ rows }) {
  const W = 520, H = 340, m = { t: 24, r: 24, b: 48, l: 52 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const maxScore = 10;

  // Filter to primary publishers only
  const filteredRows = rows.filter(r => PRIMARY_PUBLISHERS.includes(r.publisher));

  // Map score to coordinate
  const x = (v) => m.l + ((v - 1) / (maxScore - 1)) * iw;
  const y = (v) => m.t + ih - ((v - 1) / (maxScore - 1)) * ih;

  // Aggregate counts per (claimedScore, measuredScore) cell
  const cells = {};
  filteredRows.forEach((r) => {
    const key = `${r.claimedScore}|${r.measuredScore}`;
    cells[key] = (cells[key] || 0) + 1;
  });
  const maxC = Math.max(1, ...Object.values(cells));

  const ticks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  // Mismatch colors using palette
  const getMismatchColor = (mismatch) => {
    if (mismatch === 0) return PALETTE.lightGreen;      // Accurate
    if (mismatch > 0) return PALETTE.indiaGreen;         // Underrated (harder than claimed)
    return PALETTE.frozenWater;                          // Overrated (easier than claimed)
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block">
      {/* Grid lines */}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} y1={m.t} x2={x(t)} y2={m.t + ih} className={axisStroke} strokeWidth="1" opacity="0.4" />
          <line x1={m.l} y1={y(t)} x2={m.l + iw} y2={y(t)} className={axisStroke} strokeWidth="1" opacity="0.4" />
        </g>
      ))}
      {/* Diagonal agreement line */}
      <line x1={x(1)} y1={y(1)} x2={x(10)} y2={y(10)} stroke={PALETTE.pearlAqua} strokeWidth="2" strokeDasharray="6 4" opacity="0.7" />
      <text x={x(8) + 12} y={y(8) - 8} fill={PALETTE.brightFern} className="font-mono" fontSize="8">perfect agreement</text>
      {/* Points */}
      {Object.entries(cells).map(([key, n]) => {
        const [cl, me] = key.split("|").map(Number);
        const mismatch = me - cl;
        const color = getMismatchColor(mismatch);
        const rad = 6 + (n / maxC) * 14;
        return (
          <g key={key}>
            <circle cx={x(cl)} cy={y(me)} r={rad} fill={color} fillOpacity="0.3" stroke={color} strokeWidth="1.5" />
            <text x={x(cl)} y={y(me) + 3.5} textAnchor="middle" className="fill-slate-700 dark:fill-slate-200 font-mono" fontSize="10" fontWeight="600">{n}</text>
          </g>
        );
      })}
      {/* Axis labels */}
      {ticks.map((t) => (
        <g key={t}>
          <text x={x(t)} y={H - m.b + 16} textAnchor="middle" className={`${tickText} font-mono`} fontSize="9">{t}</text>
          <text x={m.l - 10} y={y(t) + 3} textAnchor="end" className={`${tickText} font-mono`} fontSize="9">{t}</text>
        </g>
      ))}
      <text x={m.l + iw / 2} y={H - 6} textAnchor="middle" className={`${labelText} font-mono`} fontSize="10" letterSpacing="0.5">CLAIMED SCORE</text>
      <text x={14} y={m.t + ih / 2} textAnchor="middle" transform={`rotate(-90 14 ${m.t + ih / 2})`} className={`${labelText} font-mono`} fontSize="10" letterSpacing="0.5">MEASURED SCORE</text>
      {/* Legend */}
      <g transform={`translate(${W - m.r - 90}, ${m.t})`}>
        <rect x="-4" y="-4" width="86" height="58" rx="4" className="fill-white/80 dark:fill-slate-900/80" />
        <circle cx="6" cy="8" r="5" fill={PALETTE.lightGreen} fillOpacity="0.4" stroke={PALETTE.lightGreen} strokeWidth="1" />
        <text x="18" y="11" className={`${tickText} font-mono`} fontSize="8">Accurate</text>
        <circle cx="6" cy="24" r="5" fill={PALETTE.indiaGreen} fillOpacity="0.4" stroke={PALETTE.indiaGreen} strokeWidth="1" />
        <text x="18" y="27" className={`${tickText} font-mono`} fontSize="8">Underrated</text>
        <circle cx="6" cy="40" r="5" fill={PALETTE.frozenWater} fillOpacity="0.4" stroke={PALETTE.pearlAqua} strokeWidth="1" />
        <text x="18" y="43" className={`${tickText} font-mono`} fontSize="8">Overrated</text>
      </g>
    </svg>
  );
}

// ====== Heatmap: Publisher × Difficulty (Unified Ordering) ==================
function Heatmap({ rows, publishers }) {
  const D = window.SudokuData;
  const W = 580, H = 260, m = { t: 16, r: 16, b: 70, l: 80 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;

  // Filter to primary publishers only
  const filteredPubs = publishers.filter(p => PRIMARY_PUBLISHERS.includes(p));

  // Use unified difficulty ordering - only include difficulties that exist in data
  const allDiffsInData = new Set();
  filteredPubs.forEach((p) => {
    (D.diffsFor(p) || []).forEach((d) => allDiffsInData.add(d));
  });

  // Filter unified order to only include difficulties that appear in data
  const orderedDiffs = UNIFIED_DIFFICULTY_ORDER.filter(d => allDiffsInData.has(d));

  // Build data matrix: publisher -> difficulty -> { count, avgMismatch, accuracy }
  const matrix = {};
  filteredPubs.forEach((p) => {
    matrix[p] = {};
    orderedDiffs.forEach((d) => {
      const matches = rows.filter((r) => r.publisher === p && r.claimed === d);
      if (matches.length > 0) {
        const accurate = matches.filter((r) => r.mismatch === 0).length;
        matrix[p][d] = {
          n: matches.length,
          avgMismatch: matches.reduce((a, b) => a + b.mismatch, 0) / matches.length,
          accuracy: accurate / matches.length,
        };
      }
    });
  });

  const activePubs = filteredPubs.filter((p) => Object.keys(matrix[p]).length > 0);

  const cellW = iw / Math.max(1, orderedDiffs.length);
  const cellH = ih / Math.max(1, activePubs.length);

  // Color scale using new palette:
  // Negative mismatch (overrated/easier): cool tones (Frozen Water, Pearl Aqua)
  // Zero mismatch (accurate): neutral (Light Green)
  // Positive mismatch (underrated/harder): warm greens (Bright Fern, India Green)
  const mismatchColor = (avg) => {
    if (avg > 2) return PALETTE.indiaGreen;      // Very underrated
    if (avg > 1) return PALETTE.brightFern;      // Underrated
    if (avg > 0.3) return PALETTE.lightGreen;    // Slightly underrated
    if (avg > -0.3) return PALETTE.pearlAqua;    // Accurate (neutral)
    if (avg > -1) return PALETTE.pearlAqua;      // Slightly overrated
    if (avg > -2) return PALETTE.frozenWater;    // Overrated
    return PALETTE.frozenWater;                   // Very overrated
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block">
      {/* Empty cells background (for publishers without certain difficulties) */}
      {activePubs.map((p, pi) => (
        orderedDiffs.map((d, di) => {
          const cx = m.l + di * cellW;
          const cy = m.t + pi * cellH;
          // Always draw a light background
          return (
            <rect key={`bg-${p}-${d}`} x={cx + 1} y={cy + 1} width={cellW - 2} height={cellH - 2} rx="3"
                  className="fill-slate-50 dark:fill-slate-800/30" />
          );
        })
      ))}
      {/* Data cells */}
      {activePubs.map((p, pi) => (
        orderedDiffs.map((d, di) => {
          const cell = matrix[p][d];
          if (!cell) return null;
          const cx = m.l + di * cellW;
          const cy = m.t + pi * cellH;
          return (
            <g key={`${p}-${d}`}>
              <rect x={cx + 2} y={cy + 2} width={cellW - 4} height={cellH - 4} rx="4" fill={mismatchColor(cell.avgMismatch)} fillOpacity="0.75" />
              <text x={cx + cellW / 2} y={cy + cellH / 2 - 2} textAnchor="middle" className="fill-slate-800 dark:fill-white font-mono" fontSize="10" fontWeight="600">
                {cell.avgMismatch >= 0 ? "+" : ""}{cell.avgMismatch.toFixed(1)}
              </text>
              <text x={cx + cellW / 2} y={cy + cellH / 2 + 10} textAnchor="middle" className="fill-slate-600 dark:fill-slate-300 font-mono" fontSize="7">
                n={cell.n}
              </text>
            </g>
          );
        })
      ))}
      {/* Row labels (publishers) */}
      {activePubs.map((p, i) => (
        <text key={p} x={m.l - 6} y={m.t + i * cellH + cellH / 2 + 3} textAnchor="end" className={`${labelText} font-mono`} fontSize="9">
          {D.SUBMIT_PUBLISHER_SHORT[p] || p}
        </text>
      ))}
      {/* Column labels (difficulties) - rotated for readability */}
      {orderedDiffs.map((d, i) => {
        const labelX = m.l + i * cellW + cellW / 2;
        const labelY = H - m.b + 14;
        const rotateOriginX = labelX + 20;
        return (
          <text key={d} x={labelX} y={labelY} textAnchor="start" className={`${labelText} font-mono`} fontSize="5"
                transform={`rotate(-35 ${rotateOriginX} ${labelY})`}>
            {d}
          </text>
        );
      })}
      {/* Legend */}
      <g transform={`translate(${W / 2 - 40}, ${H - 20})`}>
        <text x="0" y="0" className={`${tickText} font-mono`} fontSize="8">Mismatch:</text>
        <rect x="52" y="-8" width="14" height="10" rx="2" fill={PALETTE.indiaGreen} fillOpacity="0.75" />
        <text x="68" y="0" className={`${tickText} font-mono`} fontSize="7">+under</text>
        <rect x="105" y="-8" width="14" height="10" rx="2" fill={PALETTE.pearlAqua} fillOpacity="0.75" />
        <text x="120" y="0" className={`${tickText} font-mono`} fontSize="7">≈0</text>
        <rect x="140" y="-8" width="14" height="10" rx="2" fill={PALETTE.frozenWater} fillOpacity="0.75" />
        <text x="155" y="0" className={`${tickText} font-mono`} fontSize="7">-over</text>
      </g>
    </svg>
  );
}

// ====== Publisher Accuracy Bar Chart =======================================
function AccuracyBar({ rows, publishers }) {
  const D = window.SudokuData;
  const W = 520, H = 200, m = { t: 16, r: 16, b: 40, l: 80 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;

  // Filter to primary publishers only
  const filteredPubs = publishers.filter(p => PRIMARY_PUBLISHERS.includes(p));

  // Calculate accuracy per publisher
  const pubStats = filteredPubs.map((p) => {
    const matches = rows.filter((r) => r.publisher === p);
    if (matches.length === 0) return null;
    const accurate = matches.filter((r) => r.mismatch === 0).length;
    return {
      publisher: p,
      short: D.SUBMIT_PUBLISHER_SHORT[p] || p,
      n: matches.length,
      accuracy: accurate / matches.length,
      accurate,
      color: PUBLISHER_COLORS[p] || PALETTE.pearlAqua,
    };
  }).filter(Boolean).sort((a, b) => b.accuracy - a.accuracy);

  const barH = Math.min(36, ih / Math.max(1, pubStats.length) - 6);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block">
      {/* Grid lines */}
      {[0, 25, 50, 75, 100].map((t) => {
        const x = m.l + (t / 100) * iw;
        return (
          <g key={t}>
            <line x1={x} y1={m.t} x2={x} y2={m.t + ih} className={axisStroke} strokeWidth="1" opacity="0.4" />
            <text x={x} y={H - m.b + 14} textAnchor="middle" className={`${tickText} font-mono`} fontSize="8">{t}%</text>
          </g>
        );
      })}
      {/* Bars */}
      {pubStats.map((s, i) => {
        const cy = m.t + (i + 0.5) * (ih / pubStats.length);
        const barWidth = s.accuracy * iw;
        return (
          <g key={s.publisher}>
            {/* Background bar */}
            <rect x={m.l} y={cy - barH / 2} width={iw} height={barH} rx="4" className="fill-slate-100 dark:fill-slate-800" />
            {/* Accuracy bar - use publisher color */}
            <rect x={m.l} y={cy - barH / 2} width={barWidth} height={barH} rx="4" fill={s.color} fillOpacity="0.75" />
            {/* Label */}
            <text x={m.l - 6} y={cy + 3} textAnchor="end" className={`${labelText} font-mono`} fontSize="10">{s.short}</text>
            {/* Value */}
            <text x={m.l + barWidth + 6} y={cy + 3} className="fill-slate-700 dark:fill-slate-200 font-mono" fontSize="10" fontWeight="500">
              {Math.round(s.accuracy * 100)}% ({s.accurate}/{s.n})
            </text>
          </g>
        );
      })}
      <text x={m.l + iw / 2} y={H - 4} textAnchor="middle" className={`${labelText} font-mono`} fontSize="9" letterSpacing="0.5">ACCURACY (% EXACT MATCHES)</text>
    </svg>
  );
}

// Legacy Scatter for backward compatibility (using difficulty labels)
function Scatter({ rows }) {
  const W = 520, H = 300, m = { t: 18, r: 18, b: 48, l: 70 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const labels = ["Easy", "Medium", "Hard"];
  const xi = (i) => m.l + (iw / 3) * (i + 0.5);
  const yi = (i) => m.t + ih - (ih / 3) * (i + 0.5);
  const DIFF_IDX = { Easy: 0, Medium: 1, Hard: 2 };

  // aggregate counts per (claimed, measured) cell to size points
  const cells = {};
  rows.forEach((r) => {
    const key = r.claimed + "|" + r.measured;
    cells[key] = (cells[key] || 0) + 1;
  });
  const maxC = Math.max(1, ...Object.values(cells));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="block">
      {/* diagonal agreement reference */}
      <line x1={xi(0)} y1={yi(0)} x2={xi(2)} y2={yi(2)} stroke={PALETTE.pearlAqua} strokeWidth="1" strokeDasharray="4 4" />
      <text x={xi(0) + 14} y={yi(0) - 10} className={`${tickText} font-mono`} fontSize="8">perfect agreement →</text>
      {/* grid cells */}
      {labels.map((_, gx) => labels.map((_, gy) => (
        <line key={`v${gx}${gy}`} x1={m.l + (iw / 3) * gx} y1={m.t} x2={m.l + (iw / 3) * gx} y2={m.t + ih} className={axisStroke} strokeWidth="1" opacity="0.5" />
      )))}
      {[0, 1, 2, 3].map((g) => (
        <g key={g}>
          <line x1={m.l + (iw / 3) * g} y1={m.t} x2={m.l + (iw / 3) * g} y2={m.t + ih} className={axisStroke} strokeWidth="1" opacity="0.5" />
          <line x1={m.l} y1={m.t + (ih / 3) * g} x2={m.l + iw} y2={m.t + (ih / 3) * g} className={axisStroke} strokeWidth="1" opacity="0.5" />
        </g>
      ))}
      {/* points */}
      {Object.entries(cells).map(([key, n]) => {
        const [cl, me] = key.split("|");
        const x = xi(DIFF_IDX[cl]), y = yi(DIFF_IDX[me]);
        const match = cl === me;
        const over = DIFF_IDX[cl] > DIFF_IDX[me];
        const color = match ? PALETTE.lightGreen : over ? PALETTE.frozenWater : PALETTE.indiaGreen;
        const rad = 5 + (n / maxC) * 13;
        return (
          <g key={key}>
            <circle cx={x} cy={y} r={rad} fill={color} fillOpacity="0.25" stroke={color} strokeWidth="1.4" />
            <text x={x} y={y + 3.5} textAnchor="middle" className="fill-slate-700 dark:fill-slate-200 font-mono" fontSize="10" fontWeight="600">{n}</text>
          </g>
        );
      })}
      {/* axis labels */}
      {labels.map((l, i) => (
        <text key={l} x={xi(i)} y={H - m.b + 16} textAnchor="middle" className={`${labelText} font-mono`} fontSize="9">{l}</text>
      ))}
      {labels.map((l, i) => (
        <text key={l} x={m.l - 10} y={yi(i) + 3} textAnchor="end" className={`${labelText} font-mono`} fontSize="9">{l}</text>
      ))}
      <text x={m.l + iw / 2} y={H - 6} textAnchor="middle" className={`${tickText} font-mono`} fontSize="9" letterSpacing="0.5">CLAIMED →</text>
      <text x={16} y={m.t + ih / 2} textAnchor="middle" transform={`rotate(-90 16 ${m.t + ih / 2})`} className={`${tickText} font-mono`} fontSize="9" letterSpacing="0.5">MEASURED →</text>
    </svg>
  );
}

// ---- tick helper -----------------------------------------------------------
function niceTicks(max, count) {
  const step = Math.max(1, Math.ceil(max / count));
  const ticks = [];
  for (let v = 0; v <= step * count; v += step) { ticks.push(v); if (v >= max) break; }
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step);
  return ticks;
}

Object.assign(window, {
  DifficultyGauge,
  Histogram,
  BoxPlot,
  Scatter,
  ScatterPlot,
  Heatmap,
  AccuracyBar,
  // Export constants for use elsewhere
  PALETTE,
  PUBLISHER_COLORS,
  PRIMARY_PUBLISHERS,
  UNIFIED_DIFFICULTY_ORDER
});
