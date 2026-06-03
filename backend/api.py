"""FastAPI backend for Sudoku Difficulty Validator.

This module provides REST API endpoints that replace the JavaScript
solver.js and data.js functionality, enabling the frontend to use
the Python implementation instead.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Union, Any
import uvicorn

from solver import (
    analyze, parse, find_conflicts, count_solutions, solve_full,
    is_solved, difficulty_color, TECH
)
from analyzer import (
    SUBMIT_PUBLISHERS, SUBMIT_PUBLISHER_SHORT, DIFF_BY_PUBLISHER,
    CLAIMED_SCORE, TECHNIQUE_SCALE, GRID_POOL, REPO,
    diffs_for, claimed_score, verdict, tech_for_score,
    generate, analytics, pearson
)

# ---- FastAPI App Setup ----

app = FastAPI(
    title="Sudoku Difficulty Validator API",
    description="API for analyzing Sudoku puzzles and calculating difficulty metrics",
    version="1.0.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- In-memory repository (for demo; use database in production) ----
# Start with seed data from analyzer.py
repository: list[dict] = list(REPO)
next_id = 1042 + len(REPO)


# ---- Pydantic Models ----

class PuzzleInput(BaseModel):
    """Input model for puzzle string or array."""
    puzzle: Union[str, list[int]] = Field(..., description="Puzzle as string (81 chars) or array of 81 integers")


class BoardInput(BaseModel):
    """Input model for board array."""
    board: list[int] = Field(..., description="Board as array of 81 integers (0 for empty)")


class CountSolutionsInput(BaseModel):
    """Input model for counting solutions."""
    board: list[int] = Field(..., description="Board as array of 81 integers")
    limit: int = Field(default=2, description="Stop counting after this many solutions")


class SubmitPuzzleInput(BaseModel):
    """Input model for submitting a puzzle to repository."""
    publisher: str
    claimed: str
    grid: str
    measuredScore: int
    mismatch: int
    verdict: str
    tech: str
    clues: int
    date: str
    hardestTech: Optional[dict] = None
    composite: Optional[int] = None
    difficulty: Optional[str] = None


class ClaimedScoreInput(BaseModel):
    """Input model for claimed score lookup."""
    publisher: str
    label: str


class VerdictInput(BaseModel):
    """Input model for verdict calculation."""
    mismatch: int


# ---- API Endpoints ----

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Sudoku Difficulty Validator API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/analyze",
            "POST /api/parse",
            "POST /api/validate-conflicts",
            "POST /api/count-solutions",
            "POST /api/solve",
            "GET /api/repository",
            "POST /api/submit-puzzle",
            "GET /api/analytics",
            "GET /api/constants",
            "POST /api/claimed-score",
            "POST /api/verdict",
        ]
    }


@app.post("/api/analyze")
async def api_analyze(input_data: PuzzleInput):
    """
    Analyze a Sudoku puzzle and return difficulty metrics.

    This is the main endpoint that replaces SudokuEngine.analyze().
    """
    try:
        result = analyze(input_data.puzzle)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/parse")
async def api_parse(input_data: PuzzleInput):
    """
    Parse a puzzle string into an 81-element board array.

    Replaces SudokuEngine.parse().
    """
    try:
        board = parse(input_data.puzzle)
        return {"board": board}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/validate-conflicts")
async def api_validate_conflicts(input_data: BoardInput):
    """
    Find conflicting cells (duplicates in row/column/box).

    Replaces SudokuEngine.findConflicts().
    """
    try:
        conflicts = find_conflicts(input_data.board)
        return {"conflicts": list(conflicts)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/count-solutions")
async def api_count_solutions(input_data: CountSolutionsInput):
    """
    Count solutions up to a limit (for uniqueness checking).

    Replaces SudokuEngine.countSolutions().
    """
    try:
        count = count_solutions(input_data.board, input_data.limit)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/solve")
async def api_solve(input_data: BoardInput):
    """
    Solve the puzzle completely using backtracking.

    Replaces SudokuEngine.solveFull().
    """
    try:
        solution = solve_full(input_data.board)
        if solution is None:
            return {"ok": False, "message": "No solution exists"}
        return {"ok": True, "solution": solution}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/repository")
async def api_get_repository():
    """
    Get all puzzles in the repository.

    Returns seed data plus any user-submitted puzzles.
    """
    return {"puzzles": repository}


@app.post("/api/submit-puzzle")
async def api_submit_puzzle(input_data: SubmitPuzzleInput):
    """
    Submit a new puzzle to the repository.
    """
    global next_id

    new_record = {
        "id": f"SDK-{next_id:04d}",
        "publisher": input_data.publisher,
        "publisherShort": SUBMIT_PUBLISHER_SHORT.get(input_data.publisher, input_data.publisher),
        "claimed": input_data.claimed,
        "claimedScore": claimed_score(input_data.publisher, input_data.claimed),
        "measuredScore": input_data.measuredScore,
        "mismatch": input_data.mismatch,
        "verdict": input_data.verdict,
        "tech": input_data.tech,
        "clues": input_data.clues,
        "grid": input_data.grid,
        "date": input_data.date,
        "ts": input_data.date,
        "source": "user",
    }

    # Add optional fields if provided
    if input_data.hardestTech:
        new_record["hardestTech"] = input_data.hardestTech
    if input_data.composite:
        new_record["composite"] = input_data.composite
    if input_data.difficulty:
        new_record["difficulty"] = input_data.difficulty

    repository.append(new_record)
    next_id += 1

    return {"id": new_record["id"], "success": True}


@app.get("/api/analytics")
async def api_get_analytics(
    publisher: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """
    Get analytics computed on the repository.

    Replaces SudokuData.analytics().
    Optionally filter by publisher and/or difficulty.
    """
    filtered = repository

    if publisher:
        filtered = [r for r in filtered if r.get("publisher") == publisher]
    if difficulty:
        filtered = [r for r in filtered if r.get("claimed") == difficulty]

    if not filtered:
        return {
            "pearson": 0,
            "agreement": 0,
            "accurate": 0,
            "over": 0,
            "under": 0,
            "meanMeasured": 0,
            "meanAbsMismatch": 0,
            "leaderboard": [],
            "n": 0
        }

    result = analytics(filtered)
    return result


@app.get("/api/constants")
async def api_get_constants():
    """
    Get all constants needed by the frontend.

    Replaces direct access to SudokuData constants.
    """
    # Convert TECH to serializable format
    tech_dict = {}
    for key, tech in TECH.items():
        tech_dict[key] = {
            "key": tech.key,
            "name": tech.name,
            "cost": tech.cost,
            "tier": tech.tier,
            "score": tech.score,
        }

    return {
        "SUBMIT_PUBLISHERS": SUBMIT_PUBLISHERS,
        "SUBMIT_PUBLISHER_SHORT": SUBMIT_PUBLISHER_SHORT,
        "DIFF_BY_PUBLISHER": DIFF_BY_PUBLISHER,
        "CLAIMED_SCORE": CLAIMED_SCORE,
        "TECHNIQUE_SCALE": TECHNIQUE_SCALE,
        "GRID_POOL": GRID_POOL,
        "TECH": tech_dict,
    }


@app.post("/api/claimed-score")
async def api_claimed_score(input_data: ClaimedScoreInput):
    """
    Look up the claimed score for a publisher's difficulty label.

    Replaces SudokuData.claimedScore().
    """
    score = claimed_score(input_data.publisher, input_data.label)
    return {"score": score}


@app.post("/api/verdict")
async def api_verdict(input_data: VerdictInput):
    """
    Get the verdict string for a mismatch value.

    Replaces SudokuData.verdict().
    """
    v = verdict(input_data.mismatch)
    return {"verdict": v}


@app.get("/api/diffs-for/{publisher}")
async def api_diffs_for(publisher: str):
    """
    Get available difficulty labels for a publisher.

    Replaces SudokuData.diffsFor().
    """
    diffs = diffs_for(publisher)
    return {"difficulties": diffs}


@app.get("/api/difficulty-color/{difficulty}")
async def api_difficulty_color(difficulty: str):
    """
    Get the color for a difficulty level.

    Replaces SudokuEngine.difficultyColor().
    """
    color = difficulty_color(difficulty)
    return {"color": color}


# ---- Run Server ----

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
