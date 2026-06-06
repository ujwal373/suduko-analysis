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
#   7  Swordfish, X-Colors
#   8  Jellyfish
#   9  XY-Wing, W-Wing, Skyscraper, Empty Rectangle
#  10  XYZ-Wing, Unique Rectangle
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
    # Score 7 techniques
    "swordfish": Technique(key="swordfish", name="Swordfish", cost=200, tier=3, score=7),
    "xColors": Technique(key="xColors", name="X-Colors", cost=210, tier=3, score=7),
    # Score 8 technique
    "jellyfish": Technique(key="jellyfish", name="Jellyfish", cost=240, tier=3, score=8),
    # Score 9 techniques
    "xyWing": Technique(key="xyWing", name="XY-Wing", cost=190, tier=3, score=9),
    "wWing": Technique(key="wWing", name="W-Wing", cost=220, tier=3, score=9),
    "skyscraper": Technique(key="skyscraper", name="Skyscraper", cost=185, tier=3, score=9),
    "emptyRectangle": Technique(key="emptyRectangle", name="Empty Rectangle", cost=195, tier=3, score=9),
    # Score 10 techniques
    "xyzWing": Technique(key="xyzWing", name="XYZ-Wing", cost=250, tier=3, score=10),
    "uniqueRectangle": Technique(key="uniqueRectangle", name="Unique Rectangle", cost=260, tier=3, score=10),
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


