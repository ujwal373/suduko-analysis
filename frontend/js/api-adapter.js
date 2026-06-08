/* API Adapter — replaces local solver.js and data.js with Python backend calls.
   Provides window.SudokuEngine and window.SudokuData interfaces that work with
   the existing React components but fetch from the FastAPI backend.

   To use: Include this file INSTEAD of solver.js and data.js
   Make sure the Python backend is running on API_BASE_URL */

(function () {
  "use strict";

  // Configure your backend URL here
  // For local development: http://localhost:8000
  // For production: Update with your Render URL after deployment
  const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://suduko-analysis.onrender.com";  // TODO: Replace with your actual Render URL

  // Cache for constants (loaded once)
  let constantsCache = null;

  // ---- Helper for API calls ----
  async function apiPost(endpoint, data) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "API request failed");
    }
    return response.json();
  }

  async function apiGet(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "API request failed");
    }
    return response.json();
  }

  // ---- Load constants from backend ----
  async function loadConstants() {
    if (constantsCache) return constantsCache;
    constantsCache = await apiGet("/api/constants");
    return constantsCache;
  }

  // Pre-load constants when script loads
  loadConstants().catch(console.error);

  // ---- SudokuEngine (replaces solver.js) ----
  const SudokuEngine = {
    // Main analysis - can be called synchronously (uses cached promise) or async
    analyze: async function (input) {
      const puzzle = Array.isArray(input) ? input : input;
      const result = await apiPost("/api/analyze", { puzzle });
      return result;
    },

    // Synchronous wrapper that returns a promise-like object for backward compatibility
    // For components that expect synchronous results, use analyzeSync with setTimeout
    analyzeSync: function (input) {
      // This is for backward compatibility - returns result via callback
      return SudokuEngine.analyze(input);
    },

    parse: function (str) {
      // Parse can be done client-side for performance
      const b = new Array(81).fill(0);
      if (Array.isArray(str)) {
        for (let i = 0; i < 81; i++) b[i] = str[i] | 0;
        return b;
      }
      const clean = String(str).replace(/[^0-9.]/g, "").replace(/\./g, "0");
      for (let i = 0; i < 81 && i < clean.length; i++) {
        b[i] = clean[i] === "0" ? 0 : +clean[i];
      }
      return b;
    },

    findConflicts: function (board) {
      // Client-side implementation for performance (no API call needed)
      const bad = new Set();
      const units = [];

      // Build units
      for (let r = 0; r < 9; r++) {
        const row = [];
        for (let c = 0; c < 9; c++) row.push(r * 9 + c);
        units.push(row);
      }
      for (let c = 0; c < 9; c++) {
        const col = [];
        for (let r = 0; r < 9; r++) col.push(r * 9 + c);
        units.push(col);
      }
      for (let b = 0; b < 9; b++) {
        const box = [];
        const br = Math.floor(b / 3) * 3, bc = (b % 3) * 3;
        for (let dr = 0; dr < 3; dr++) {
          for (let dc = 0; dc < 3; dc++) {
            box.push((br + dr) * 9 + (bc + dc));
          }
        }
        units.push(box);
      }

      for (const unit of units) {
        const seen = {};
        for (const i of unit) {
          const v = board[i];
          if (!v) continue;
          if (seen[v] != null) {
            bad.add(i);
            bad.add(seen[v]);
          } else {
            seen[v] = i;
          }
        }
      }
      return bad;
    },

    countSolutions: async function (board, limit) {
      const result = await apiPost("/api/count-solutions", { board, limit });
      return result.count;
    },

    solveFull: async function (board) {
      const result = await apiPost("/api/solve", { board });
      return result.ok ? result.solution : null;
    },

    isSolved: function (board) {
      return board.every((v) => v !== 0);
    },

    difficultyColor: function (d) {
      return { Easy: "#059669", Medium: "#d97706", Hard: "#e11d48" }[d] || "#475569";
    },

    // TECH catalogue (loaded from backend)
    TECH: null,
  };

  // ---- SudokuData (replaces data.js) ----
  const SudokuData = {
    // These will be populated from the backend
    PUBLISHERS: ["The New York Times", "The Times", "The Guardian", "Sudoku.com"],
    PUBLISHER_SHORT: {
      "The New York Times": "NYT",
      "The Times": "Times",
      "The Guardian": "Guardian",
      "Sudoku.com": "Sudoku.com",
    },
    DIFFS: ["Easy", "Medium", "Hard"],

    SUBMIT_PUBLISHERS: ["NYT", "Sudoku.com", "The Guardian", "Times Sudoku", "Others"],
    SUBMIT_PUBLISHER_SHORT: {
      "NYT": "NYT",
      "Sudoku.com": "Sudoku.com",
      "The Guardian": "Guardian",
      "Times Sudoku": "Times",
      "Others": "Other",
    },

    DIFF_BY_PUBLISHER: {
      "NYT": ["Easy", "Medium", "Hard"],
      "Sudoku.com": ["Easy", "Medium", "Hard", "Expert", "Master", "Extreme"],
      "The Guardian": ["Easy", "Medium", "Hard", "Expert"],
      "Times Sudoku": ["Easy", "Mild", "Moderate", "Difficult", "Fiendish", "Super Fiendish"],
      "Others": ["Easy", "Medium", "Hard"],
    },

    // Range-based difficulty validation: [low, high, midpoint] arrays
    CLAIMED_RANGES: {
      "NYT": {
        Easy: [1, 3, 2],
        Medium: [4, 6, 5],
        Hard: [7, 10, 8],
      },
      "Sudoku.com": {
        Easy: [1, 2, 1.5],
        Medium: [3, 4, 3.5],
        Hard: [5, 5, 5],
        Expert: [6, 7, 6.5],
        Master: [8, 8, 8],
        Extreme: [9, 10, 9.5],
      },
      "The Guardian": {
        Easy: [1, 3, 2],
        Medium: [4, 5, 4.5],
        Hard: [6, 7, 6.5],
        Expert: [8, 10, 9],
      },
      "Times Sudoku": {
        Easy: [1, 1, 1],
        Mild: [2, 2, 2],
        Moderate: [3, 4, 3.5],
        Difficult: [5, 6, 5.5],
        Fiendish: [7, 9, 8],
        "Super Fiendish": [10, 10, 10],
      },
      "Others": {
        Easy: [1, 3, 2],
        Medium: [4, 6, 5],
        Hard: [7, 10, 8],
      },
    },

    TECHNIQUE_SCALE: [
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
    ],

    // Repository data (loaded from backend, starts empty)
    REPO: [],

    diffsFor: function (publisher) {
      return SudokuData.DIFF_BY_PUBLISHER[publisher] || [];
    },

    claimedRange: function (publisher, label) {
      const m = SudokuData.CLAIMED_RANGES[publisher];
      return m && m[label] != null ? m[label] : null;
    },

    isInRange: function (measured, rangeLow, rangeHigh) {
      return measured >= rangeLow && measured <= rangeHigh;
    },

    calculateMismatch: function (measured, rangeLow, rangeHigh, midpoint) {
      if (SudokuData.isInRange(measured, rangeLow, rangeHigh)) {
        return 0;
      }
      return Math.round((measured - midpoint) * 10) / 10;
    },

    verdict: function (mismatch) {
      if (mismatch === 0) return "Accurate";
      if (mismatch >= 3) return "Significantly Underrated";
      if (mismatch >= 2) return "Moderately Underrated";
      if (mismatch >= 1) return "Slightly Underrated";
      if (mismatch <= -3) return "Significantly Overrated";
      if (mismatch <= -2) return "Moderately Overrated";
      if (mismatch <= -1) return "Slightly Overrated";
      return "Accurate"; // -1 < mismatch < 1
    },

    techForScore: function (score) {
      const matches = SudokuData.TECHNIQUE_SCALE.filter((t) => t.score === score);
      if (!matches.length) return "Advanced Out-of-Scope Technique";
      return matches[0].name;
    },

    // Analytics - computed client-side using range-based validation
    analytics: function (rows) {
      const n = rows.length;
      if (n < 2) return { pearson: 0, agreement: 0, accurate: 0, over: 0, under: 0, meanMeasured: 0, meanAbsMismatch: 0, leaderboard: [], n: 0 };

      // Pearson correlation using midpoint (fall back to claimedScore for compatibility)
      const xs = rows.map((x) => x.claimedMidpoint || x.claimedScore || 0);
      const ys = rows.map((x) => x.measuredScore);
      const mx = xs.reduce((a, b) => a + b, 0) / n;
      const my = ys.reduce((a, b) => a + b, 0) / n;
      let num = 0, dx = 0, dy = 0;
      for (let i = 0; i < n; i++) {
        const a = xs[i] - mx, b = ys[i] - my;
        num += a * b; dx += a * a; dy += b * b;
      }
      const r = dx && dy ? num / Math.sqrt(dx * dy) : 0;

      // Use tolerance for float comparison
      const accurate = rows.filter((x) => Math.abs(x.mismatch) < 0.001).length;
      const agreement = n ? accurate / n : 0;
      const over = rows.filter((x) => x.mismatch < -0.001).length;
      const under = rows.filter((x) => x.mismatch > 0.001).length;
      const meanMeasured = n ? rows.reduce((a, b) => a + b.measuredScore, 0) / n : 0;
      const meanAbsMismatch = n ? rows.reduce((a, b) => a + Math.abs(b.mismatch), 0) / n : 0;

      // Leaderboard by publisher
      const byPub = {};
      rows.forEach((x) => { (byPub[x.publisher] = byPub[x.publisher] || []).push(x); });
      const leaderboard = Object.entries(byPub).map(([pub, list]) => {
        const acc = list.filter((x) => Math.abs(x.mismatch) < 0.001).length / list.length;
        const o = list.filter((x) => x.mismatch < -0.001).length;
        const u = list.filter((x) => x.mismatch > 0.001).length;
        const meanMis = list.reduce((a, b) => a + b.mismatch, 0) / list.length;
        return {
          publisher: pub,
          short: SudokuData.SUBMIT_PUBLISHER_SHORT[pub] || pub,
          n: list.length,
          accuracy: acc,
          over: o, under: u,
          meanMismatch: meanMis,
          tendency: meanMis > 0.4 ? "under-rates" : meanMis < -0.4 ? "over-rates" : "balanced",
        };
      }).sort((a, b) => b.accuracy - a.accuracy);

      return { pearson: r, agreement, accurate, over, under, meanMeasured, meanAbsMismatch, leaderboard, n };
    },

    pearson: function (xs, ys) {
      const n = xs.length;
      if (n < 2) return 0;
      const mx = xs.reduce((a, b) => a + b, 0) / n;
      const my = ys.reduce((a, b) => a + b, 0) / n;
      let num = 0, dx = 0, dy = 0;
      for (let i = 0; i < n; i++) {
        const a = xs[i] - mx, b = ys[i] - my;
        num += a * b; dx += a * a; dy += b * b;
      }
      return dx && dy ? num / Math.sqrt(dx * dy) : 0;
    },
  };

  // Expose to window
  window.SudokuEngine = SudokuEngine;
  window.SudokuData = SudokuData;
  window.API_BASE_URL = API_BASE_URL;

  // Also expose async versions for future use
  window.SudokuAPI = {
    analyze: (puzzle) => apiPost("/api/analyze", { puzzle }),
    getRepository: () => apiGet("/api/repository"),
    submitPuzzle: (data) => apiPost("/api/submit-puzzle", data),
    getAnalytics: (params) => apiGet(`/api/analytics?${new URLSearchParams(params)}`),
    getConstants: loadConstants,
  };

  console.log("Sudoku API Adapter loaded. Backend URL:", API_BASE_URL);
})();
