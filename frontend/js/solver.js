/* Sudoku Difficulty Validator — logical solver + scoring engine.
   Applies human techniques in increasing order of difficulty, records each
   step, and derives a composite difficulty score + measured difficulty band.
   Attaches window.SudokuEngine. Plain JS (no JSX). */
(function () {
  "use strict";

  // ---- Geometry -----------------------------------------------------------
  const rc = (i) => [Math.floor(i / 9), i % 9];
  const boxOf = (r, c) => Math.floor(r / 3) * 3 + Math.floor(c / 3);

  const unitRows = [], unitCols = [], unitBoxes = [];
  for (let r = 0; r < 9; r++) { unitRows.push([]); for (let c = 0; c < 9; c++) unitRows[r].push(r * 9 + c); }
  for (let c = 0; c < 9; c++) { unitCols.push([]); for (let r = 0; r < 9; r++) unitCols[c].push(r * 9 + c); }
  for (let b = 0; b < 9; b++) {
    unitBoxes.push([]);
    const br = Math.floor(b / 3) * 3, bc = (b % 3) * 3;
    for (let dr = 0; dr < 3; dr++) for (let dc = 0; dc < 3; dc++) unitBoxes[b].push((br + dr) * 9 + (bc + dc));
  }
  const allUnits = [...unitRows, ...unitCols, ...unitBoxes];

  const peers = [];
  for (let i = 0; i < 81; i++) {
    const [r, c] = rc(i), b = boxOf(r, c);
    const s = new Set();
    unitRows[r].forEach((x) => s.add(x));
    unitCols[c].forEach((x) => s.add(x));
    unitBoxes[b].forEach((x) => s.add(x));
    s.delete(i);
    peers.push(s);
  }

  // ---- Technique catalogue ------------------------------------------------
  // tier: 1 = Easy, 2 = Medium, 3 = Hard (legacy band, used by repository).
  // score: position on the Technique-Tier Classification scale (1–10). The
  //        measured difficulty is the highest score encountered.
  const TECH = {
    nakedSingle:  { key: "nakedSingle",  name: "Naked Single",         cost: 8,   tier: 1, score: 1 },
    hiddenSingle: { key: "hiddenSingle", name: "Hidden Single",        cost: 14,  tier: 1, score: 2 },
    pointing:     { key: "pointing",     name: "Pointing Pair",        cost: 42,  tier: 2, score: 3 },
    claiming:     { key: "claiming",     name: "Box-Line Reduction",   cost: 48,  tier: 2, score: 3 },
    nakedPair:    { key: "nakedPair",    name: "Naked Pair",           cost: 60,  tier: 2, score: 4 },
    hiddenPair:   { key: "hiddenPair",   name: "Hidden Pair",          cost: 72,  tier: 2, score: 5 },
    nakedTriple:  { key: "nakedTriple",  name: "Naked Triple",         cost: 92,  tier: 3, score: 4 },
    hiddenTriple: { key: "hiddenTriple", name: "Hidden Triple",        cost: 116, tier: 3, score: 5 },
    xWing:        { key: "xWing",        name: "X-Wing",               cost: 165, tier: 3, score: 6 },
    xyWing:       { key: "xyWing",       name: "XY-Wing",              cost: 190, tier: 3, score: 9 },
    backtrack:    { key: "backtrack",    name: "Advanced Out-of-Scope Technique", cost: 340, tier: 3, score: 10 },
  };

  // ---- Parsing / validation ----------------------------------------------
  function parse(str) {
    const b = new Array(81).fill(0);
    if (Array.isArray(str)) { for (let i = 0; i < 81; i++) b[i] = str[i] | 0; return b; }
    const clean = String(str).replace(/[^0-9.]/g, "").replace(/\./g, "0");
    for (let i = 0; i < 81 && i < clean.length; i++) b[i] = clean[i] === "0" ? 0 : +clean[i];
    return b;
  }

  function findConflicts(board) {
    const bad = new Set();
    for (const unit of allUnits) {
      const seen = {};
      for (const i of unit) {
        const v = board[i];
        if (!v) continue;
        if (seen[v] != null) { bad.add(i); bad.add(seen[v]); }
        else seen[v] = i;
      }
    }
    return bad; // set of conflicting cell indices
  }

  function computeCandidates(board) {
    const cand = new Array(81);
    for (let i = 0; i < 81; i++) {
      if (board[i]) { cand[i] = new Set(); continue; }
      const s = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9]);
      peers[i].forEach((p) => { if (board[p]) s.delete(board[p]); });
      cand[i] = s;
    }
    return cand;
  }

  const isSolved = (board) => board.every((v) => v !== 0);

  // ---- Backtracking solver (uniqueness check + fallback) ------------------
  function countSolutions(board0, limit) {
    const board = board0.slice();
    let count = 0;
    function bt() {
      if (count >= limit) return;
      let best = -1, bestCand = null;
      for (let i = 0; i < 81; i++) {
        if (board[i]) continue;
        const opts = [];
        for (let v = 1; v <= 9; v++) {
          let ok = true;
          for (const p of peers[i]) if (board[p] === v) { ok = false; break; }
          if (ok) opts.push(v);
        }
        if (opts.length === 0) return;
        if (bestCand === null || opts.length < bestCand.length) { best = i; bestCand = opts; }
      }
      if (best === -1) { count++; return; }
      for (const v of bestCand) { board[best] = v; bt(); if (count >= limit) { board[best] = 0; return; } board[best] = 0; }
    }
    bt();
    return count;
  }

  function solveFull(board0) {
    const board = board0.slice();
    function bt() {
      let best = -1, bestCand = null;
      for (let i = 0; i < 81; i++) {
        if (board[i]) continue;
        const opts = [];
        for (let v = 1; v <= 9; v++) {
          let ok = true;
          for (const p of peers[i]) if (board[p] === v) { ok = false; break; }
          if (ok) opts.push(v);
        }
        if (opts.length === 0) return false;
        if (bestCand === null || opts.length < bestCand.length) { best = i; bestCand = opts; }
      }
      if (best === -1) return true;
      for (const v of bestCand) { board[best] = v; if (bt()) return true; board[best] = 0; }
      return false;
    }
    return bt() ? board : null;
  }

  // ---- Mutation helper ----------------------------------------------------
  function place(board, cand, i, v) {
    board[i] = v;
    cand[i] = new Set();
    peers[i].forEach((p) => cand[p].delete(v));
  }

  function combinations(arr, k) {
    const res = [];
    (function go(start, combo) {
      if (combo.length === k) { res.push(combo.slice()); return; }
      for (let i = start; i < arr.length; i++) { combo.push(arr[i]); go(i + 1, combo); combo.pop(); }
    })(0, []);
    return res;
  }

  // ---- Techniques (each returns an action object or null) -----------------
  function tNakedSingle(board, cand) {
    for (let i = 0; i < 81; i++) {
      if (!board[i] && cand[i].size === 1) {
        const v = [...cand[i]][0];
        return { tech: "nakedSingle", placements: [{ i, v }], eliminations: [] };
      }
    }
    return null;
  }

  function tHiddenSingle(board, cand) {
    for (const unit of allUnits) {
      for (let v = 1; v <= 9; v++) {
        let spot = -1, cnt = 0, already = false;
        for (const i of unit) {
          if (board[i] === v) { already = true; break; }
          if (!board[i] && cand[i].has(v)) { cnt++; spot = i; }
        }
        if (!already && cnt === 1) return { tech: "hiddenSingle", placements: [{ i: spot, v }], eliminations: [] };
      }
    }
    return null;
  }

  // Pointing: candidate confined to one box AND one line -> eliminate from line outside box.
  function tPointing(board, cand) {
    for (let b = 0; b < 9; b++) {
      const cells = unitBoxes[b];
      for (let v = 1; v <= 9; v++) {
        const spots = cells.filter((i) => !board[i] && cand[i].has(v));
        if (spots.length < 2) continue;
        const rows = new Set(spots.map((i) => Math.floor(i / 9)));
        const cols = new Set(spots.map((i) => i % 9));
        const elim = [];
        if (rows.size === 1) {
          const r = [...rows][0];
          for (const i of unitRows[r]) if (!cells.includes(i) && !board[i] && cand[i].has(v)) elim.push({ i, v });
        } else if (cols.size === 1) {
          const c = [...cols][0];
          for (const i of unitCols[c]) if (!cells.includes(i) && !board[i] && cand[i].has(v)) elim.push({ i, v });
        }
        if (elim.length) return { tech: "pointing", placements: [], eliminations: elim };
      }
    }
    return null;
  }

  // Claiming: candidate in a line confined to one box -> eliminate from rest of box.
  function tClaiming(board, cand) {
    const lines = [...unitRows, ...unitCols];
    for (const line of lines) {
      for (let v = 1; v <= 9; v++) {
        const spots = line.filter((i) => !board[i] && cand[i].has(v));
        if (spots.length < 2) continue;
        const boxes = new Set(spots.map((i) => boxOf(Math.floor(i / 9), i % 9)));
        if (boxes.size !== 1) continue;
        const b = [...boxes][0];
        const elim = [];
        for (const i of unitBoxes[b]) if (!line.includes(i) && !board[i] && cand[i].has(v)) elim.push({ i, v });
        if (elim.length) return { tech: "claiming", placements: [], eliminations: elim };
      }
    }
    return null;
  }

  function tNakedSet(board, cand, k, techKey) {
    for (const unit of allUnits) {
      const cells = unit.filter((i) => !board[i] && cand[i].size >= 2 && cand[i].size <= k);
      if (cells.length < k) continue;
      for (const combo of combinations(cells, k)) {
        const union = new Set();
        combo.forEach((i) => cand[i].forEach((v) => union.add(v)));
        if (union.size !== k) continue;
        const elim = [];
        for (const i of unit) {
          if (combo.includes(i) || board[i]) continue;
          union.forEach((v) => { if (cand[i].has(v)) elim.push({ i, v }); });
        }
        if (elim.length) return { tech: techKey, placements: [], eliminations: elim };
      }
    }
    return null;
  }

  function tHiddenSet(board, cand, k, techKey) {
    for (const unit of allUnits) {
      const present = [];
      for (let v = 1; v <= 9; v++) {
        const spots = unit.filter((i) => !board[i] && cand[i].has(v));
        if (spots.length >= 1 && spots.length <= k) present.push({ v, spots });
      }
      if (present.length < k) continue;
      for (const combo of combinations(present, k)) {
        const cellSet = new Set();
        combo.forEach((p) => p.spots.forEach((i) => cellSet.add(i)));
        if (cellSet.size !== k) continue;
        const digits = new Set(combo.map((p) => p.v));
        const elim = [];
        cellSet.forEach((i) => { cand[i].forEach((v) => { if (!digits.has(v)) elim.push({ i, v }); }); });
        if (elim.length) return { tech: techKey, placements: [], eliminations: elim };
      }
    }
    return null;
  }

  // X-Wing on rows and columns.
  function tXWing(board, cand) {
    for (let v = 1; v <= 9; v++) {
      // row-based
      const rowSpots = [];
      for (let r = 0; r < 9; r++) {
        const cols = unitRows[r].filter((i) => !board[i] && cand[i].has(v)).map((i) => i % 9);
        rowSpots.push(cols);
      }
      for (let r1 = 0; r1 < 9; r1++) {
        if (rowSpots[r1].length !== 2) continue;
        for (let r2 = r1 + 1; r2 < 9; r2++) {
          if (rowSpots[r2].length !== 2) continue;
          if (rowSpots[r1][0] === rowSpots[r2][0] && rowSpots[r1][1] === rowSpots[r2][1]) {
            const [c1, c2] = rowSpots[r1];
            const elim = [];
            for (let r = 0; r < 9; r++) {
              if (r === r1 || r === r2) continue;
              [c1, c2].forEach((c) => { const i = r * 9 + c; if (!board[i] && cand[i].has(v)) elim.push({ i, v }); });
            }
            if (elim.length) return { tech: "xWing", placements: [], eliminations: elim };
          }
        }
      }
      // column-based
      const colSpots = [];
      for (let c = 0; c < 9; c++) {
        const rows = unitCols[c].filter((i) => !board[i] && cand[i].has(v)).map((i) => Math.floor(i / 9));
        colSpots.push(rows);
      }
      for (let a = 0; a < 9; a++) {
        if (colSpots[a].length !== 2) continue;
        for (let b = a + 1; b < 9; b++) {
          if (colSpots[b].length !== 2) continue;
          if (colSpots[a][0] === colSpots[b][0] && colSpots[a][1] === colSpots[b][1]) {
            const [r1, r2] = colSpots[a];
            const elim = [];
            for (let c = 0; c < 9; c++) {
              if (c === a || c === b) continue;
              [r1, r2].forEach((r) => { const i = r * 9 + c; if (!board[i] && cand[i].has(v)) elim.push({ i, v }); });
            }
            if (elim.length) return { tech: "xWing", placements: [], eliminations: elim };
          }
        }
      }
    }
    return null;
  }

  // XY-Wing.
  function tXYWing(board, cand) {
    const bival = [];
    for (let i = 0; i < 81; i++) if (!board[i] && cand[i].size === 2) bival.push(i);
    for (const piv of bival) {
      const [x, y] = [...cand[piv]];
      for (const p1 of bival) {
        if (p1 === piv || !peers[piv].has(p1)) continue;
        if (!cand[p1].has(x)) continue;
        const z1 = [...cand[p1]].find((d) => d !== x);
        if (z1 == null || z1 === y) continue;
        for (const p2 of bival) {
          if (p2 === piv || p2 === p1 || !peers[piv].has(p2)) continue;
          if (!cand[p2].has(y) || !cand[p2].has(z1)) continue;
          if (![...cand[p2]].every((d) => d === y || d === z1)) continue;
          const z = z1;
          const elim = [];
          for (let i = 0; i < 81; i++) {
            if (i === p1 || i === p2 || board[i]) continue;
            if (peers[p1].has(i) && peers[p2].has(i) && cand[i].has(z)) elim.push({ i, v: z });
          }
          if (elim.length) return { tech: "xyWing", placements: [], eliminations: elim };
        }
      }
    }
    return null;
  }

  const ORDER = [
    tNakedSingle,
    tHiddenSingle,
    tPointing,
    tClaiming,
    (b, c) => tNakedSet(b, c, 2, "nakedPair"),
    (b, c) => tHiddenSet(b, c, 2, "hiddenPair"),
    (b, c) => tNakedSet(b, c, 3, "nakedTriple"),
    (b, c) => tHiddenSet(b, c, 3, "hiddenTriple"),
    tXWing,
    tXYWing,
  ];

  function applyResult(board, cand, res) {
    for (const p of res.placements) place(board, cand, p.i, p.v);
    for (const e of res.eliminations) cand[e.i].delete(e.v);
  }

  // ---- Main analysis ------------------------------------------------------
  function analyze(input) {
    const board = parse(input);
    const filled = board.filter((v) => v).length;
    const conflicts = findConflicts(board);

    if (conflicts.size) {
      return { ok: false, reason: "conflict", message: "The grid has duplicate values in a row, column, or box.", conflicts: [...conflicts] };
    }
    if (filled < 17) {
      return { ok: false, reason: "insufficient", message: "A valid Sudoku needs at least 17 clues. Add more givens to analyze." };
    }

    const nSol = countSolutions(board, 2);
    if (nSol === 0) return { ok: false, reason: "unsolvable", message: "This puzzle has no solution." };
    if (nSol > 1) return { ok: false, reason: "nonunique", message: "This puzzle has multiple solutions — it is not a valid Sudoku." };

    const work = board.slice();
    const cand = computeCandidates(work);
    const steps = [];
    let guard = 0;
    while (!isSolved(work) && guard++ < 1000) {
      let progressed = false;
      for (let t = 0; t < ORDER.length; t++) {
        const res = ORDER[t](work, cand);
        if (res) { applyResult(work, cand, res); steps.push(res); progressed = true; break; }
      }
      if (!progressed) break;
    }

    const solvedByLogic = isSolved(work);
    const counts = {};
    let total = 0, maxCost = 0, maxTier = 1, hardest = TECH.nakedSingle;
    let maxScore = 0, hardestByScore = TECH.nakedSingle;
    for (const s of steps) {
      const m = TECH[s.tech];
      counts[s.tech] = (counts[s.tech] || 0) + 1;
      total += m.cost;
      if (m.cost > maxCost) { maxCost = m.cost; hardest = m; }
      if (m.tier > maxTier) maxTier = m.tier;
      if (m.score > maxScore) { maxScore = m.score; hardestByScore = m; }
    }

    // Out-of-scope: the puzzle could not be cracked with the catalogued
    // techniques, so an advanced technique beyond the scale was required.
    let requiresGuessing = false, outOfScope = false;
    if (!solvedByLogic) {
      requiresGuessing = true;
      outOfScope = true;
      counts.backtrack = 1;
      total += TECH.backtrack.cost;
      maxCost = TECH.backtrack.cost;
      maxTier = 3;
      hardest = TECH.backtrack;
      maxScore = TECH.backtrack.score; // 10
      hardestByScore = TECH.backtrack;
    }

    // Technique-Tier Classification: measured difficulty = highest score seen.
    const measuredScore = maxScore || 1;
    const hardestTech = outOfScope
      ? { key: "outOfScope", name: "Advanced Out-of-Scope Technique", score: 10 }
      : { key: hardestByScore.key, name: hardestByScore.name, score: hardestByScore.score };

    const composite = Math.round(maxCost * 2.4 + total * 0.32);
    const difficulty = maxTier === 1 ? "Easy" : maxTier === 2 ? "Medium" : "Hard";

    const order = ["nakedSingle", "hiddenSingle", "pointing", "claiming", "nakedPair", "hiddenPair", "nakedTriple", "hiddenTriple", "xWing", "xyWing", "backtrack"];
    const breakdown = order.filter((k) => counts[k]).map((k) => {
      const m = TECH[k];
      return { key: k, name: m.name, tier: m.tier, score: m.score, count: counts[k], cost: m.cost, total: m.cost * counts[k] };
    });

    const solution = solveFull(board);

    return {
      ok: true,
      difficulty,
      composite,
      maxScore: 1000,
      // Technique-Tier Classification (Phase 1 model)
      measuredScore,
      hardestTech,
      outOfScope,
      breakdown,
      totalSteps: steps.length + (requiresGuessing ? 1 : 0),
      requiresGuessing,
      solvedByLogic,
      clues: filled,
      solution,
    };
  }

  window.SudokuEngine = {
    analyze, parse, findConflicts, countSolutions, solveFull,
    TECH, isSolved,
    difficultyColor: (d) => ({ Easy: "#059669", Medium: "#d97706", Hard: "#e11d48" }[d] || "#475569"),
  };
})();
