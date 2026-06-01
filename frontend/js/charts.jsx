/* Hand-built SVG charts — academic, minimal. Exports to window.
   Each chart uses a fixed viewBox and scales to its container width. */

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
  // 180deg (left) -> 360/0deg (right). map frac to 180..360
  const ang = 180 + frac * 180;
  const bands = [
    { from: 0, to: 0.255, color: "#059669" },
    { from: 0.255, to: 0.515, color: "#d97706" },
    { from: 0.515, to: 1, color: "#e11d48" },
  ];
  const [nx, ny] = polar(cx, cy, r - 26, ang);
  const dColor = { Easy: "#059669", Medium: "#d97706", Hard: "#e11d48" }[difficulty] || "#0d9488";

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
  const bandColor = (lo) => (lo < 255 ? "#059669" : lo < 515 ? "#d97706" : "#e11d48");
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
  const groups = publishers.map((p) => {
    const scores = rows.filter((r) => r.publisher === p).map((r) => r.measuredScore);
    return { p, short: window.SudokuData.SUBMIT_PUBLISHER_SHORT[p] || p, scores };
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
        const col = "#0d9488";
        return (
          <g key={g.p}>
            {/* whiskers */}
            <line x1={cx} y1={y(Q.min)} x2={cx} y2={y(Q.max)} className="stroke-slate-400 dark:stroke-slate-500" strokeWidth="1" />
            <line x1={cx - 8} y1={y(Q.min)} x2={cx + 8} y2={y(Q.min)} className="stroke-slate-400 dark:stroke-slate-500" strokeWidth="1" />
            <line x1={cx - 8} y1={y(Q.max)} x2={cx + 8} y2={y(Q.max)} className="stroke-slate-400 dark:stroke-slate-500" strokeWidth="1" />
            {/* box */}
            <rect x={cx - boxW / 2} y={y(Q.q3)} width={boxW} height={Math.max(1, y(Q.q1) - y(Q.q3))} rx="2" fill={col} fillOpacity="0.14" stroke={col} strokeWidth="1.4" />
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

// ====== Scatter: claimed vs measured =======================================
function Scatter({ rows }) {
  const W = 520, H = 300, m = { t: 18, r: 18, b: 48, l: 70 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const labels = ["Easy", "Medium", "Hard"];
  const xi = (i) => m.l + (iw / 3) * (i + 0.5);
  const yi = (i) => m.t + ih - (ih / 3) * (i + 0.5);
  const DIFF_IDX = window.SudokuData.DIFF_IDX;

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
      <line x1={xi(0)} y1={yi(0)} x2={xi(2)} y2={yi(2)} className="stroke-slate-300 dark:stroke-slate-600" strokeWidth="1" strokeDasharray="4 4" />
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
        const color = match ? "#0d9488" : over ? "#e11d48" : "#d97706";
        const rad = 5 + (n / maxC) * 13;
        return (
          <g key={key}>
            <circle cx={x} cy={y} r={rad} fill={color} fillOpacity="0.16" stroke={color} strokeWidth="1.4" />
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

Object.assign(window, { DifficultyGauge, Histogram, BoxPlot, Scatter });
