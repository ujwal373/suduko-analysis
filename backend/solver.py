"""Sudoku Difficulty Validator — logical solver + scoring engine.

Faithful Python migration from solver.js. Applies human techniques in increasing
order of difficulty, records each step, and derives a composite difficulty score
+ measured difficulty band.

This module preserves EXACT behavioral equivalence with the JavaScript version.
"""

from __future__ import annotations
import re
import math
from dataclasses import dataclass
from typing import Optional, Union, Any
from itertools import combinations


# ---- Geometry ---------------------------------------------------------------

def rc(i: int) -> tuple[int, int]:
    """Convert flat index to (row, col)."""
    return (i // 9, i % 9)


def box_of(r: int, c: int) -> int:
    """Get box number (0-8) from row/col."""
    return (r // 3) * 3 + (c // 3)


# Pre-computed unit arrays (matching JS exactly)
UNIT_ROWS: list[list[int]] = []
for r in range(9):
    row = []
    for c in range(9):
        row.append(r * 9 + c)
    UNIT_ROWS.append(row)

UNIT_COLS: list[list[int]] = []
for c in range(9):
    col = []
    for r in range(9):
        col.append(r * 9 + c)
    UNIT_COLS.append(col)

UNIT_BOXES: list[list[int]] = []
for b in range(9):
    box = []
    br = (b // 3) * 3
    bc = (b % 3) * 3
    for dr in range(3):
        for dc in range(3):
            box.append((br + dr) * 9 + (bc + dc))
    UNIT_BOXES.append(box)

ALL_UNITS: list[list[int]] = UNIT_ROWS + UNIT_COLS + UNIT_BOXES

# Pre-compute peers for each cell
PEERS: list[set[int]] = []
for i in range(81):
    r, c = rc(i)
    b = box_of(r, c)
    s: set[int] = set()
    for x in UNIT_ROWS[r]:
        s.add(x)
    for x in UNIT_COLS[c]:
        s.add(x)
    for x in UNIT_BOXES[b]:
        s.add(x)
    s.discard(i)
    PEERS.append(s)


# ---- Technique catalogue ----------------------------------------------------
# Scoring Scale (strict 1-10):
#   1  Full House, Naked Single
#   2  Hidden Single
#   3  Pointing Pair, Box-Line Reduction
#   4  Naked Pair / Triple / Quad
#   5  Hidden Pair / Triple / Quad
#   6  X-Wing
#   7  Swordfish, X-Colours (not implemented)
#   8  Jellyfish (not implemented)
#   9  XY-Wing, W-Wing, Skyscraper, Empty Rectangle
#  10  XYZ-Wing, Unique Rectangle (not implemented)
# Anything beyond this scale is "Out of Scope" (no numeric score)

@dataclass(frozen=True)
class Technique:
    """Technique metadata."""
    key: str
    name: str
    cost: int
    tier: int
    score: Optional[int]  # None for out-of-scope techniques


TECH: dict[str, Technique] = {
    "fullHouse": Technique(key="fullHouse", name="Full House", cost=6, tier=1, score=1),
    "nakedSingle": Technique(key="nakedSingle", name="Naked Single", cost=8, tier=1, score=1),
    "hiddenSingle": Technique(key="hiddenSingle", name="Hidden Single", cost=14, tier=1, score=2),
    "pointing": Technique(key="pointing", name="Pointing Pair", cost=42, tier=2, score=3),
    "claiming": Technique(key="claiming", name="Box-Line Reduction", cost=48, tier=2, score=3),
    "nakedPair": Technique(key="nakedPair", name="Naked Pair", cost=60, tier=2, score=4),
    "nakedTriple": Technique(key="nakedTriple", name="Naked Triple", cost=92, tier=3, score=4),
    "nakedQuad": Technique(key="nakedQuad", name="Naked Quad", cost=120, tier=3, score=4),
    "hiddenPair": Technique(key="hiddenPair", name="Hidden Pair", cost=72, tier=2, score=5),
    "hiddenTriple": Technique(key="hiddenTriple", name="Hidden Triple", cost=116, tier=3, score=5),
    "hiddenQuad": Technique(key="hiddenQuad", name="Hidden Quad", cost=150, tier=3, score=5),
    "xWing": Technique(key="xWing", name="X-Wing", cost=165, tier=3, score=6),
    "xyWing": Technique(key="xyWing", name="XY-Wing", cost=190, tier=3, score=9),
    # Out-of-scope: score is None (beyond 1-10 scale)
    "backtrack": Technique(key="backtrack", name="Out-of-Scope Technique", cost=360, tier=3, score=None),
}

# Advanced techniques beyond the 1-10 scale (out of scope)
# These require techniques not implemented in this solver
OUT_OF_SCOPE: list[str] = [
    "Alternating Inference Chain",
    "Nice Loop",
    "Sue de Coq",
    "Aligned Pair Exclusion",
    "Almost Locked Sets",
    "Death Blossom",
]


def assumed_out_of_scope(board: list[int]) -> str:
    """Deterministic selection based on board hash (matching JS >>> 0)."""
    h = 0
    for i in range(81):
        h = ((h * 31 + (board[i] if board[i] else 0)) & 0xFFFFFFFF)
    return OUT_OF_SCOPE[h % len(OUT_OF_SCOPE)]


# ---- Parsing / validation ---------------------------------------------------

def parse(input_val: Union[str, list[int]]) -> list[int]:
    """Parse input string or array into 81-element board array."""
    board = [0] * 81
    if isinstance(input_val, list):
        for i in range(min(81, len(input_val))):
            board[i] = input_val[i] if input_val[i] else 0
        return board

    # String parsing
    s = str(input_val)
    clean = re.sub(r'[^0-9.]', '', s).replace('.', '0')
    for i in range(min(81, len(clean))):
        board[i] = 0 if clean[i] == '0' else int(clean[i])
    return board


def find_conflicts(board: list[int]) -> set[int]:
    """Return set of conflicting cell indices."""
    bad: set[int] = set()
    for unit in ALL_UNITS:
        seen: dict[int, int] = {}
        for i in unit:
            v = board[i]
            if not v:
                continue
            if v in seen:
                bad.add(i)
                bad.add(seen[v])
            else:
                seen[v] = i
    return bad


def compute_candidates(board: list[int]) -> list[set[int]]:
    """Build array of candidate sets for each cell."""
    cand: list[set[int]] = []
    for i in range(81):
        if board[i]:
            cand.append(set())
            continue
        s = {1, 2, 3, 4, 5, 6, 7, 8, 9}
        for p in PEERS[i]:
            if board[p]:
                s.discard(board[p])
        cand.append(s)
    return cand


def is_solved(board: list[int]) -> bool:
    """Check if all 81 cells are filled."""
    return all(v != 0 for v in board)


# ---- Backtracking solver (uniqueness check + fallback) ----------------------

def count_solutions(board: list[int], limit: int) -> int:
    """Count solutions up to limit (uses MRV heuristic)."""
    work = board[:]
    count = [0]  # Use list to allow modification in nested function

    def bt() -> None:
        if count[0] >= limit:
            return
        best = -1
        best_cand: Optional[list[int]] = None
        for i in range(81):
            if work[i]:
                continue
            opts = []
            for v in range(1, 10):
                ok = True
                for p in PEERS[i]:
                    if work[p] == v:
                        ok = False
                        break
                if ok:
                    opts.append(v)
            if len(opts) == 0:
                return
            if best_cand is None or len(opts) < len(best_cand):
                best = i
                best_cand = opts
        if best == -1:
            count[0] += 1
            return
        for v in best_cand:
            work[best] = v
            bt()
            if count[0] >= limit:
                work[best] = 0
                return
            work[best] = 0

    bt()
    return count[0]


def solve_full(board: list[int]) -> Optional[list[int]]:
    """Solve using pure backtracking, return solved board or None."""
    work = board[:]

    def bt() -> bool:
        best = -1
        best_cand: Optional[list[int]] = None
        for i in range(81):
            if work[i]:
                continue
            opts = []
            for v in range(1, 10):
                ok = True
                for p in PEERS[i]:
                    if work[p] == v:
                        ok = False
                        break
                if ok:
                    opts.append(v)
            if len(opts) == 0:
                return False
            if best_cand is None or len(opts) < len(best_cand):
                best = i
                best_cand = opts
        if best == -1:
            return True
        for v in best_cand:
            work[best] = v
            if bt():
                return True
            work[best] = 0
        return False

    return work if bt() else None


# ---- Mutation helper --------------------------------------------------------

def place(board: list[int], cand: list[set[int]], i: int, v: int) -> None:
    """Place value v at cell i, clear candidates, eliminate from peers."""
    board[i] = v
    cand[i] = set()
    for p in PEERS[i]:
        cand[p].discard(v)


# ---- Techniques (each returns an action dict or None) -----------------------

def t_full_house(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """Full House: a unit with exactly one empty cell."""
    for unit in ALL_UNITS:
        empty = -1
        cnt = 0
        for i in unit:
            if not board[i]:
                empty = i
                cnt += 1
                if cnt > 1:
                    break
        if cnt == 1:
            # Get the smallest candidate (matches JS Set iteration order)
            if cand[empty]:
                v = min(cand[empty])
                return {"tech": "fullHouse", "placements": [{"i": empty, "v": v}], "eliminations": []}
    return None


def t_naked_single(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """Naked Single: cell with only 1 candidate."""
    for i in range(81):
        if not board[i] and len(cand[i]) == 1:
            v = min(cand[i])  # Get the single element
            return {"tech": "nakedSingle", "placements": [{"i": i, "v": v}], "eliminations": []}
    return None


def t_hidden_single(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """Hidden Single: value appears in only 1 place in a unit."""
    for unit in ALL_UNITS:
        for v in range(1, 10):
            spot = -1
            cnt = 0
            already = False
            for i in unit:
                if board[i] == v:
                    already = True
                    break
                if not board[i] and v in cand[i]:
                    cnt += 1
                    spot = i
            if not already and cnt == 1:
                return {"tech": "hiddenSingle", "placements": [{"i": spot, "v": v}], "eliminations": []}
    return None


def t_pointing(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """Pointing: candidate confined to one box AND one line -> eliminate from line outside box."""
    for b in range(9):
        cells = UNIT_BOXES[b]
        for v in range(1, 10):
            spots = [i for i in cells if not board[i] and v in cand[i]]
            if len(spots) < 2:
                continue
            rows = set(i // 9 for i in spots)
            cols = set(i % 9 for i in spots)
            elim = []
            if len(rows) == 1:
                r = next(iter(rows))
                for i in UNIT_ROWS[r]:
                    if i not in cells and not board[i] and v in cand[i]:
                        elim.append({"i": i, "v": v})
            elif len(cols) == 1:
                c = next(iter(cols))
                for i in UNIT_COLS[c]:
                    if i not in cells and not board[i] and v in cand[i]:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": "pointing", "placements": [], "eliminations": elim}
    return None


def t_claiming(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """Claiming: candidate in a line confined to one box -> eliminate from rest of box."""
    lines = UNIT_ROWS + UNIT_COLS
    for line in lines:
        for v in range(1, 10):
            spots = [i for i in line if not board[i] and v in cand[i]]
            if len(spots) < 2:
                continue
            boxes = set(box_of(i // 9, i % 9) for i in spots)
            if len(boxes) != 1:
                continue
            b = next(iter(boxes))
            elim = []
            for i in UNIT_BOXES[b]:
                if i not in line and not board[i] and v in cand[i]:
                    elim.append({"i": i, "v": v})
            if elim:
                return {"tech": "claiming", "placements": [], "eliminations": elim}
    return None


def t_naked_set(board: list[int], cand: list[set[int]], k: int, tech_key: str) -> Optional[dict]:
    """Naked Set (pairs/triples/quads): k cells in unit with k candidates total."""
    for unit in ALL_UNITS:
        cells = [i for i in unit if not board[i] and 2 <= len(cand[i]) <= k]
        if len(cells) < k:
            continue
        for combo in combinations(cells, k):
            union: set[int] = set()
            for i in combo:
                union.update(cand[i])
            if len(union) != k:
                continue
            elim = []
            for i in unit:
                if i in combo or board[i]:
                    continue
                for v in union:
                    if v in cand[i]:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": tech_key, "placements": [], "eliminations": elim}
    return None


def t_hidden_set(board: list[int], cand: list[set[int]], k: int, tech_key: str) -> Optional[dict]:
    """Hidden Set (pairs/triples/quads): k values appear only in same k cells of unit."""
    for unit in ALL_UNITS:
        present = []
        for v in range(1, 10):
            spots = [i for i in unit if not board[i] and v in cand[i]]
            if 1 <= len(spots) <= k:
                present.append({"v": v, "spots": spots})
        if len(present) < k:
            continue
        for combo in combinations(present, k):
            cell_set: set[int] = set()
            for p in combo:
                cell_set.update(p["spots"])
            if len(cell_set) != k:
                continue
            digits = set(p["v"] for p in combo)
            elim = []
            for i in cell_set:
                for v in cand[i]:
                    if v not in digits:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": tech_key, "placements": [], "eliminations": elim}
    return None


def t_x_wing(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """X-Wing on rows and columns."""
    for v in range(1, 10):
        # Row-based
        row_spots: list[list[int]] = []
        for r in range(9):
            cols = [i % 9 for i in UNIT_ROWS[r] if not board[i] and v in cand[i]]
            row_spots.append(cols)
        for r1 in range(9):
            if len(row_spots[r1]) != 2:
                continue
            for r2 in range(r1 + 1, 9):
                if len(row_spots[r2]) != 2:
                    continue
                if row_spots[r1][0] == row_spots[r2][0] and row_spots[r1][1] == row_spots[r2][1]:
                    c1, c2 = row_spots[r1]
                    elim = []
                    for r in range(9):
                        if r == r1 or r == r2:
                            continue
                        for c in [c1, c2]:
                            i = r * 9 + c
                            if not board[i] and v in cand[i]:
                                elim.append({"i": i, "v": v})
                    if elim:
                        return {"tech": "xWing", "placements": [], "eliminations": elim}

        # Column-based
        col_spots: list[list[int]] = []
        for c in range(9):
            rows = [i // 9 for i in UNIT_COLS[c] if not board[i] and v in cand[i]]
            col_spots.append(rows)
        for a in range(9):
            if len(col_spots[a]) != 2:
                continue
            for b in range(a + 1, 9):
                if len(col_spots[b]) != 2:
                    continue
                if col_spots[a][0] == col_spots[b][0] and col_spots[a][1] == col_spots[b][1]:
                    r1, r2 = col_spots[a]
                    elim = []
                    for c in range(9):
                        if c == a or c == b:
                            continue
                        for r in [r1, r2]:
                            i = r * 9 + c
                            if not board[i] and v in cand[i]:
                                elim.append({"i": i, "v": v})
                    if elim:
                        return {"tech": "xWing", "placements": [], "eliminations": elim}
    return None


def t_xy_wing(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """XY-Wing pattern."""
    bival = [i for i in range(81) if not board[i] and len(cand[i]) == 2]
    for piv in bival:
        piv_cands = sorted(cand[piv])
        x, y = piv_cands[0], piv_cands[1]
        for p1 in bival:
            if p1 == piv or p1 not in PEERS[piv]:
                continue
            if x not in cand[p1]:
                continue
            p1_cands = sorted(cand[p1])
            z1 = p1_cands[0] if p1_cands[0] != x else p1_cands[1]
            if z1 == y:
                continue
            for p2 in bival:
                if p2 == piv or p2 == p1 or p2 not in PEERS[piv]:
                    continue
                if y not in cand[p2] or z1 not in cand[p2]:
                    continue
                # Check p2 has exactly {y, z1}
                if cand[p2] != {y, z1}:
                    continue
                z = z1
                elim = []
                for i in range(81):
                    if i == p1 or i == p2 or board[i]:
                        continue
                    if p1 in PEERS[i] and p2 in PEERS[i] and z in cand[i]:
                        elim.append({"i": i, "v": z})
                if elim:
                    return {"tech": "xyWing", "placements": [], "eliminations": elim}
    return None


# Technique order (matching JS exactly)
ORDER = [
    t_full_house,
    t_naked_single,
    t_hidden_single,
    t_pointing,
    t_claiming,
    lambda b, c: t_naked_set(b, c, 2, "nakedPair"),
    lambda b, c: t_naked_set(b, c, 3, "nakedTriple"),
    lambda b, c: t_naked_set(b, c, 4, "nakedQuad"),
    lambda b, c: t_hidden_set(b, c, 2, "hiddenPair"),
    lambda b, c: t_hidden_set(b, c, 3, "hiddenTriple"),
    lambda b, c: t_hidden_set(b, c, 4, "hiddenQuad"),
    t_x_wing,
    t_xy_wing,
]


def apply_result(board: list[int], cand: list[set[int]], res: dict) -> None:
    """Apply placements and eliminations to board."""
    for p in res["placements"]:
        place(board, cand, p["i"], p["v"])
    for e in res["eliminations"]:
        cand[e["i"]].discard(e["v"])


# ---- Helper for JavaScript-compatible rounding ------------------------------

def js_round(x: float) -> int:
    """Round like JavaScript (round half away from zero)."""
    if x >= 0:
        return int(math.floor(x + 0.5))
    else:
        return int(math.ceil(x - 0.5))


# ---- Main analysis ----------------------------------------------------------

def analyze(input_val: Union[str, list[int]]) -> dict[str, Any]:
    """
    Analyze a Sudoku puzzle and return difficulty metrics.

    Returns a dict with:
    - ok: bool
    - reason, message: str (if not ok)
    - conflicts: list[int] (if conflict)
    - difficulty: str ("Easy"|"Medium"|"Hard")
    - composite: int
    - maxScore: int (always 1000)
    - measuredScore: int
    - hardestTech: dict
    - outOfScope: bool
    - assumedTech: str|None
    - scaleMax: int (always 10)
    - breakdown: list[dict]
    - totalSteps: int
    - requiresGuessing: bool
    - solvedByLogic: bool
    - clues: int
    - solution: list[int]|None
    """
    board = parse(input_val)
    filled = sum(1 for v in board if v)
    conflicts = find_conflicts(board)

    if conflicts:
        return {
            "ok": False,
            "reason": "conflict",
            "message": "The grid has duplicate values in a row, column, or box.",
            "conflicts": list(conflicts),
        }

    if filled < 17:
        return {
            "ok": False,
            "reason": "insufficient",
            "message": "A valid Sudoku needs at least 17 clues. Add more givens to analyze.",
        }

    n_sol = count_solutions(board, 2)
    if n_sol == 0:
        return {
            "ok": False,
            "reason": "unsolvable",
            "message": "This puzzle has no solution.",
        }
    if n_sol > 1:
        return {
            "ok": False,
            "reason": "nonunique",
            "message": "This puzzle has multiple solutions — it is not a valid Sudoku.",
        }

    work = board[:]
    cand = compute_candidates(work)
    steps: list[dict] = []
    guard = 0

    while not is_solved(work) and guard < 1000:
        guard += 1
        progressed = False
        for t in range(len(ORDER)):
            res = ORDER[t](work, cand)
            if res:
                apply_result(work, cand, res)
                steps.append(res)
                progressed = True
                break
        if not progressed:
            break

    solved_by_logic = is_solved(work)
    counts: dict[str, int] = {}
    total = 0
    max_cost = 0
    max_tier = 1
    hardest = TECH["nakedSingle"]
    max_score = 0
    hardest_by_score = TECH["nakedSingle"]

    for s in steps:
        m = TECH[s["tech"]]
        counts[s["tech"]] = counts.get(s["tech"], 0) + 1
        total += m.cost
        if m.cost > max_cost:
            max_cost = m.cost
            hardest = m
        if m.tier > max_tier:
            max_tier = m.tier
        if m.score > max_score:
            max_score = m.score
            hardest_by_score = m

    # Out-of-scope handling
    requires_guessing = False
    out_of_scope = False
    assumed_tech = None

    if not solved_by_logic:
        requires_guessing = True
        out_of_scope = True
        assumed_tech = assumed_out_of_scope(board)
        counts["backtrack"] = 1
        total += TECH["backtrack"].cost
        max_cost = TECH["backtrack"].cost
        max_tier = 3
        hardest = TECH["backtrack"]
        # Out of scope: max_score stays at highest known technique used
        # (don't assign numeric score beyond 10)
        hardest_by_score = TECH["backtrack"]

    # Technique-Tier Classification
    # Strict 1-10 scale; out-of-scope is indicated separately, not with score 12
    measured_score = max_score if max_score else 1
    if out_of_scope:
        hardest_tech = {
            "key": "outOfScope",
            "name": assumed_tech,
            "outOfScope": True,
            # No numeric "score" field - this is beyond the 1-10 scale
        }
    else:
        hardest_tech = {
            "key": hardest_by_score.key,
            "name": hardest_by_score.name,
            "score": hardest_by_score.score,
        }

    composite = js_round(max_cost * 2.4 + total * 0.32)
    difficulty = "Easy" if max_tier == 1 else "Medium" if max_tier == 2 else "Hard"

    # Build breakdown in specific order
    breakdown_order = [
        "fullHouse", "nakedSingle", "hiddenSingle", "pointing", "claiming",
        "nakedPair", "nakedTriple", "nakedQuad", "hiddenPair", "hiddenTriple",
        "hiddenQuad", "xWing", "xyWing", "backtrack"
    ]
    breakdown = []
    for k in breakdown_order:
        if k in counts:
            m = TECH[k]
            name = (assumed_tech + " (out of scope)") if k == "backtrack" and assumed_tech else m.name
            entry = {
                "key": k,
                "name": name,
                "tier": m.tier,
                "count": counts[k],
                "cost": m.cost,
                "total": m.cost * counts[k],
            }
            # Only include score if it's on the 1-10 scale (not out-of-scope)
            if m.score is not None:
                entry["score"] = m.score
            else:
                entry["outOfScope"] = True
            breakdown.append(entry)

    solution = solve_full(board)

    return {
        "ok": True,
        "difficulty": difficulty,
        "composite": composite,
        "maxScore": 1000,
        "measuredScore": measured_score,
        "hardestTech": hardest_tech,
        "outOfScope": out_of_scope,
        "assumedTech": assumed_tech,
        "scaleMax": 10,
        "breakdown": breakdown,
        "totalSteps": len(steps) + (1 if requires_guessing else 0),
        "requiresGuessing": requires_guessing,
        "solvedByLogic": solved_by_logic,
        "clues": filled,
        "solution": solution,
    }


def difficulty_color(d: str) -> str:
    """Map difficulty string to hex color."""
    colors = {
        "Easy": "#059669",
        "Medium": "#d97706",
        "Hard": "#e11d48",
    }
    return colors.get(d, "#475569")


# Module exports
__all__ = [
    'analyze',
    'parse',
    'find_conflicts',
    'count_solutions',
    'solve_full',
    'TECH',
    'is_solved',
    'difficulty_color',
    'compute_candidates',
    'UNIT_ROWS',
    'UNIT_COLS',
    'UNIT_BOXES',
    'ALL_UNITS',
    'PEERS',
]
