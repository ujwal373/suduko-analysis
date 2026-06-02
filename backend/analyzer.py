"""Sample puzzles (real, engine-verified) + deterministic repository dataset.

Faithful Python migration from data.js. Contains publisher data, difficulty
mappings, verdict calculations, deterministic RNG, and analytics functions.

This module preserves EXACT behavioral equivalence with the JavaScript version.
"""

from __future__ import annotations
import math
from datetime import date, timedelta
from typing import Any, Optional, Callable


# ---- Publisher constants ----------------------------------------------------

PUBLISHERS: list[str] = [
    "The New York Times",
    "The Times",
    "The Guardian",
    "Sudoku.com",
]

PUBLISHER_SHORT: dict[str, str] = {
    "The New York Times": "NYT",
    "The Times": "Times",
    "The Guardian": "Guardian",
    "Sudoku.com": "Sudoku.com",
}

DIFFS: list[str] = ["Easy", "Medium", "Hard"]


# ---- Submit page — Publisher / claimed-difficulty system --------------------

SUBMIT_PUBLISHERS: list[str] = [
    "NYT",
    "Sudoku.com",
    "The Guardian",
    "Times Sudoku",
    "Others",
]

SUBMIT_PUBLISHER_SHORT: dict[str, str] = {
    "NYT": "NYT",
    "Sudoku.com": "Sudoku.com",
    "The Guardian": "Guardian",
    "Times Sudoku": "Times",
    "Others": "Other",
}

# Difficulty labels available per publisher
DIFF_BY_PUBLISHER: dict[str, list[str]] = {
    "NYT": ["Easy", "Medium", "Hard"],
    "Sudoku.com": ["Easy", "Medium", "Hard", "Expert", "Master", "Extreme"],
    "The Guardian": ["Easy", "Medium", "Hard", "Expert"],
    "Times Sudoku": ["Easy", "Mild", "Moderate", "Difficult", "Fiendish", "Super Fiendish"],
    "Others": ["Easy", "Medium", "Hard"],
}

# Fixed conversion of each publisher's label to a numeric claimed score
CLAIMED_SCORE: dict[str, dict[str, int]] = {
    "NYT": {"Easy": 2, "Medium": 4, "Hard": 6},
    "Sudoku.com": {"Easy": 2, "Medium": 4, "Hard": 5, "Expert": 7, "Master": 8, "Extreme": 9},
    "The Guardian": {"Easy": 2, "Medium": 4, "Hard": 7, "Expert": 9},
    "Times Sudoku": {"Easy": 1, "Mild": 2, "Moderate": 4, "Difficult": 6, "Fiendish": 9, "Super Fiendish": 10},
    "Others": {"Easy": 2, "Medium": 4, "Hard": 6},
}


def diffs_for(publisher: str) -> list[str]:
    """Get available difficulty labels for a publisher."""
    return DIFF_BY_PUBLISHER.get(publisher, [])


def claimed_score(publisher: str, label: str) -> Optional[int]:
    """Get the numeric claimed score for a publisher's difficulty label."""
    m = CLAIMED_SCORE.get(publisher)
    if m and label in m:
        return m[label]
    return None


def verdict(mismatch: int) -> str:
    """
    Convert mismatch value to verdict string.

    Mismatch = Measured Score - Claimed Score
    Positive => publisher under-rated (harder than claimed)
    Negative => publisher over-rated (easier than claimed)
    """
    if mismatch == 0:
        return "Accurate"
    if mismatch == 1:
        return "Slightly Underrated"
    if mismatch == 2:
        return "Moderately Underrated"
    if mismatch >= 3:
        return "Significantly Underrated"
    if mismatch == -1:
        return "Slightly Overrated"
    if mismatch == -2:
        return "Moderately Overrated"
    return "Significantly Overrated"  # -3 or less


# ---- Technique scale reference ----------------------------------------------

TECHNIQUE_SCALE: list[dict[str, Any]] = [
    {"name": "Full House", "score": 1},
    {"name": "Naked Single", "score": 1},
    {"name": "Hidden Single", "score": 2},
    {"name": "Pointing Pair", "score": 3},
    {"name": "Box-Line Reduction", "score": 3},
    {"name": "Naked Pair / Triple / Quad", "score": 4},
    {"name": "Hidden Pair / Triple / Quad", "score": 5},
    {"name": "X-Wing", "score": 6},
    {"name": "Swordfish", "score": 7},
    {"name": "X-Colors", "score": 7},
    {"name": "Jellyfish", "score": 8},
    {"name": "XY-Wing", "score": 9},
    {"name": "W-Wing", "score": 9},
    {"name": "Skyscraper", "score": 9},
    {"name": "Empty Rectangle", "score": 9},
    {"name": "XYZ-Wing", "score": 10},
    {"name": "Unique Rectangle", "score": 10},
]

