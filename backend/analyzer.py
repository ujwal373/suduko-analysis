"""Publisher data, difficulty mappings, verdict calculations, and analytics functions.

This module contains the configuration and analytics logic for the Sudoku
Difficulty Validator research platform.
"""

from __future__ import annotations
import math
from typing import Any, Optional


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

# Range-based difficulty validation: (low, high, midpoint) tuples
# A puzzle is "Accurate" if measured score falls within the range
# Mismatch is calculated from midpoint only when outside the range
CLAIMED_RANGES: dict[str, dict[str, tuple[float, float, float]]] = {
    "NYT": {
        "Easy": (1, 3, 2),
        "Medium": (4, 6, 5),
        "Hard": (7, 10, 8),
    },
    "Sudoku.com": {
        "Easy": (1, 2, 1.5),
        "Medium": (3, 4, 3.5),
        "Hard": (5, 5, 5),
        "Expert": (6, 7, 6.5),
        "Master": (8, 8, 8),
        "Extreme": (9, 10, 9.5),
    },
    "The Guardian": {
        "Easy": (1, 3, 2),
        "Medium": (4, 5, 4.5),
        "Hard": (6, 7, 6.5),
        "Expert": (8, 10, 9),
    },
    "Times Sudoku": {
        "Easy": (1, 1, 1),
        "Mild": (2, 2, 2),
        "Moderate": (3, 4, 3.5),
        "Difficult": (5, 6, 5.5),
        "Fiendish": (7, 9, 8),
        "Super Fiendish": (10, 10, 10),
    },
    "Others": {
        "Easy": (1, 3, 2),
        "Medium": (4, 6, 5),
        "Hard": (7, 10, 8),
    },
}


def diffs_for(publisher: str) -> list[str]:
    """Get available difficulty labels for a publisher."""
    return DIFF_BY_PUBLISHER.get(publisher, [])


def claimed_range(publisher: str, label: str) -> Optional[tuple[float, float, float]]:
    """Get the claimed range (low, high, midpoint) for a publisher's difficulty label."""
    m = CLAIMED_RANGES.get(publisher)
    if m and label in m:
        return m[label]
    return None


def is_in_range(measured: int, range_low: float, range_high: float) -> bool:
    """Check if measured score falls within the claimed range."""
    return range_low <= measured <= range_high


def calculate_mismatch(measured: int, range_low: float, range_high: float, midpoint: float) -> float:
    """
    Calculate mismatch value using range-based validation.

    Returns 0 if measured score is within the claimed range.
    Otherwise returns (measured - midpoint) rounded to 1 decimal place.
    """
    if is_in_range(measured, range_low, range_high):
        return 0.0
    return round(measured - midpoint, 1)


def verdict(mismatch: float) -> str:
    """
    Convert mismatch value to verdict string.

    Range-based thresholds:
    - mismatch = 0: Accurate (score within claimed range)
    - +1 to <2: Slightly Underrated
    - +2 to <3: Moderately Underrated
    - >=3: Significantly Underrated
    - -1 to >-2: Slightly Overrated
    - -2 to >-3: Moderately Overrated
    - <=-3: Significantly Overrated

    Positive => publisher under-rated (harder than claimed)
    Negative => publisher over-rated (easier than claimed)
    """
    if mismatch == 0:
        return "Accurate"
    if mismatch >= 3:
        return "Significantly Underrated"
    if mismatch >= 2:
        return "Moderately Underrated"
    if mismatch >= 1:
        return "Slightly Underrated"
    if mismatch <= -3:
        return "Significantly Overrated"
    if mismatch <= -2:
        return "Moderately Overrated"
    if mismatch <= -1:
        return "Slightly Overrated"
    # Edge case: -1 < mismatch < 1 (but not exactly 0)
    return "Accurate"


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

# ---- Publisher behavioral profiles for synthetic data generation -----------
# bias > 0 => publisher typically UNDER-rates difficulty (measured > claimed midpoint)
# bias < 0 => publisher typically OVER-rates difficulty
PROFILE: dict[str, dict[str, float]] = {
    "NYT": {"bias": 0.1, "noise": 0.9},  # accurate, tight
    "Sudoku.com": {"bias": -1.6, "noise": 1.2},  # inflates claims (over-rates)
    "The Guardian": {"bias": 1.2, "noise": 1.7},  # under-rates, inconsistent
    "Times Sudoku": {"bias": 1.7, "noise": 1.5},  # under-rates the most
    "Others": {"bias": -0.2, "noise": 2.0},  # mixed / noisy
}

# Real, solvable puzzle grids assigned to seed records for the detail view.
GRID_POOL: list[str] = [
    "530070000600195000098000060800060003400803001700020006060000280000419005000080079",
    "300000000970010000600583000200000900500621003008000005000435002000090056000000001",
    "100000569492056108056109240009640801064010000218035604040500016905061402621000005",
    "800000000003600000070090200050007000000045700000100030001000068008500010090000400",
    "000000907000420180000705026100904000050000040000507009920108000034059000507000000",
    "020810740700003100090002805009040087400208003160030200302700060005600008076051090",
]


