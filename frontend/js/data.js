/* Sample puzzles (real, engine-verified) + deterministic repository dataset.
   Attaches window.SudokuData. Plain JS. */
(function () {
  "use strict";

  const PUBLISHERS = ["The New York Times", "The Times", "The Guardian", "Sudoku.com"];
  const PUBLISHER_SHORT = {
    "The New York Times": "NYT",
    "The Times": "Times",
    "The Guardian": "Guardian",
    "Sudoku.com": "Sudoku.com",
  };

  const DIFFS = ["Easy", "Medium", "Hard"];

  // ======================================================================
  // SUBMIT PAGE — Publisher / claimed-difficulty system (Phase 1 redesign)
  // ======================================================================
  // Publisher dropdown for the Submit page. Selection is mandatory.
  const SUBMIT_PUBLISHERS = ["NYT", "Sudoku.com", "The Guardian", "Times Sudoku", "Others"];
  const SUBMIT_PUBLISHER_SHORT = {
    "NYT": "NYT",
    "Sudoku.com": "Sudoku.com",
    "The Guardian": "Guardian",
    "Times Sudoku": "Times",
    "Others": "Other",
  };

  // Difficulty labels available per publisher. The Submit page difficulty
  // dropdown is populated from this and stays disabled until a publisher is
  // chosen; changing publisher resets the chosen difficulty.
  const DIFF_BY_PUBLISHER = {
    "NYT":          ["Easy", "Medium", "Hard"],
    "Sudoku.com":   ["Easy", "Medium", "Hard", "Expert", "Master", "Extreme"],
    "The Guardian": ["Easy", "Medium", "Hard", "Expert"],
    "Times Sudoku": ["Easy", "Mild", "Moderate", "Difficult", "Fiendish", "Super Fiendish"],
    "Others":       ["Easy", "Medium", "Hard"],
  };

  // Fixed conversion of each publisher's label to a numeric claimed score.
  // These mappings are constant throughout the application.
  const CLAIMED_SCORE = {
    "NYT":          { Easy: 2, Medium: 4, Hard: 6 },
    "Sudoku.com":   { Easy: 2, Medium: 4, Hard: 5, Expert: 7, Master: 8, Extreme: 9 },
    "The Guardian": { Easy: 2, Medium: 4, Hard: 7, Expert: 9 },
    "Times Sudoku": { Easy: 1, Mild: 2, Moderate: 4, Difficult: 6, Fiendish: 9, "Super Fiendish": 10 },
    "Others":       { Easy: 2, Medium: 4, Hard: 6 },
  };

  function diffsFor(publisher) { return DIFF_BY_PUBLISHER[publisher] || []; }
  function claimedScore(publisher, label) {
    const m = CLAIMED_SCORE[publisher];
    return m && m[label] != null ? m[label] : null;
  }

  // Mismatch = Measured Score − Claimed Score. Positive => publisher
  // under-rated the puzzle (it is harder than claimed); negative => over-rated.
  function verdict(mismatch) {
    if (mismatch === 0)  return "Accurate";
    if (mismatch === 1)  return "Slightly Underrated";
    if (mismatch === 2)  return "Moderately Underrated";
    if (mismatch >= 3)   return "Significantly Underrated";
    if (mismatch === -1) return "Slightly Overrated";
    if (mismatch === -2) return "Moderately Overrated";
    return "Significantly Overrated"; // -3 or less
  }

  // Reference copy of the technique-tier scale used by the engine (display).
  const TECHNIQUE_SCALE = [
    { name: "Full House", score: 1 },
    { name: "Naked Single", score: 1 },
    { name: "Hidden Single", score: 2 },
    { name: "Pointing Pair", score: 3 },
    { name: "Box-Line Reduction", score: 3 },
    { name: "Naked Pair / Triple / Quad", score: 4 },
    { name: "Hidden Pair / Triple / Quad", score: 5 },
    { name: "X-Wing", score: 6 },
    { name: "Swordfish", score: 7 },
    { name: "X-Colors", score: 7 },
    { name: "Jellyfish", score: 8 },
    { name: "XY-Wing", score: 9 },
    { name: "W-Wing", score: 9 },
    { name: "Skyscraper", score: 9 },
    { name: "Empty Rectangle", score: 9 },
    { name: "XYZ-Wing", score: 10 },
    { name: "Unique Rectangle", score: 10 },
  ];

  const TECH_BY_TIER = {
    Easy: ["Naked Single", "Hidden Single"],
    Medium: ["Pointing Pair/Triple", "Claiming Pair/Triple", "Naked Pair", "Hidden Pair"],
    Hard: ["Naked Triple", "Hidden Triple", "X-Wing", "XY-Wing", "Trial & Error (backtracking)"],
  };
  const SCORE_RANGE = { Easy: [110, 255], Medium: [260, 515], Hard: [525, 955] };

  // Per-publisher grading character on the 1–10 technique-tier scale.
  // bias > 0 => publisher tends to UNDER-rate (claims easier than measured,
  // so measured > claimed => positive mismatch). bias < 0 => OVER-rates.
  const PROFILE = {
    "NYT":          { bias: 0.1,  noise: 0.9 }, // accurate, tight
    "Sudoku.com":   { bias: -1.6, noise: 1.2 }, // inflates claims (over-rates)
    "The Guardian": { bias: 1.2,  noise: 1.7 }, // under-rates, inconsistent
    "Times Sudoku": { bias: 1.7,  noise: 1.5 }, // under-rates the most
    "Others":       { bias: -0.2, noise: 2.0 }, // mixed / noisy
  };

  // Real, solvable puzzle grids assigned to seed records for the detail view.
  const GRID_POOL = [
    "530070000600195000098000060800060003400803001700020006060000280000419005000080079",
    "300000000970010000600583000200000900500621003008000005000435002000090056000000001",
    "100000569492056108056109240009640801064010000218035604040500016905061402621000005",
    "800000000003600000070090200050007000000045700000100030001000068008500010090000400",
    "000000907000420180000705026100904000050000040000507009920108000034059000507000000",
    "020810740700003100090002805009040087400208003160030200302700060005600008076051090",
  ];

  // Representative hardest technique for a measured score (1–10).
  function techForScore(score, rnd) {
    const matches = TECHNIQUE_SCALE.filter((t) => t.score === score);
    if (!matches.length) return "Advanced Out-of-Scope Technique";
    const i = rnd ? Math.floor(rnd() * matches.length) : 0;
    return matches[i].name;
  }

  // ---- Deterministic RNG --------------------------------------------------
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function generate(n, seed) {
    const rnd = mulberry32(seed || 20260531);
    const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    const records = [];
    for (let k = 0; k < n; k++) {
      const publisher = pick(SUBMIT_PUBLISHERS);
      const prof = PROFILE[publisher];
      // Pick the publisher's claimed label, then derive measured score from it.
      const labels = DIFF_BY_PUBLISHER[publisher];
      const claimed = pick(labels);
      const cScore = claimedScore(publisher, claimed);
      const drift = prof.bias + (rnd() - 0.5) * 2 * prof.noise;
      const measuredScore = clamp(Math.round(cScore + drift), 1, 10);
      const mismatch = measuredScore - cScore;
      const tech = techForScore(measuredScore, rnd);
      const clues = clamp(38 - measuredScore - Math.floor(rnd() * 3), 22, 36);
      const d = new Date(2026, 0, 1 + Math.floor(rnd() * 150));

      records.push({
        id: "SDK-" + String(1042 + k).padStart(4, "0"),
        publisher,
        publisherShort: SUBMIT_PUBLISHER_SHORT[publisher],
        claimed,
        claimedScore: cScore,
        measuredScore,
        mismatch,
        verdict: verdict(mismatch),
        tech,
        clues,
        grid: GRID_POOL[k % GRID_POOL.length],
        date: d.toISOString().slice(0, 10),
        ts: d.toISOString(),
        source: "seed",
      });
    }
    return records;
  }

  const REPO = generate(36);

  // ---- Analytics helpers --------------------------------------------------
  const DIFF_IDX = { Easy: 0, Medium: 1, Hard: 2 };

  function pearson(xs, ys) {
    const n = xs.length;
    if (n < 2) return 0;
    const mx = xs.reduce((a, b) => a + b, 0) / n;
    const my = ys.reduce((a, b) => a + b, 0) / n;
    let num = 0, dx = 0, dy = 0;
    for (let i = 0; i < n; i++) { const a = xs[i] - mx, b = ys[i] - my; num += a * b; dx += a * a; dy += b * b; }
    return dx && dy ? num / Math.sqrt(dx * dy) : 0;
  }

  // Analytics over the Technique-Tier model. mismatch = measured − claimed:
  // positive => under-rated by publisher, negative => over-rated.
  function analytics(rows) {
    const n = rows.length;
    const r = pearson(rows.map((x) => x.claimedScore), rows.map((x) => x.measuredScore));
    const accurate = rows.filter((x) => x.mismatch === 0).length;
    const agreement = n ? accurate / n : 0;
    const over = rows.filter((x) => x.mismatch < 0).length;
    const under = rows.filter((x) => x.mismatch > 0).length;
    const meanMeasured = n ? rows.reduce((a, b) => a + b.measuredScore, 0) / n : 0;
    const meanAbsMismatch = n ? rows.reduce((a, b) => a + Math.abs(b.mismatch), 0) / n : 0;

    const byPub = {};
    rows.forEach((x) => { (byPub[x.publisher] = byPub[x.publisher] || []).push(x); });
    const leaderboard = Object.entries(byPub).map(([pub, list]) => {
      const acc = list.filter((x) => x.mismatch === 0).length / list.length;
      const o = list.filter((x) => x.mismatch < 0).length;
      const u = list.filter((x) => x.mismatch > 0).length;
      const meanMis = list.reduce((a, b) => a + b.mismatch, 0) / list.length;
      return {
        publisher: pub,
        short: SUBMIT_PUBLISHER_SHORT[pub] || pub,
        n: list.length,
        accuracy: acc,
        over: o, under: u,
        meanMismatch: meanMis,
        tendency: meanMis > 0.4 ? "under-rates" : meanMis < -0.4 ? "over-rates" : "balanced",
      };
    }).sort((a, b) => b.accuracy - a.accuracy);

    return { pearson: r, agreement, accurate, over, under, meanMeasured, meanAbsMismatch, leaderboard, n };
  }

  window.SudokuData = {
    PUBLISHERS, PUBLISHER_SHORT, DIFFS, REPO, generate, analytics, pearson, DIFF_IDX,
    // Submit-page + Repository (Phase 1/2) system
    SUBMIT_PUBLISHERS, SUBMIT_PUBLISHER_SHORT, DIFF_BY_PUBLISHER, CLAIMED_SCORE,
    TECHNIQUE_SCALE, GRID_POOL, diffsFor, claimedScore, verdict, techForScore,
  };
})();