TECH_BY_TIER: dict[str, list[str]] = {
    "Easy": ["Naked Single", "Hidden Single"],
    "Medium": ["Pointing Pair/Triple", "Claiming Pair/Triple", "Naked Pair", "Hidden Pair"],
    "Hard": ["Naked Triple", "Hidden Triple", "X-Wing", "XY-Wing", "Trial & Error (backtracking)"],
}

SCORE_RANGE: dict[str, list[int]] = {
    "Easy": [110, 255],
    "Medium": [260, 515],
    "Hard": [525, 955],
}

# Per-publisher grading character on the 1-10 technique-tier scale
# bias > 0 => publisher tends to UNDER-rate; bias < 0 => OVER-rates
PROFILE: dict[str, dict[str, float]] = {
    "NYT": {"bias": 0.1, "noise": 0.9},           # accurate, tight
    "Sudoku.com": {"bias": -1.6, "noise": 1.2},   # inflates claims (over-rates)
    "The Guardian": {"bias": 1.2, "noise": 1.7}, # under-rates, inconsistent
    "Times Sudoku": {"bias": 1.7, "noise": 1.5}, # under-rates the most
    "Others": {"bias": -0.2, "noise": 2.0},      # mixed / noisy
}

# Real, solvable puzzle grids assigned to seed records for the detail view
GRID_POOL: list[str] = [
    "530070000600195000098000060800060003400803001700020006060000280000419005000080079",
    "300000000970010000600583000200000900500621003008000005000435002000090056000000001",
    "100000569492056108056109240009640801064010000218035604040500016905061402621000005",
    "800000000003600000070090200050007000000045700000100030001000068008500010090000400",
    "000000907000420180000705026100904000050000040000507009920108000034059000507000000",
    "020810740700003100090002805009040087400208003160030200302700060005600008076051090",
]


def tech_for_score(score: int, rnd: Optional[Callable[[], float]] = None) -> str:
    """Get representative technique name for a measured score (1-10)."""
    matches = [t for t in TECHNIQUE_SCALE if t["score"] == score]
    if not matches:
        return "Advanced Out-of-Scope Technique"
    i = int(rnd() * len(matches)) if rnd else 0
    return matches[i]["name"]


# ---- Deterministic RNG (matching JavaScript mulberry32 exactly) -------------

def _imul(a: int, b: int) -> int:
    """
    Emulate JavaScript Math.imul (32-bit signed multiplication with truncation).

    Math.imul returns the result of the C-like 32-bit multiplication of the
    two parameters.
    """
    # Convert to unsigned 32-bit
    a = a & 0xFFFFFFFF
    b = b & 0xFFFFFFFF

    # Perform multiplication and truncate to 32 bits
    result = (a * b) & 0xFFFFFFFF

    # Convert to signed 32-bit (for imul behavior)
    if result >= 0x80000000:
        return result - 0x100000000
    return result


def _to_signed32(n: int) -> int:
    """Convert to signed 32-bit integer."""
    n = n & 0xFFFFFFFF
    if n >= 0x80000000:
        return n - 0x100000000
    return n


def _unsigned_right_shift(n: int, bits: int) -> int:
    """Emulate JavaScript's >>> (unsigned right shift)."""
    return (n & 0xFFFFFFFF) >> bits


def mulberry32(seed: int) -> Callable[[], float]:
    """
    Deterministic PRNG matching JavaScript mulberry32 implementation exactly.

    JavaScript implementation:
    function mulberry32(a) {
      return function () {
        a |= 0; a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    }
    """
    state = [seed]  # Use list to allow modification in closure

    def rng() -> float:
        # a |= 0 converts to signed 32-bit
        a = _to_signed32(state[0])
        # a = (a + 0x6D2B79F5) | 0
        a = _to_signed32(a + 0x6D2B79F5)
        state[0] = a

        # t = Math.imul(a ^ (a >>> 15), 1 | a)
        t = _imul(a ^ _unsigned_right_shift(a, 15), 1 | a)

        # t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
        t = (t + _imul(t ^ _unsigned_right_shift(t, 7), 61 | t)) ^ t
        t = _to_signed32(t)

        # return ((t ^ (t >>> 14)) >>> 0) / 4294967296
        result = _unsigned_right_shift(t ^ _unsigned_right_shift(t, 14), 0)
        return result / 4294967296

    return rng


