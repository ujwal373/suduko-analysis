"""Tests for analyzer.py - Publisher data and analytics.

These tests verify behavioral equivalence with the JavaScript implementation.
Updated for range-based validation methodology.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer import (
    PUBLISHERS, PUBLISHER_SHORT, DIFFS,
    SUBMIT_PUBLISHERS, SUBMIT_PUBLISHER_SHORT,
    DIFF_BY_PUBLISHER, CLAIMED_RANGES,
    TECHNIQUE_SCALE, TECH_BY_TIER, SCORE_RANGE, PROFILE, GRID_POOL, REPO,
    diffs_for, claimed_range, is_in_range, calculate_mismatch, verdict, tech_for_score,
    mulberry32, generate, pearson, analytics
)


class TestPublisherConstants:
    """Test publisher-related constants."""

    def test_publishers_list(self):
        """Test PUBLISHERS list matches JavaScript."""
        assert PUBLISHERS == [
            "The New York Times",
            "The Times",
            "The Guardian",
            "Sudoku.com"
        ]

    def test_publisher_short(self):
        """Test PUBLISHER_SHORT mapping."""
        assert PUBLISHER_SHORT["The New York Times"] == "NYT"
        assert PUBLISHER_SHORT["The Times"] == "Times"
        assert PUBLISHER_SHORT["The Guardian"] == "Guardian"
        assert PUBLISHER_SHORT["Sudoku.com"] == "Sudoku.com"

    def test_submit_publishers(self):
        """Test SUBMIT_PUBLISHERS list."""
        assert SUBMIT_PUBLISHERS == [
            "NYT", "Sudoku.com", "The Guardian", "Times Sudoku", "Others"
        ]

    def test_diffs(self):
        """Test DIFFS list."""
        assert DIFFS == ["Easy", "Medium", "Hard"]


class TestDifficultyMappings:
    """Test difficulty mappings per publisher."""

    def test_diff_by_publisher_nyt(self):
        """Test NYT difficulty options."""
        assert DIFF_BY_PUBLISHER["NYT"] == ["Easy", "Medium", "Hard"]

    def test_diff_by_publisher_sudoku_com(self):
        """Test Sudoku.com difficulty options."""
        assert DIFF_BY_PUBLISHER["Sudoku.com"] == [
            "Easy", "Medium", "Hard", "Expert", "Master", "Extreme"
        ]

    def test_diff_by_publisher_guardian(self):
        """Test The Guardian difficulty options."""
        assert DIFF_BY_PUBLISHER["The Guardian"] == [
            "Easy", "Medium", "Hard", "Expert"
        ]

    def test_diff_by_publisher_times(self):
        """Test Times Sudoku difficulty options."""
        assert DIFF_BY_PUBLISHER["Times Sudoku"] == [
            "Easy", "Mild", "Moderate", "Difficult", "Fiendish", "Super Fiendish"
        ]


class TestClaimedRanges:
    """Test claimed range mappings (low, high, midpoint)."""

    def test_claimed_ranges_nyt(self):
        """Test NYT claimed ranges."""
        assert CLAIMED_RANGES["NYT"]["Easy"] == (1, 3, 2)
        assert CLAIMED_RANGES["NYT"]["Medium"] == (4, 6, 5)
        assert CLAIMED_RANGES["NYT"]["Hard"] == (7, 10, 8)

    def test_claimed_ranges_sudoku_com(self):
        """Test Sudoku.com claimed ranges."""
        assert CLAIMED_RANGES["Sudoku.com"]["Easy"] == (1, 2, 1.5)
        assert CLAIMED_RANGES["Sudoku.com"]["Medium"] == (3, 4, 3.5)
        assert CLAIMED_RANGES["Sudoku.com"]["Hard"] == (5, 5, 5)
        assert CLAIMED_RANGES["Sudoku.com"]["Expert"] == (6, 7, 6.5)
        assert CLAIMED_RANGES["Sudoku.com"]["Master"] == (8, 8, 8)
        assert CLAIMED_RANGES["Sudoku.com"]["Extreme"] == (9, 10, 9.5)

    def test_claimed_ranges_guardian(self):
        """Test The Guardian claimed ranges."""
        assert CLAIMED_RANGES["The Guardian"]["Easy"] == (1, 3, 2)
        assert CLAIMED_RANGES["The Guardian"]["Medium"] == (4, 5, 4.5)
        assert CLAIMED_RANGES["The Guardian"]["Hard"] == (6, 7, 6.5)
        assert CLAIMED_RANGES["The Guardian"]["Expert"] == (8, 10, 9)

    def test_claimed_ranges_times(self):
        """Test Times Sudoku claimed ranges."""
        assert CLAIMED_RANGES["Times Sudoku"]["Easy"] == (1, 1, 1)
        assert CLAIMED_RANGES["Times Sudoku"]["Mild"] == (2, 2, 2)
        assert CLAIMED_RANGES["Times Sudoku"]["Moderate"] == (3, 4, 3.5)
        assert CLAIMED_RANGES["Times Sudoku"]["Difficult"] == (5, 6, 5.5)
        assert CLAIMED_RANGES["Times Sudoku"]["Fiendish"] == (7, 9, 8)
        assert CLAIMED_RANGES["Times Sudoku"]["Super Fiendish"] == (10, 10, 10)


class TestHelperFunctions:
    """Test helper functions."""

    def test_diffs_for_valid_publisher(self):
        """Test diffs_for with valid publisher."""
        assert diffs_for("NYT") == ["Easy", "Medium", "Hard"]
        assert diffs_for("Sudoku.com") == [
            "Easy", "Medium", "Hard", "Expert", "Master", "Extreme"
        ]

    def test_diffs_for_invalid_publisher(self):
        """Test diffs_for with invalid publisher returns empty list."""
        assert diffs_for("Unknown") == []

    def test_claimed_range_valid(self):
        """Test claimed_range with valid inputs."""
        assert claimed_range("NYT", "Easy") == (1, 3, 2)
        assert claimed_range("NYT", "Hard") == (7, 10, 8)
        assert claimed_range("Times Sudoku", "Super Fiendish") == (10, 10, 10)

    def test_claimed_range_invalid(self):
        """Test claimed_range with invalid inputs returns None."""
        assert claimed_range("Unknown", "Easy") is None
        assert claimed_range("NYT", "SuperHard") is None


class TestRangeHelpers:
    """Test range-based helper functions."""

    def test_is_in_range_true(self):
        """Test is_in_range returns True when score is within range."""
        assert is_in_range(2, 1, 3) is True
        assert is_in_range(1, 1, 3) is True  # boundary
        assert is_in_range(3, 1, 3) is True  # boundary
        assert is_in_range(5, 4, 6) is True

    def test_is_in_range_false(self):
        """Test is_in_range returns False when score is outside range."""
        assert is_in_range(0, 1, 3) is False
        assert is_in_range(4, 1, 3) is False
        assert is_in_range(7, 4, 6) is False

    def test_calculate_mismatch_in_range(self):
        """Test calculate_mismatch returns 0 when in range."""
        assert calculate_mismatch(2, 1, 3, 2) == 0.0
        assert calculate_mismatch(1, 1, 3, 2) == 0.0
        assert calculate_mismatch(3, 1, 3, 2) == 0.0
        assert calculate_mismatch(5, 4, 6, 5) == 0.0

    def test_calculate_mismatch_out_of_range(self):
        """Test calculate_mismatch returns difference from midpoint when outside."""
        assert calculate_mismatch(5, 1, 3, 2) == 3.0  # 5 - 2 = 3
        assert calculate_mismatch(1, 4, 6, 5) == -4.0  # 1 - 5 = -4
        assert calculate_mismatch(7, 1, 3, 2) == 5.0  # 7 - 2 = 5
        assert calculate_mismatch(8, 4, 6, 5) == 3.0  # 8 - 5 = 3


class TestVerdict:
    """Test verdict function with float mismatch values."""

    def test_verdict_accurate(self):
        """Test verdict for zero mismatch."""
        assert verdict(0) == "Accurate"
        assert verdict(0.0) == "Accurate"

    def test_verdict_underrated(self):
        """Test verdict for positive mismatch (underrated)."""
        assert verdict(1.0) == "Slightly Underrated"
        assert verdict(1.5) == "Slightly Underrated"
        assert verdict(2.0) == "Moderately Underrated"
        assert verdict(2.9) == "Moderately Underrated"
        assert verdict(3.0) == "Significantly Underrated"
        assert verdict(5.5) == "Significantly Underrated"

    def test_verdict_overrated(self):
        """Test verdict for negative mismatch (overrated)."""
        assert verdict(-1.0) == "Slightly Overrated"
        assert verdict(-1.5) == "Slightly Overrated"
        assert verdict(-2.0) == "Moderately Overrated"
        assert verdict(-2.9) == "Moderately Overrated"
        assert verdict(-3.0) == "Significantly Overrated"
        assert verdict(-5.5) == "Significantly Overrated"

    def test_verdict_edge_cases(self):
        """Test verdict for edge cases between thresholds."""
        # Values between -1 and 0, or between 0 and 1 should be Accurate
        assert verdict(0.5) == "Accurate"
        assert verdict(-0.5) == "Accurate"
        assert verdict(0.9) == "Accurate"
        assert verdict(-0.9) == "Accurate"


class TestTechniqueScale:
    """Test technique scale reference."""

    def test_technique_scale_count(self):
        """Test TECHNIQUE_SCALE has correct number of entries."""
        assert len(TECHNIQUE_SCALE) == 17

    def test_technique_scale_scores(self):
        """Test some technique scores."""
        # Find Full House
        full_house = next(t for t in TECHNIQUE_SCALE if t["name"] == "Full House")
        assert full_house["score"] == 1

        # Find X-Wing
        x_wing = next(t for t in TECHNIQUE_SCALE if t["name"] == "X-Wing")
        assert x_wing["score"] == 6

        # Find XY-Wing
        xy_wing = next(t for t in TECHNIQUE_SCALE if t["name"] == "XY-Wing")
        assert xy_wing["score"] == 9


class TestTechForScore:
    """Test tech_for_score function."""

    def test_tech_for_score_basic(self):
        """Test tech_for_score returns valid technique."""
        result = tech_for_score(1)
        assert result in ["Full House", "Naked Single"]

    def test_tech_for_score_x_wing(self):
        """Test tech_for_score for X-Wing score."""
        result = tech_for_score(6)
        assert result == "X-Wing"

    def test_tech_for_score_out_of_range(self):
        """Test tech_for_score for out-of-range score."""
        result = tech_for_score(15)
        assert result == "Advanced Out-of-Scope Technique"


class TestProfile:
    """Test publisher profile constants."""

    def test_profile_nyt(self):
        """Test NYT profile."""
        assert PROFILE["NYT"]["bias"] == 0.1
        assert PROFILE["NYT"]["noise"] == 0.9

    def test_profile_sudoku_com(self):
        """Test Sudoku.com profile."""
        assert PROFILE["Sudoku.com"]["bias"] == -1.6
        assert PROFILE["Sudoku.com"]["noise"] == 1.2


class TestGridPool:
    """Test GRID_POOL constants."""

    def test_grid_pool_count(self):
        """Test GRID_POOL has 6 puzzles."""
        assert len(GRID_POOL) == 6

    def test_grid_pool_length(self):
        """Test each grid in GRID_POOL is 81 characters."""
        for i, grid in enumerate(GRID_POOL):
            assert len(grid) == 81, f"GRID_POOL[{i}] has length {len(grid)}"


class TestMulberry32:
    """Test mulberry32 RNG."""

    def test_mulberry32_deterministic(self):
        """Test mulberry32 produces same sequence for same seed."""
        rng1 = mulberry32(12345)
        rng2 = mulberry32(12345)

        values1 = [rng1() for _ in range(10)]
        values2 = [rng2() for _ in range(10)]

        assert values1 == values2

    def test_mulberry32_range(self):
        """Test mulberry32 produces values in [0, 1)."""
        rng = mulberry32(20260531)
        for _ in range(100):
            v = rng()
            assert 0 <= v < 1

    def test_mulberry32_different_seeds(self):
        """Test different seeds produce different sequences."""
        rng1 = mulberry32(12345)
        rng2 = mulberry32(54321)

        values1 = [rng1() for _ in range(10)]
        values2 = [rng2() for _ in range(10)]

        assert values1 != values2


class TestGenerate:
    """Test generate function with range-based validation."""

    def test_generate_count(self):
        """Test generate produces correct number of records."""
        records = generate(10)
        assert len(records) == 10

    def test_generate_deterministic(self):
        """Test generate produces same records for same seed."""
        records1 = generate(10, seed=12345)
        records2 = generate(10, seed=12345)

        for i in range(10):
            assert records1[i]["id"] == records2[i]["id"]
            assert records1[i]["publisher"] == records2[i]["publisher"]
            assert records1[i]["measuredScore"] == records2[i]["measuredScore"]
            assert records1[i]["mismatch"] == records2[i]["mismatch"]
            assert records1[i]["inRange"] == records2[i]["inRange"]

    def test_generate_record_structure(self):
        """Test generated records have required fields for range-based validation."""
        records = generate(5)
        for record in records:
            # Base fields
            assert "id" in record
            assert "publisher" in record
            assert "publisherShort" in record
            assert "claimed" in record
            # Range-based fields (new)
            assert "claimedRangeLow" in record
            assert "claimedRangeHigh" in record
            assert "claimedMidpoint" in record
            assert "inRange" in record
            # Measured and calculated fields
            assert "measuredScore" in record
            assert "mismatch" in record
            assert "verdict" in record
            # Additional fields
            assert "tech" in record
            assert "clues" in record
            assert "grid" in record
            assert "date" in record
            assert "source" in record

    def test_generate_id_format(self):
        """Test generated IDs have correct format."""
        records = generate(5)
        for i, record in enumerate(records):
            expected_id = f"SDK-{1042 + i:04d}"
            assert record["id"] == expected_id

    def test_generate_range_fields_valid(self):
        """Test range fields are valid tuples from CLAIMED_RANGES."""
        records = generate(50)
        for record in records:
            publisher = record["publisher"]
            claimed = record["claimed"]
            expected_range = claimed_range(publisher, claimed)
            assert expected_range is not None
            assert record["claimedRangeLow"] == expected_range[0]
            assert record["claimedRangeHigh"] == expected_range[1]
            assert record["claimedMidpoint"] == expected_range[2]

    def test_generate_mismatch_calculation(self):
        """Test mismatch is calculated using range-based validation."""
        records = generate(100)
        for record in records:
            range_low = record["claimedRangeLow"]
            range_high = record["claimedRangeHigh"]
            midpoint = record["claimedMidpoint"]
            measured = record["measuredScore"]
            expected_mismatch = calculate_mismatch(measured, range_low, range_high, midpoint)
            assert record["mismatch"] == expected_mismatch

    def test_generate_in_range_correct(self):
        """Test inRange field correctly reflects whether measured is in claimed range."""
        records = generate(100)
        for record in records:
            range_low = record["claimedRangeLow"]
            range_high = record["claimedRangeHigh"]
            measured = record["measuredScore"]
            expected_in_range = is_in_range(measured, range_low, range_high)
            assert record["inRange"] == expected_in_range

    def test_generate_in_range_implies_zero_mismatch(self):
        """Test that inRange=True always means mismatch=0."""
        records = generate(100)
        for record in records:
            if record["inRange"]:
                assert record["mismatch"] == 0.0
            else:
                # When out of range, mismatch should be non-zero
                assert record["mismatch"] != 0.0

    def test_generate_verdict_matches_mismatch(self):
        """Test verdict matches mismatch value."""
        records = generate(100)
        for record in records:
            expected_verdict = verdict(record["mismatch"])
            assert record["verdict"] == expected_verdict


class TestRepo:
    """Test pre-generated REPO constant with range-based fields."""

    def test_repo_count(self):
        """Test REPO has 36 records."""
        assert len(REPO) == 36

    def test_repo_structure(self):
        """Test REPO records have required range-based fields."""
        for record in REPO:
            # Core fields
            assert "id" in record
            assert "publisher" in record
            assert "measuredScore" in record
            # Range-based fields
            assert "claimedRangeLow" in record
            assert "claimedRangeHigh" in record
            assert "claimedMidpoint" in record
            assert "inRange" in record
            assert "mismatch" in record
            assert "verdict" in record

    def test_repo_in_range_consistency(self):
        """Test REPO inRange field is consistent with mismatch."""
        for record in REPO:
            if record["inRange"]:
                assert record["mismatch"] == 0.0
            else:
                assert record["mismatch"] != 0.0


class TestPearson:
    """Test Pearson correlation function."""

    def test_pearson_perfect_positive(self):
        """Test Pearson correlation of 1 for perfect positive correlation."""
        xs = [1, 2, 3, 4, 5]
        ys = [2, 4, 6, 8, 10]
        r = pearson(xs, ys)
        assert abs(r - 1.0) < 0.0001

    def test_pearson_perfect_negative(self):
        """Test Pearson correlation of -1 for perfect negative correlation."""
        xs = [1, 2, 3, 4, 5]
        ys = [10, 8, 6, 4, 2]
        r = pearson(xs, ys)
        assert abs(r - (-1.0)) < 0.0001

    def test_pearson_no_correlation(self):
        """Test Pearson correlation near 0 for no correlation."""
        xs = [1, 2, 3, 4, 5]
        ys = [3, 1, 4, 1, 5]  # Roughly random
        r = pearson(xs, ys)
        assert -0.5 < r < 0.5

    def test_pearson_insufficient_data(self):
        """Test Pearson returns 0 for insufficient data."""
        assert pearson([1], [1]) == 0
        assert pearson([], []) == 0


class TestAnalytics:
    """Test analytics function."""

    def test_analytics_structure(self):
        """Test analytics returns correct structure."""
        result = analytics(REPO)

        assert "pearson" in result
        assert "agreement" in result
        assert "accurate" in result
        assert "over" in result
        assert "under" in result
        assert "meanMeasured" in result
        assert "meanAbsMismatch" in result
        assert "leaderboard" in result
        assert "n" in result

    def test_analytics_counts(self):
        """Test analytics counts are consistent."""
        result = analytics(REPO)

        # accurate + over + under should equal n
        assert result["accurate"] + result["over"] + result["under"] == result["n"]

    def test_analytics_leaderboard_structure(self):
        """Test leaderboard entries have required fields."""
        result = analytics(REPO)

        for entry in result["leaderboard"]:
            assert "publisher" in entry
            assert "short" in entry
            assert "n" in entry
            assert "accuracy" in entry
            assert "over" in entry
            assert "under" in entry
            assert "meanMismatch" in entry
            assert "tendency" in entry

    def test_analytics_leaderboard_sorted(self):
        """Test leaderboard is sorted by accuracy descending."""
        result = analytics(REPO)

        accuracies = [entry["accuracy"] for entry in result["leaderboard"]]
        assert accuracies == sorted(accuracies, reverse=True)

    def test_analytics_tendency(self):
        """Test tendency is correctly calculated."""
        result = analytics(REPO)

        for entry in result["leaderboard"]:
            mean_mismatch = entry["meanMismatch"]
            if mean_mismatch > 0.4:
                assert entry["tendency"] == "under-rates"
            elif mean_mismatch < -0.4:
                assert entry["tendency"] == "over-rates"
            else:
                assert entry["tendency"] == "balanced"


class TestScoreRange:
    """Test SCORE_RANGE constants."""

    def test_score_range_values(self):
        """Test SCORE_RANGE has correct values."""
        assert SCORE_RANGE["Easy"] == [110, 255]
        assert SCORE_RANGE["Medium"] == [260, 515]
        assert SCORE_RANGE["Hard"] == [525, 955]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