def tech_for_score(score: int) -> str:
    """Get representative technique name for a measured score (1-10)."""
    matches = [t for t in TECHNIQUE_SCALE if t["score"] == score]
    if not matches:
        return "Advanced Out-of-Scope Technique"
    return matches[0]["name"]


# ---- Deterministic RNG for reproducible test data ---------------------------

def mulberry32(seed: int):
    """
    Mulberry32 PRNG - deterministic random number generator.
    Returns a function that produces floats in [0, 1).
    """
    a = seed

    def next_random() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + ((t ^ (t >> 7)) * (61 | t))) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return next_random


def generate(n: int, seed: int = 20260531) -> list[dict[str, Any]]:
    """
    Generate n synthetic puzzle records using range-based validation.

    Records include:
    - id, publisher, publisherShort, claimed
    - claimedRangeLow, claimedRangeHigh, claimedMidpoint, inRange
    - measuredScore, mismatch, verdict
    - tech, clues, grid, date, ts, source
    """
    rnd = mulberry32(seed)

    def pick(arr: list) -> Any:
        return arr[int(rnd() * len(arr))]

    def clamp(v: float, lo: float, hi: float) -> int:
        return int(max(lo, min(hi, v)))

    records: list[dict[str, Any]] = []

    for k in range(n):
        publisher = pick(SUBMIT_PUBLISHERS)
        prof = PROFILE[publisher]

        # Pick the publisher's claimed label, then derive measured score
        labels = DIFF_BY_PUBLISHER[publisher]
        claimed = pick(labels)
        rng = claimed_range(publisher, claimed)
        range_low, range_high, midpoint = rng

        # Apply bias and noise to simulate real-world variation
        drift = prof["bias"] + (rnd() - 0.5) * 2 * prof["noise"]
        measured_score = clamp(round(midpoint + drift), 1, 10)

        # Range-based validation
        in_range = is_in_range(measured_score, range_low, range_high)
        mismatch = calculate_mismatch(measured_score, range_low, range_high, midpoint)

        tech = tech_for_score(measured_score)
        clues = clamp(38 - measured_score - int(rnd() * 3), 22, 36)

        # Generate date in first 150 days of 2026
        day_offset = int(rnd() * 150)
        # Use datetime-like calculation
        year, month, day = 2026, 1, 1 + day_offset
        while True:
            days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
            if day <= days_in_month:
                break
            day -= days_in_month
            month += 1
            if month > 12:
                month = 1
                year += 1

        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        ts_str = f"{date_str}T00:00:00.000Z"

        records.append({
            "id": f"SDK-{1042 + k:04d}",
            "publisher": publisher,
            "publisherShort": SUBMIT_PUBLISHER_SHORT.get(publisher, publisher),
            "claimed": claimed,
            "claimedRangeLow": range_low,
            "claimedRangeHigh": range_high,
            "claimedMidpoint": midpoint,
            "inRange": in_range,
            "measuredScore": measured_score,
            "mismatch": mismatch,
            "verdict": verdict(mismatch),
            "tech": tech,
            "clues": clues,
            "grid": GRID_POOL[k % len(GRID_POOL)],
            "date": date_str,
            "ts": ts_str,
            "source": "seed",
        })

    return records


# Pre-generate 36 repository records for testing
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
    Calculate analytics using range-based validation model.

    mismatch = 0 when measured score is within claimed range
    mismatch = measured - midpoint when outside range
    positive => under-rated by publisher (harder than claimed)
    negative => over-rated by publisher (easier than claimed)
    """
    n = len(rows)

    # Use midpoint for correlation calculation (fall back to claimedScore for compatibility)
    r = pearson(
        [x.get("claimedMidpoint", x.get("claimedScore", 0)) for x in rows],
        [x["measuredScore"] for x in rows]
    )

    # Use tolerance for float comparison (mismatch is now a float)
    accurate = sum(1 for x in rows if abs(x["mismatch"]) < 0.001)
    agreement = accurate / n if n else 0
    over = sum(1 for x in rows if x["mismatch"] < -0.001)
    under = sum(1 for x in rows if x["mismatch"] > 0.001)
    mean_measured = sum(x["measuredScore"] for x in rows) / n if n else 0
    mean_abs_mismatch = sum(abs(x["mismatch"]) for x in rows) / n if n else 0

    # Group by publisher
    by_pub: dict[str, list[dict[str, Any]]] = {}
    for x in rows:
        by_pub.setdefault(x["publisher"], []).append(x)

    leaderboard: list[dict[str, Any]] = []
    for pub, lst in by_pub.items():
        acc = sum(1 for x in lst if abs(x["mismatch"]) < 0.001) / len(lst)
        o = sum(1 for x in lst if x["mismatch"] < -0.001)
        u = sum(1 for x in lst if x["mismatch"] > 0.001)
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
    'CLAIMED_RANGES',
    'TECHNIQUE_SCALE',
    'TECH_BY_TIER',
    'SCORE_RANGE',
    'PROFILE',
    'GRID_POOL',
    'REPO',
    'DIFF_IDX',
    'diffs_for',
    'claimed_range',
    'is_in_range',
    'calculate_mismatch',
    'verdict',
    'tech_for_score',
    'mulberry32',
    'generate',
    'pearson',
    'analytics',
]
