"""Sudoku Difficulty Validator - Python Backend

Faithful migration from JavaScript solver.js and data.js with exact behavioral equivalence.
"""

from .solver import (
    analyze,
    parse,
    find_conflicts,
    count_solutions,
    solve_full,
    TECH,
    is_solved,
    difficulty_color,
)

from .analyzer import (
    PUBLISHERS,
    PUBLISHER_SHORT,
    DIFFS,
    SUBMIT_PUBLISHERS,
    SUBMIT_PUBLISHER_SHORT,
    DIFF_BY_PUBLISHER,
    CLAIMED_RANGES,
    TECHNIQUE_SCALE,
    TECH_BY_TIER,
    SCORE_RANGE,
    PROFILE,
    GRID_POOL,
    REPO,
    DIFF_IDX,
    diffs_for,
    claimed_range,
    is_in_range,
    calculate_mismatch,
    verdict,
    tech_for_score,
    mulberry32,
    generate,
    pearson,
    analytics,
)

__all__ = [
    # solver.py exports
    'analyze',
    'parse',
    'find_conflicts',
    'count_solutions',
    'solve_full',
    'TECH',
    'is_solved',
    'difficulty_color',
    # analyzer.py exports
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