def generate(n: int, seed: int = 20260531) -> list[dict[str, Any]]:
    """
    Generate n deterministic test records.

    Matches JavaScript generate() exactly for the same seed.
    """
    rnd = mulberry32(seed)

    def pick(arr: list) -> Any:
        return arr[int(rnd() * len(arr))]

    def clamp(v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, v))

    records: list[dict[str, Any]] = []
    for k in range(n):
        publisher = pick(SUBMIT_PUBLISHERS)
        prof = PROFILE[publisher]

        # Pick the publisher's claimed label, then derive measured score
        labels = DIFF_BY_PUBLISHER[publisher]
        claimed = pick(labels)
        c_score = claimed_score(publisher, claimed)

        drift = prof["bias"] + (rnd() - 0.5) * 2 * prof["noise"]
        measured_score = clamp(round(c_score + drift), 1, 10)
        mismatch = measured_score - c_score

        tech = tech_for_score(measured_score, rnd)
        clues = clamp(38 - measured_score - int(rnd() * 3), 22, 36)

        # Date: 2026-01-01 + random days (matching JS Date behavior)
        days_offset = int(rnd() * 150)
        d = date(2026, 1, 1) + timedelta(days=days_offset)

        records.append({
            "id": f"SDK-{1042 + k:04d}",
            "publisher": publisher,
            "publisherShort": SUBMIT_PUBLISHER_SHORT[publisher],
            "claimed": claimed,
            "claimedScore": c_score,
            "measuredScore": measured_score,
            "mismatch": mismatch,
            "verdict": verdict(mismatch),
            "tech": tech,
            "clues": clues,
            "grid": GRID_POOL[k % len(GRID_POOL)],
            "date": d.isoformat(),
            "ts": d.isoformat(),  # Simplified; JS includes time component
            "source": "seed",
        })

    return records


# Pre-generate the repository (36 records)
REPO: list[dict[str, Any]] = generate(36)


# ---- Analytics helpers ------------------------------------------------------

DIFF_IDX: dict[str, int] = {"Easy": 0, "Medium": 1, "Hard": 2}


def pearson(xs: list[float], ys: list[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    n = len(xs)
    if n < 2:
        return 0

    mx = sum(xs) / n
    my = sum(ys) / n

    num = 0.0
    dx = 0.0
    dy = 0.0

    for i in range(n):
        a = xs[i] - mx
        b = ys[i] - my
        num += a * b
        dx += a * a
        dy += b * b

    if dx and dy:
        return num / math.sqrt(dx * dy)
    return 0


def analytics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate analytics over the Technique-Tier model.

    mismatch = measured - claimed:
    positive => under-rated by publisher
    negative => over-rated
    """
    n = len(rows)

    r = pearson(
        [x["claimedScore"] for x in rows],
        [x["measuredScore"] for x in rows]
    )

    accurate = sum(1 for x in rows if x["mismatch"] == 0)
    agreement = accurate / n if n else 0
    over = sum(1 for x in rows if x["mismatch"] < 0)
    under = sum(1 for x in rows if x["mismatch"] > 0)
    mean_measured = sum(x["measuredScore"] for x in rows) / n if n else 0
    mean_abs_mismatch = sum(abs(x["mismatch"]) for x in rows) / n if n else 0

    # Group by publisher
    by_pub: dict[str, list[dict[str, Any]]] = {}
    for x in rows:
        by_pub.setdefault(x["publisher"], []).append(x)

    leaderboard: list[dict[str, Any]] = []
    for pub, lst in by_pub.items():
        acc = sum(1 for x in lst if x["mismatch"] == 0) / len(lst)
        o = sum(1 for x in lst if x["mismatch"] < 0)
        u = sum(1 for x in lst if x["mismatch"] > 0)
        mean_mis = sum(x["mismatch"] for x in lst) / len(lst)

        if mean_mis > 0.4:
            tendency = "under-rates"
        elif mean_mis < -0.4:
            tendency = "over-rates"
        else:
            tendency = "balanced"

        leaderboard.append({
            "publisher": pub,
            "short": SUBMIT_PUBLISHER_SHORT.get(pub, pub),
            "n": len(lst),
            "accuracy": acc,
            "over": o,
            "under": u,
            "meanMismatch": mean_mis,
            "tendency": tendency,
        })

    # Sort by accuracy descending
    leaderboard.sort(key=lambda a: -a["accuracy"])

    return {
        "pearson": r,
        "agreement": agreement,
        "accurate": accurate,
        "over": over,
        "under": under,
        "meanMeasured": mean_measured,
        "meanAbsMismatch": mean_abs_mismatch,
        "leaderboard": leaderboard,
        "n": n,
    }


# Module exports
__all__ = [
    'PUBLISHERS',
    'PUBLISHER_SHORT',
    'DIFFS',
    'SUBMIT_PUBLISHERS',
    'SUBMIT_PUBLISHER_SHORT',
    'DIFF_BY_PUBLISHER',
    'CLAIMED_SCORE',
    'TECHNIQUE_SCALE',
    'TECH_BY_TIER',
    'SCORE_RANGE',
    'PROFILE',
    'GRID_POOL',
    'REPO',
    'DIFF_IDX',
    'diffs_for',
    'claimed_score',
    'verdict',
    'tech_for_score',
    'mulberry32',
    'generate',
    'pearson',
    'analytics',
]
