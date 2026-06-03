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



def tech_for_score(score: int) -> str:
    """Get representative technique name for a measured score (1-10)."""
    matches = [t for t in TECHNIQUE_SCALE if t["score"] == score]
    if not matches:
        return "Advanced Out-of-Scope Technique"
    return matches[0]["name"]


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
    'DIFF_IDX',
    'diffs_for',
    'claimed_score',
    'verdict',
    'tech_for_score',
    'pearson',
    'analytics',
]
