"""FastAPI backend for Sudoku Research Platform.

This module provides REST API endpoints for the Sudoku Difficulty Validator,
including user identification, puzzle submission, and analytics.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import func
import uvicorn

from solver import (
    analyze, parse, find_conflicts, count_solutions, solve_full,
    is_solved, difficulty_color, TECH
)
from analyzer import (
    SUBMIT_PUBLISHERS, SUBMIT_PUBLISHER_SHORT, DIFF_BY_PUBLISHER,
    CLAIMED_SCORE, TECHNIQUE_SCALE,
    diffs_for, claimed_score, verdict, tech_for_score,
    analytics
)
from database import get_db, init_db, User, Puzzle

# Analytics unlock threshold
MIN_FOR_ANALYTICS = 5

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

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


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
        "name": "Sudoku Research Platform API",
        "version": "2.0.0",
        "endpoints": [
            "POST /api/user/identify",
            "POST /api/analyze",
            "POST /api/parse",
            "POST /api/validate-conflicts",
            "POST /api/count-solutions",
            "POST /api/solve",
            "GET /api/repository?user_id=",
            "POST /api/submit-puzzle?user_id=",
            "GET /api/analytics?user_id=",
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


# ---- User Identification Endpoints ----

class UserIdentifyInput(BaseModel):
    """Input model for user identification."""
    email: str


@app.post("/api/user/identify")
async def identify_user(input_data: UserIdentifyInput, db: Session = Depends(get_db)):
    """
    Create or retrieve user by email.

    Simple email-based identification - no password required.
    Returns user info and puzzle count for analytics unlock check.
    """
    email = input_data.email.lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    puzzle_count = db.query(Puzzle).filter(Puzzle.user_id == user.id).count()
    return {
        "userId": user.id,
        "email": user.email,
        "puzzleCount": puzzle_count,
        "analyticsUnlocked": puzzle_count >= MIN_FOR_ANALYTICS
    }


@app.get("/api/repository")
async def api_get_repository(user_id: int, db: Session = Depends(get_db)):
    """
    Get user's puzzles from the repository.

    Returns only puzzles belonging to the specified user.
    """
    puzzles = db.query(Puzzle).filter(Puzzle.user_id == user_id)\
        .order_by(Puzzle.created_at.desc()).all()
    return {"puzzles": [p.to_dict() for p in puzzles]}


@app.post("/api/submit-puzzle")
async def api_submit_puzzle(
    input_data: SubmitPuzzleInput,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Submit a new puzzle to the repository for a specific user.
    """
    # Check for duplicate grid for this user
    existing = db.query(Puzzle).filter(
        Puzzle.user_id == user_id,
        Puzzle.grid == input_data.grid
    ).first()
    if existing:
        return {"success": False, "error": "duplicate", "existingId": existing.puzzle_id}

    # Generate new puzzle ID
    max_id = db.query(func.max(Puzzle.id)).scalar() or 0
    puzzle_id = f"SDK-{1042 + max_id + 1:04d}"

    # Create puzzle record
    puzzle = Puzzle(
        puzzle_id=puzzle_id,
        user_id=user_id,
        grid=input_data.grid,
        clues=input_data.clues,
        publisher=input_data.publisher,
        publisher_short=SUBMIT_PUBLISHER_SHORT.get(input_data.publisher, input_data.publisher),
        claimed_difficulty=input_data.claimed,
        claimed_score=claimed_score(input_data.publisher, input_data.claimed) or 0,
        measured_score=input_data.measuredScore,
        mismatch=input_data.mismatch,
        verdict=input_data.verdict,
        hardest_technique=input_data.tech,
        composite_score=input_data.composite,
        difficulty_tier=input_data.difficulty,
    )
    db.add(puzzle)
    db.commit()

    # Get updated puzzle count for analytics unlock
    count = db.query(Puzzle).filter(Puzzle.user_id == user_id).count()

    return {
        "id": puzzle_id,
        "success": True,
        "puzzleCount": count,
        "analyticsUnlocked": count >= MIN_FOR_ANALYTICS
    }


@app.get("/api/analytics")
async def api_get_analytics(
    user_id: int,
    publisher: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get analytics computed on the user's repository.

    Returns locked status if user has fewer than MIN_FOR_ANALYTICS puzzles.
    Optionally filter by publisher and/or difficulty.
    """
    query = db.query(Puzzle).filter(Puzzle.user_id == user_id)

    if publisher:
        query = query.filter(Puzzle.publisher == publisher)
    if difficulty:
        query = query.filter(Puzzle.claimed_difficulty == difficulty)

    puzzles = query.all()

    # Check if analytics are unlocked
    total_count = db.query(Puzzle).filter(Puzzle.user_id == user_id).count()
    if total_count < MIN_FOR_ANALYTICS:
        return {
            "locked": True,
            "count": total_count,
            "required": MIN_FOR_ANALYTICS
        }

    if not puzzles:
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

    result = analytics([p.to_dict() for p in puzzles])
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
