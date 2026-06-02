# Sudoku Difficulty Audit — Methodology

> A systematic investigation into whether publisher-assigned difficulty labels accurately reflect the objective solving complexity of Sudoku puzzles across four major platforms.

| Project type | Publishers covered | Scoring scale | Analysis type |
|---|---|---|---|
| Analytical Audit | 4 platforms | 1–10 technique tiers | Mismatch scoring |

---

## Contents

1. [Publisher Selection](#1-publisher-selection)
2. [Measuring Difficulty: The Technique Scoring Scale](#2-measuring-difficulty-the-technique-scoring-scale)
3. [Converting Claimed Difficulty to a Numeric Score](#3-converting-claimed-difficulty-to-a-numeric-score)
4. [Mismatch Scoring Framework](#4-mismatch-scoring-framework)
5. [Limitations](#5-limitations)

---

## 1. Publisher Selection

Four publishers were selected to provide a representative cross-section of the Sudoku publishing landscape. Selection was not arbitrary — each publisher was evaluated against a fixed set of inclusion criteria designed to ensure comparability and analytical rigour.

### Inclusion criteria

Each publisher included in the study met all four of the following conditions:

- **Daily publication** — publishes new puzzles on a daily basis, ensuring a consistent and ongoing archive
- **Archive accessibility** — maintains a retrievable archive of historical puzzles available for analysis
- **Distinct labelling system** — uses a named difficulty-labelling system applied consistently across all published puzzles
- **Audience diversity** — represents a distinct segment of the solver spectrum, from casual to enthusiast audiences

### Selected publishers

| Publisher | Audience type | Difficulty tiers |
|---|---|---|
| New York Times | Casual / mainstream | Easy, Medium, Hard |
| Sudoku.com | General digital | Easy, Medium, Hard, Expert, Master, Extreme |
| The Guardian | Broadsheet / mixed | Easy, Medium, Hard, Expert |
| Times Sudoku | Enthusiast / specialist | Easy, Mild, Moderate, Difficult, Fiendish, Super Fiendish |

The four publishers span a wide range of tier granularity — from NYT's three-tier system to the six-tier systems used by Sudoku.com and Times Sudoku. This variation is itself a feature of the dataset, not a flaw, and is explicitly accounted for in the analysis design.

---

## 2. Measuring Difficulty: The Technique Scoring Scale

Objective difficulty is operationalised as the **hardest solving technique required to complete the puzzle without guessing**. This approach is standard in the Sudoku analysis literature and mirrors the methodology used by automated grading tools such as Sudoku Wiki.

> **Scoring principle:** A puzzle that requires an X-Wing at any point — regardless of how many simpler techniques were also applied — receives a score of 6 (X-Wing). Difficulty reflects the ceiling of technique required, not an average across all steps taken.

### Technique scoring scale

The scale below was defined in full before data collection began. No adjustments were made after reviewing results.

| Score | Techniques | Complexity tier |
|---|---|---|
| 1 | Full house, Naked Single | Trivial — no elimination strategy required |
| 2 | Hidden Single | Beginner — basic scanning |
| 3 | Pointing pairs, Box-line reduction | Elementary — candidate filtering |
| 4 | Naked pair / triple / quad | Intermediate — subset elimination |
| 5 | Hidden pair / triple / quad | Intermediate — hidden subsets |
| 6 | X-Wing | Advanced — pattern recognition |
| 7 | Swordfish, X-Colours | Advanced — multi-row patterns |
| 8 | Jellyfish | Expert — four-row structures |
| 9 | XY-Wing, W-Wing, Skyscraper, Empty rectangle | Expert — chain and wing logic |
| 10 | XYZ-Wing, Unique rectangle | Master — uniqueness and chains |

The scale runs from 1 (trivially easy) to 10 (advanced chain and uniqueness reasoning). The ordering reflects both the cognitive difficulty of identifying each technique and the frequency with which each appears in standard puzzle grading literature.

### Out-of-scope techniques

If a puzzle required a technique not present on the scale — such as ALS-XZ or Sue de Coq — it was recorded as out of scope and assigned a measured score of 10. This places it at the top of the advanced tier without distorting the scale or requiring post-hoc additions to the framework.

---

## 3. Converting Claimed Difficulty to a Numeric Score

Publisher difficulty labels are categorical — they describe relative difficulty within a publisher's own system, not a universal standard. To calculate a mismatch between claimed and measured difficulty, each label was converted to a single numeric score on the 1–10 technique scale.

The mapping was anchored to publicly available descriptions of each publisher's difficulty system — most explicitly for Times Sudoku, which publishes its own technique-based tier definitions. All mappings were finalised before data collection began and held constant throughout the study.

> **Methodological note:** These mappings are not factual claims about publisher intent. They are calibrated anchor points, defined in advance and applied consistently. A different reasonable mapping would produce different mismatch values — this is a documented design choice, not a finding.

### New York Times

| Label | Claimed score |
|---|---|
| Easy | 2 |
| Medium | 4 |
| Hard | 6 |

### Sudoku.com

| Label | Claimed score |
|---|---|
| Easy | 2 |
| Medium | 4 |
| Hard | 5 |
| Expert | 7 |
| Master | 8 |
| Extreme | 9 |

### The Guardian

| Label | Claimed score |
|---|---|
| Easy | 2 |
| Medium | 4 |
| Hard | 7 |
| Expert | 9 |

### Times Sudoku

| Label | Claimed score |
|---|---|
| Easy | 1 |
| Mild | 2 |
| Moderate | 4 |
| Difficult | 6 |
| Fiendish | 9 |
| Super Fiendish | 10 |

---

## 4. Mismatch Scoring Framework

The core analytical output of this study is the **mismatch value** — a signed integer representing the gap between what a publisher claims a puzzle's difficulty to be and what objective technique analysis reveals it to actually be.

### Formula

```
mismatch = measured_score − claimed_score
```

A positive value indicates the puzzle is harder than labelled (underrated). A negative value indicates it is easier than labelled (overrated). A value of zero indicates an accurate label.

### Verdict classification

| Mismatch value | Verdict | Plain-English meaning |
|---|---|---|
| 0 | Accurate | Publisher got it right |
| +1 | Slightly underrated | A little harder than claimed |
| +2 | Moderately underrated | Noticeably harder than claimed |
| +3 or more | Significantly underrated | Much harder than claimed — potentially misleading |
| −1 | Slightly overrated | A little easier than claimed |
| −2 | Moderately overrated | Noticeably easier than claimed |
| −3 or more | Significantly overrated | Much easier than claimed — potentially misleading |

> **Interpretive note:** Verdicts of "significantly underrated" or "significantly overrated" do not imply publisher intent to mislead. They describe the scale of discrepancy between label and objective measurement. Causes may include editorial convention, audience calibration, or the inherent imprecision of categorical labels.

---

## 5. Limitations

This methodology involves several design choices that affect interpretation of results. Each is documented transparently below.

### Tier count disparity across publishers

The NYT uses three difficulty tiers while Sudoku.com and Times Sudoku use six. Publishers with more tiers have greater precision within their system, meaning their puzzles are constrained to narrower bands of expected difficulty. As a result, raw mismatch magnitudes are not directly comparable across publishers. Within-tier variance analyses are more appropriate for cross-publisher comparisons than raw mismatch values.

### Claimed score mapping involves judgment

Converting categorical labels to numeric scores requires interpretive decisions. While the mapping was defined before data collection and held constant throughout, a different mapping — equally defensible — would produce different mismatch values. This is a documented methodological choice, not a factual claim about what publishers intend their labels to mean.

### Out-of-scope technique handling

Puzzles requiring techniques beyond the defined scale are assigned a measured score of 10. This prevents scale distortion but means the measured score for these puzzles represents a floor, not a precise measurement. Their true difficulty may exceed 10 on any extended scale.

### Single-technique scoring model

Difficulty is assigned based on the hardest technique required, not a weighted average across all techniques applied. This is consistent with industry convention but means two puzzles with the same maximum technique score may differ substantially in overall solving effort — if one requires repeated advanced steps while the other requires it only once.