def t_swordfish(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    Swordfish: Fish pattern with 3 rows or 3 columns.

    When a candidate appears in exactly 2-3 cells in each of 3 rows,
    and those cells are confined to exactly 3 columns, eliminate that
    candidate from those columns outside the defining rows.
    """
    for v in range(1, 10):
        # Row-based Swordfish
        row_positions: list[list[int]] = []
        for r in range(9):
            cols = [i % 9 for i in UNIT_ROWS[r] if not board[i] and v in cand[i]]
            row_positions.append(cols)

        for r1, r2, r3 in combinations(range(9), 3):
            if not (2 <= len(row_positions[r1]) <= 3):
                continue
            if not (2 <= len(row_positions[r2]) <= 3):
                continue
            if not (2 <= len(row_positions[r3]) <= 3):
                continue

            cols_union = set(row_positions[r1]) | set(row_positions[r2]) | set(row_positions[r3])
            if len(cols_union) != 3:
                continue

            elim = []
            for c in cols_union:
                for r in range(9):
                    if r in (r1, r2, r3):
                        continue
                    i = r * 9 + c
                    if not board[i] and v in cand[i]:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": "swordfish", "placements": [], "eliminations": elim}

        # Column-based Swordfish
        col_positions: list[list[int]] = []
        for c in range(9):
            rows = [i // 9 for i in UNIT_COLS[c] if not board[i] and v in cand[i]]
            col_positions.append(rows)

        for c1, c2, c3 in combinations(range(9), 3):
            if not (2 <= len(col_positions[c1]) <= 3):
                continue
            if not (2 <= len(col_positions[c2]) <= 3):
                continue
            if not (2 <= len(col_positions[c3]) <= 3):
                continue

            rows_union = set(col_positions[c1]) | set(col_positions[c2]) | set(col_positions[c3])
            if len(rows_union) != 3:
                continue

            elim = []
            for r in rows_union:
                for c in range(9):
                    if c in (c1, c2, c3):
                        continue
                    i = r * 9 + c
                    if not board[i] and v in cand[i]:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": "swordfish", "placements": [], "eliminations": elim}

    return None


def t_x_colors(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    X-Colors (Simple Coloring): Chain-based technique using conjugate pairs.

    For a candidate that appears exactly twice in a unit, those two cells
    form a conjugate pair (one must be true, one false). Connect all such
    pairs to form chains. Color the chain with two colors.

    Elimination rules:
    1. If two cells with the same color see each other, that color is false.
    2. If an uncolored cell sees both colors, it can be eliminated.

    IMPORTANT: Each connected component (chain) must be processed independently.
    Cells from different chains should never be compared.
    """
    for v in range(1, 10):
        # Build graph of conjugate pairs for candidate v
        # Each cell is a node; conjugate pairs are edges
        conj_pairs: list[tuple[int, int]] = []

        for unit in ALL_UNITS:
            cells_with_v = [i for i in unit if not board[i] and v in cand[i]]
            if len(cells_with_v) == 2:
                c1, c2 = cells_with_v
                conj_pairs.append((c1, c2))

        if not conj_pairs:
            continue

        # Build adjacency list
        adj: dict[int, list[int]] = {}
        for c1, c2 in conj_pairs:
            adj.setdefault(c1, []).append(c2)
            adj.setdefault(c2, []).append(c1)

        # Process each connected component (chain) separately
        visited: set[int] = set()

        for start in adj:
            if start in visited:
                continue

            # BFS to color THIS chain only
            chain_color: dict[int, int] = {}
            queue = [start]
            chain_color[start] = 0

            while queue:
                node = queue.pop(0)
                visited.add(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in chain_color:
                        chain_color[neighbor] = 1 - chain_color[node]
                        queue.append(neighbor)

            if len(chain_color) < 2:
                continue

            # Collect cells by color for THIS chain only
            chain_color0 = [c for c, col in chain_color.items() if col == 0]
            chain_color1 = [c for c, col in chain_color.items() if col == 1]

            # Rule 1: Check if same-color cells see each other (contradiction)
            # Only check within THIS chain
            def has_contradiction(cells: list[int]) -> bool:
                for i in range(len(cells)):
                    for j in range(i + 1, len(cells)):
                        if cells[j] in PEERS[cells[i]]:
                            return True
                return False

            elim = []
            if has_contradiction(chain_color0):
                # Color 0 is false, eliminate v from all color0 cells in this chain
                for c in chain_color0:
                    if v in cand[c]:
                        elim.append({"i": c, "v": v})
            elif has_contradiction(chain_color1):
                # Color 1 is false, eliminate v from all color1 cells in this chain
                for c in chain_color1:
                    if v in cand[c]:
                        elim.append({"i": c, "v": v})

            if elim:
                return {"tech": "xColors", "placements": [], "eliminations": elim}

            # Rule 2: Uncolored cell sees both colors of THIS chain
            for i in range(81):
                if board[i] or i in chain_color or v not in cand[i]:
                    continue
                sees_color0 = any(c in PEERS[i] for c in chain_color0)
                sees_color1 = any(c in PEERS[i] for c in chain_color1)
                if sees_color0 and sees_color1:
                    elim.append({"i": i, "v": v})

            if elim:
                return {"tech": "xColors", "placements": [], "eliminations": elim}

    return None


def t_jellyfish(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    Jellyfish: Fish pattern with 4 rows or 4 columns.

    When a candidate appears in exactly 2-4 cells in each of 4 rows,
    and those cells are confined to exactly 4 columns, eliminate that
    candidate from those columns outside the defining rows.
    """
    for v in range(1, 10):
        # Row-based Jellyfish
        row_positions: list[list[int]] = []
        for r in range(9):
            cols = [i % 9 for i in UNIT_ROWS[r] if not board[i] and v in cand[i]]
            row_positions.append(cols)

        for r1, r2, r3, r4 in combinations(range(9), 4):
            rows = [r1, r2, r3, r4]
            valid = True
            for r in rows:
                if not (2 <= len(row_positions[r]) <= 4):
                    valid = False
                    break
            if not valid:
                continue

            cols_union = set()
            for r in rows:
                cols_union.update(row_positions[r])
            if len(cols_union) != 4:
                continue

            elim = []
            for c in cols_union:
                for r in range(9):
                    if r in rows:
                        continue
                    i = r * 9 + c
                    if not board[i] and v in cand[i]:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": "jellyfish", "placements": [], "eliminations": elim}

        # Column-based Jellyfish
        col_positions: list[list[int]] = []
        for c in range(9):
            rows = [i // 9 for i in UNIT_COLS[c] if not board[i] and v in cand[i]]
            col_positions.append(rows)

        for c1, c2, c3, c4 in combinations(range(9), 4):
            cols = [c1, c2, c3, c4]
            valid = True
            for c in cols:
                if not (2 <= len(col_positions[c]) <= 4):
                    valid = False
                    break
            if not valid:
                continue

            rows_union = set()
            for c in cols:
                rows_union.update(col_positions[c])
            if len(rows_union) != 4:
                continue

            elim = []
            for r in rows_union:
                for c in range(9):
                    if c in cols:
                        continue
                    i = r * 9 + c
                    if not board[i] and v in cand[i]:
                        elim.append({"i": i, "v": v})
            if elim:
                return {"tech": "jellyfish", "placements": [], "eliminations": elim}

    return None


def t_w_wing(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    W-Wing: Two bivalue cells with same candidates, connected by a strong link.

    Pattern: Two cells with candidates {A, B}, where one of them (A) is
    connected to another cell via a strong link on A. This creates a
    chain: if cell1 is B, cell2 must be B. So any cell seeing both
    cell1 and cell2 cannot be B.
    """
    bival = [i for i in range(81) if not board[i] and len(cand[i]) == 2]

    # Find strong links: cells where candidate appears exactly twice in a unit
    strong_links: dict[int, list[tuple[int, int]]] = {}  # candidate -> [(cell1, cell2), ...]
    for v in range(1, 10):
        strong_links[v] = []
        for unit in ALL_UNITS:
            cells_with_v = [i for i in unit if not board[i] and v in cand[i]]
            if len(cells_with_v) == 2:
                strong_links[v].append((cells_with_v[0], cells_with_v[1]))

    for i in range(len(bival)):
        c1 = bival[i]
        cands1 = cand[c1]

        for j in range(i + 1, len(bival)):
            c2 = bival[j]
            if cand[c2] != cands1:
                continue
            # c1 and c2 have same candidates {A, B}
            if c2 in PEERS[c1]:
                continue  # They shouldn't see each other for W-Wing

            vals = sorted(cands1)
            a, b = vals[0], vals[1]

            # Check if there's a strong link on 'a' connecting cells that see c1 and c2
            for link_a, link_b in strong_links[a]:
                # Strong-link cells must not be any of the bivalue cells
                if link_a in (c1, c2) or link_b in (c1, c2):
                    continue

                # Case 1: link connects cells where link_a sees c1 and link_b sees c2
                if link_a in PEERS[c1] and link_b in PEERS[c2]:
                    # If c1=B, then link_a=A, then link_b≠A, so c2=B
                    # Eliminate B from cells seeing both c1 and c2
                    elim = []
                    for k in range(81):
                        if k == c1 or k == c2 or board[k]:
                            continue
                        if c1 in PEERS[k] and c2 in PEERS[k] and b in cand[k]:
                            elim.append({"i": k, "v": b})
                    if elim:
                        return {"tech": "wWing", "placements": [], "eliminations": elim}

                # Case 2: link connects cells where link_b sees c1 and link_a sees c2
                if link_b in PEERS[c1] and link_a in PEERS[c2]:
                    elim = []
                    for k in range(81):
                        if k == c1 or k == c2 or board[k]:
                            continue
                        if c1 in PEERS[k] and c2 in PEERS[k] and b in cand[k]:
                            elim.append({"i": k, "v": b})
                    if elim:
                        return {"tech": "wWing", "placements": [], "eliminations": elim}

            # Try with 'b' as the linking candidate
            for link_a, link_b in strong_links[b]:
                # Strong-link cells must not be any of the bivalue cells
                if link_a in (c1, c2) or link_b in (c1, c2):
                    continue

                if link_a in PEERS[c1] and link_b in PEERS[c2]:
                    elim = []
                    for k in range(81):
                        if k == c1 or k == c2 or board[k]:
                            continue
                        if c1 in PEERS[k] and c2 in PEERS[k] and a in cand[k]:
                            elim.append({"i": k, "v": a})
                    if elim:
                        return {"tech": "wWing", "placements": [], "eliminations": elim}

                if link_b in PEERS[c1] and link_a in PEERS[c2]:
                    elim = []
                    for k in range(81):
                        if k == c1 or k == c2 or board[k]:
                            continue
                        if c1 in PEERS[k] and c2 in PEERS[k] and a in cand[k]:
                            elim.append({"i": k, "v": a})
                    if elim:
                        return {"tech": "wWing", "placements": [], "eliminations": elim}

    return None


def t_skyscraper(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    Skyscraper: Two conjugate pairs for the same candidate, sharing one endpoint.

    When a candidate has exactly 2 positions in two different rows/columns,
    and these form a pattern where one end of each pair is in the same column/row,
    the other ends can eliminate that candidate from cells seeing both.
    """
    for v in range(1, 10):
        # Row-based Skyscraper
        row_pairs: list[tuple[int, int, int]] = []  # (row, col1, col2)
        for r in range(9):
            cols = [i % 9 for i in UNIT_ROWS[r] if not board[i] and v in cand[i]]
            if len(cols) == 2:
                row_pairs.append((r, cols[0], cols[1]))

        for i in range(len(row_pairs)):
            r1, c1a, c1b = row_pairs[i]
            for j in range(i + 1, len(row_pairs)):
                r2, c2a, c2b = row_pairs[j]

                # Check if they share one column (forming the base)
                shared = None
                end1, end2 = None, None

                if c1a == c2a:
                    shared = c1a
                    end1, end2 = (r1, c1b), (r2, c2b)
                elif c1a == c2b:
                    shared = c1a
                    end1, end2 = (r1, c1b), (r2, c2a)
                elif c1b == c2a:
                    shared = c1b
                    end1, end2 = (r1, c1a), (r2, c2b)
                elif c1b == c2b:
                    shared = c1b
                    end1, end2 = (r1, c1a), (r2, c2a)

                if shared is None:
                    continue

                # end1 and end2 are the "roof" cells
                idx1 = end1[0] * 9 + end1[1]
                idx2 = end2[0] * 9 + end2[1]

                # Eliminate v from cells that see both roof cells
                elim = []
                for k in range(81):
                    if k == idx1 or k == idx2 or board[k]:
                        continue
                    if idx1 in PEERS[k] and idx2 in PEERS[k] and v in cand[k]:
                        elim.append({"i": k, "v": v})

                if elim:
                    return {"tech": "skyscraper", "placements": [], "eliminations": elim}

        # Column-based Skyscraper
        col_pairs: list[tuple[int, int, int]] = []  # (col, row1, row2)
        for c in range(9):
            rows = [i // 9 for i in UNIT_COLS[c] if not board[i] and v in cand[i]]
            if len(rows) == 2:
                col_pairs.append((c, rows[0], rows[1]))

        for i in range(len(col_pairs)):
            c1, r1a, r1b = col_pairs[i]
            for j in range(i + 1, len(col_pairs)):
                c2, r2a, r2b = col_pairs[j]

                shared = None
                end1, end2 = None, None

                if r1a == r2a:
                    shared = r1a
                    end1, end2 = (r1b, c1), (r2b, c2)
                elif r1a == r2b:
                    shared = r1a
                    end1, end2 = (r1b, c1), (r2a, c2)
                elif r1b == r2a:
                    shared = r1b
                    end1, end2 = (r1a, c1), (r2b, c2)
                elif r1b == r2b:
                    shared = r1b
                    end1, end2 = (r1a, c1), (r2a, c2)

                if shared is None:
                    continue

                idx1 = end1[0] * 9 + end1[1]
                idx2 = end2[0] * 9 + end2[1]

                elim = []
                for k in range(81):
                    if k == idx1 or k == idx2 or board[k]:
                        continue
                    if idx1 in PEERS[k] and idx2 in PEERS[k] and v in cand[k]:
                        elim.append({"i": k, "v": v})

                if elim:
                    return {"tech": "skyscraper", "placements": [], "eliminations": elim}

    return None


def t_empty_rectangle(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    Empty Rectangle: Uses a box where a candidate forms an "L" or "+" shape.

    When a candidate in a box is confined to exactly one row and one column
    (but not in their intersection), and there's a strong link in that row/column
    outside the box, eliminations can be made.
    """
    for v in range(1, 10):
        for b in range(9):
            box_cells = UNIT_BOXES[b]
            cells_with_v = [i for i in box_cells if not board[i] and v in cand[i]]

            if len(cells_with_v) < 2:
                continue

            rows_in_box = set(i // 9 for i in cells_with_v)
            cols_in_box = set(i % 9 for i in cells_with_v)

            # For Empty Rectangle, need candidate in multiple rows AND multiple columns
            if len(rows_in_box) < 2 or len(cols_in_box) < 2:
                continue

            # Find a row where there's exactly one cell with v in this box
            for er_row in rows_in_box:
                row_cells = [i for i in cells_with_v if i // 9 == er_row]
                if len(row_cells) != 1:
                    continue
                er_cell = row_cells[0]
                er_col = er_cell % 9

                # Look for a strong link in the ER row, outside the box
                row_outside = [i for i in UNIT_ROWS[er_row] if i not in box_cells and not board[i] and v in cand[i]]

                for link_cell in row_outside:
                    link_col = link_cell % 9

                    # Verify link_cell is part of a conjugate pair in its column
                    # (v must appear exactly twice in the column for a strong link)
                    cells_in_link_col = [i for i in UNIT_COLS[link_col] if not board[i] and v in cand[i]]
                    if len(cells_in_link_col) != 2:
                        continue  # Not a genuine strong link

                    # Find the other cell in the conjugate pair (outside ER row)
                    col_cells = [i for i in cells_in_link_col if i != link_cell]

                    if len(col_cells) != 1:
                        continue

                    target = col_cells[0]
                    target_row = target // 9

                    # Check if there's another cell in ER column at target_row
                    check_cell = target_row * 9 + er_col
                    if board[check_cell] or v not in cand[check_cell]:
                        continue

                    # Can eliminate v from target if there's strong link logic
                    # The elimination is at the intersection: target sees link_cell (same col)
                    # and the ER box provides the constraint
                    elim = [{"i": target, "v": v}]
                    return {"tech": "emptyRectangle", "placements": [], "eliminations": elim}

            # Try with columns
            for er_col in cols_in_box:
                col_cells = [i for i in cells_with_v if i % 9 == er_col]
                if len(col_cells) != 1:
                    continue
                er_cell = col_cells[0]
                er_row = er_cell // 9

                col_outside = [i for i in UNIT_COLS[er_col] if i not in box_cells and not board[i] and v in cand[i]]

                for link_cell in col_outside:
                    link_row = link_cell // 9

                    # Verify link_cell is part of a conjugate pair in its row
                    # (v must appear exactly twice in the row for a strong link)
                    cells_in_link_row = [i for i in UNIT_ROWS[link_row] if not board[i] and v in cand[i]]
                    if len(cells_in_link_row) != 2:
                        continue  # Not a genuine strong link

                    # Find the other cell in the conjugate pair (outside ER col)
                    row_cells = [i for i in cells_in_link_row if i != link_cell]

                    if len(row_cells) != 1:
                        continue

                    target = row_cells[0]
                    target_col = target % 9

                    check_cell = er_row * 9 + target_col
                    if board[check_cell] or v not in cand[check_cell]:
                        continue

                    elim = [{"i": target, "v": v}]
                    return {"tech": "emptyRectangle", "placements": [], "eliminations": elim}

    return None


def t_xyz_wing(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    XYZ-Wing: Extension of XY-Wing where pivot has 3 candidates.

    Pivot cell has {X, Y, Z}, two wing cells have {X, Z} and {Y, Z}.
    All three cells share candidate Z. Any cell seeing all three cannot have Z.
    """
    # Find cells with exactly 3 candidates (potential pivots)
    trival = [i for i in range(81) if not board[i] and len(cand[i]) == 3]
    bival = [i for i in range(81) if not board[i] and len(cand[i]) == 2]

    for piv in trival:
        piv_cands = cand[piv]
        xyz = sorted(piv_cands)

        # Need to find pairs of bivalue cells that together have 2 of the 3 values
        # and share the third value Z
        for z in xyz:
            other = [v for v in xyz if v != z]
            x, y = other[0], other[1]

            # Wing 1 must have {X, Z} and see pivot
            # Wing 2 must have {Y, Z} and see pivot
            wing1_cands = {x, z}
            wing2_cands = {y, z}

            wing1_cells = [i for i in bival if i in PEERS[piv] and cand[i] == wing1_cands]
            wing2_cells = [i for i in bival if i in PEERS[piv] and cand[i] == wing2_cands]

            for w1 in wing1_cells:
                for w2 in wing2_cells:
                    if w1 == w2:
                        continue

                    # Z can be eliminated from cells seeing all three (pivot, w1, w2)
                    elim = []
                    for i in range(81):
                        if i == piv or i == w1 or i == w2 or board[i]:
                            continue
                        if piv in PEERS[i] and w1 in PEERS[i] and w2 in PEERS[i]:
                            if z in cand[i]:
                                elim.append({"i": i, "v": z})

                    if elim:
                        return {"tech": "xyzWing", "placements": [], "eliminations": elim}

    return None


def t_unique_rectangle(board: list[int], cand: list[set[int]]) -> Optional[dict]:
    """
    Unique Rectangle: Exploits the fact that valid Sudoku must have unique solution.

    Type 1: Four cells in rectangle (2 rows, 2 columns, 2 boxes) where:
    - Three cells have exactly {A, B}
    - Fourth cell has {A, B} plus extra candidates
    The extra candidates must be true (to avoid deadly pattern).

    Type 2: Four cells where two have {A, B} and two have {A, B, X}:
    - X can be eliminated from cells outside rectangle that see both +X cells.
    """
    bival = [i for i in range(81) if not board[i] and len(cand[i]) == 2]

    # Find potential UR base: pairs of bivalue cells in same row with same candidates
    for i in range(len(bival)):
        c1 = bival[i]
        r1, col1 = c1 // 9, c1 % 9
        cands = cand[c1]

        for j in range(i + 1, len(bival)):
            c2 = bival[j]
            r2, col2 = c2 // 9, c2 % 9

            if cand[c2] != cands:
                continue

            # Need same row or same column
            if r1 != r2 and col1 != col2:
                continue

            if r1 == r2:
                # Same row - look for completing row
                for other_row in range(9):
                    if other_row == r1:
                        continue

                    c3 = other_row * 9 + col1
                    c4 = other_row * 9 + col2

                    if board[c3] or board[c4]:
                        continue

                    # Check box constraint: UR must span exactly 2 boxes
                    b1, b2 = box_of(r1, col1), box_of(r1, col2)
                    b3, b4 = box_of(other_row, col1), box_of(other_row, col2)

                    if len({b1, b2, b3, b4}) != 2:
                        continue  # UR must span exactly 2 boxes

                    # Type 1: Three have {A,B}, one has {A,B}+extras
                    type1_found = False

                    if cand[c3] == cands and cands.issubset(cand[c4]) and len(cand[c4]) > 2:
                        # c4 has extras - eliminate A,B from c4
                        elim = []
                        for v in cands:
                            if v in cand[c4]:
                                elim.append({"i": c4, "v": v})
                        if elim:
                            return {"tech": "uniqueRectangle", "placements": [], "eliminations": elim}
                        type1_found = True

                    if cand[c4] == cands and cands.issubset(cand[c3]) and len(cand[c3]) > 2:
                        elim = []
                        for v in cands:
                            if v in cand[c3]:
                                elim.append({"i": c3, "v": v})
                        if elim:
                            return {"tech": "uniqueRectangle", "placements": [], "eliminations": elim}
                        type1_found = True

                    if type1_found:
                        continue

                    # Type 2: Two opposite corners have same extra candidate
                    if cands.issubset(cand[c3]) and cands.issubset(cand[c4]):
                        extra3 = cand[c3] - cands
                        extra4 = cand[c4] - cands

                        if len(extra3) == 1 and extra3 == extra4:
                            x = next(iter(extra3))
                            # Eliminate x from cells seeing both c3 and c4
                            elim = []
                            for k in range(81):
                                if k in (c1, c2, c3, c4) or board[k]:
                                    continue
                                if c3 in PEERS[k] and c4 in PEERS[k] and x in cand[k]:
                                    elim.append({"i": k, "v": x})
                            if elim:
                                return {"tech": "uniqueRectangle", "placements": [], "eliminations": elim}

            else:
                # Same column - look for completing column
                for other_col in range(9):
                    if other_col == col1:
                        continue

                    c3 = r1 * 9 + other_col
                    c4 = r2 * 9 + other_col

                    if board[c3] or board[c4]:
                        continue

                    # Check box constraint: UR must span exactly 2 boxes
                    b1, b2 = box_of(r1, col1), box_of(r2, col1)
                    b3, b4 = box_of(r1, other_col), box_of(r2, other_col)

                    if len({b1, b2, b3, b4}) != 2:
                        continue  # UR must span exactly 2 boxes

                    # Type 1
                    if cand[c3] == cands and cands.issubset(cand[c4]) and len(cand[c4]) > 2:
                        elim = []
                        for v in cands:
                            if v in cand[c4]:
                                elim.append({"i": c4, "v": v})
                        if elim:
                            return {"tech": "uniqueRectangle", "placements": [], "eliminations": elim}

                    if cand[c4] == cands and cands.issubset(cand[c3]) and len(cand[c3]) > 2:
                        elim = []
                        for v in cands:
                            if v in cand[c3]:
                                elim.append({"i": c3, "v": v})
                        if elim:
                            return {"tech": "uniqueRectangle", "placements": [], "eliminations": elim}

                    # Type 2
                    if cands.issubset(cand[c3]) and cands.issubset(cand[c4]):
                        extra3 = cand[c3] - cands
                        extra4 = cand[c4] - cands

                        if len(extra3) == 1 and extra3 == extra4:
                            x = next(iter(extra3))
                            elim = []
                            for k in range(81):
                                if k in (c1, c2, c3, c4) or board[k]:
                                    continue
                                if c3 in PEERS[k] and c4 in PEERS[k] and x in cand[k]:
                                    elim.append({"i": k, "v": x})
                            if elim:
                                return {"tech": "uniqueRectangle", "placements": [], "eliminations": elim}

    return None


# Technique order (in increasing difficulty)
# Techniques are attempted in this order; solver uses first one that finds eliminations
ORDER = [
    # Score 1: Basic singles
    t_full_house,
    t_naked_single,
    # Score 2: Hidden single
    t_hidden_single,
    # Score 3: Intersection techniques
    t_pointing,
    t_claiming,
    # Score 4: Naked subsets
    lambda b, c: t_naked_set(b, c, 2, "nakedPair"),
    lambda b, c: t_naked_set(b, c, 3, "nakedTriple"),
    lambda b, c: t_naked_set(b, c, 4, "nakedQuad"),
    # Score 5: Hidden subsets
    lambda b, c: t_hidden_set(b, c, 2, "hiddenPair"),
    lambda b, c: t_hidden_set(b, c, 3, "hiddenTriple"),
    lambda b, c: t_hidden_set(b, c, 4, "hiddenQuad"),
    # Score 6: Basic fish
    t_x_wing,
    # Score 7: Advanced fish and coloring
    t_swordfish,
    t_x_colors,
    # Score 8: Large fish
    t_jellyfish,
    # Score 9: Wings and single-digit patterns
    t_skyscraper,
    t_xy_wing,
    t_w_wing,
    t_empty_rectangle,
    # Score 10: Advanced wings and uniqueness
    t_xyz_wing,
    t_unique_rectangle,
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

    # Build breakdown in specific order (by increasing score/difficulty)
    breakdown_order = [
        # Score 1
        "fullHouse", "nakedSingle",
        # Score 2
        "hiddenSingle",
        # Score 3
        "pointing", "claiming",
        # Score 4
        "nakedPair", "nakedTriple", "nakedQuad",
        # Score 5
        "hiddenPair", "hiddenTriple", "hiddenQuad",
        # Score 6
        "xWing",
        # Score 7
        "swordfish", "xColors",
        # Score 8
        "jellyfish",
        # Score 9
        "skyscraper", "xyWing", "wWing", "emptyRectangle",
        # Score 10
        "xyzWing", "uniqueRectangle",
        # Out of scope
        "backtrack"
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
