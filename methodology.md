# Sudoku Difficulty Audit - Methodology

> An analytical tool that accepts any user-submitted Sudoku puzzle, measures its objective difficulty against a defined technique scoring scale, and compares that measurement against the difficulty label assigned by the puzzle's publisher.

| Tool type | Publisher frameworks | Scoring scale | Analysis type |
|---|---|---|---|
| User-driven analysis | 4 supported publishers | 1–10 technique tiers | Mismatch scoring |

---

## Contents

1. [How the Tool Works](#1-how-the-tool-works)
2. [Publisher Frameworks](#2-publisher-frameworks)
3. [Measuring Difficulty: The Technique Scoring Scale](#3-measuring-difficulty-the-technique-scoring-scale)
4. [Converting Claimed Difficulty to a Numeric Score](#4-converting-claimed-difficulty-to-a-numeric-score)
5. [Mismatch Scoring Framework](#5-mismatch-scoring-framework)
6. [Limitations](#6-limitations)

---

## 1. How the Tool Works

The tool does not operate on a pre-collected dataset. Instead, it is designed to analyse any puzzle a user chooses to submit. The workflow is as follows:

1. **Upload** — the user submits a Sudoku puzzle of their choice.
2. **Attribute** — the user specifies which publisher the puzzle is from and which difficulty label it was assigned (e.g. NYT Hard, Guardian Expert).
3. **Measure** — the tool determines the hardest-solving technique required to complete the puzzle without guessing and maps this to a score on the 1–10 technique scale.
4. **Compare** — the measured score is compared against the claimed score derived from the publisher's label.
5. **Verdict** — a mismatch value is calculated and a verdict label is assigned.

The four supported publishers are not part of the study sample. They are reference frameworks built into the tool, each with a defined difficulty-labelling system and a pre-established mapping from label to numeric score, against which any submitted puzzle can be benchmarked.

---

## 2. Publisher Frameworks

Four publishers are supported as reference frameworks. They were selected because each meets a specific set of criteria that make their labelling systems meaningful for comparison with objective measurement.

### Selection criteria

A publisher is included as a supported framework if it meets all of the following:

- **Named difficulty tiers** — uses a clearly defined, publicly visible difficulty-labelling system applied consistently across puzzles.
- **Distinct tier structure** — has a labelling system that is meaningfully different from the others, either in the number of tiers, the tier names, or the implied difficulty range.
- **Publicly documented conventions** — its difficulty expectations are inferable or explicitly stated in public-facing descriptions, making a claimed score mapping defensible.
- **Audience representativeness** — covers a distinct segment of the solver spectrum, so the tool is useful across a range of puzzle contexts.

### Supported publishers

| Publisher | Audience type | Difficulty tiers |
|---|---|---|
| New York Times | Casual / mainstream | Easy, Medium, Hard |
| Sudoku.com | General digital | Easy, Medium, Hard, Expert, Master, Extreme |
| The Guardian | Broadsheet / mixed | Easy, Medium, Hard, Expert |
| Times Sudoku | Enthusiast / specialist | Easy, Mild, Moderate, Difficult, Fiendish, Super Fiendish |

The four publishers span a wide range of tier granularity — from NYT's three-tier system to the six-tier systems used by Sudoku.com and Times Sudoku. This variation is intentional: it allows the tool to surface how labelling precision differs across publishers, not just how accurate any single publisher's labels are.

> **Note:** If a user submits a puzzle from a publisher not on this list, the tool still performs a full mismatch analysis. A set of fixed claimed-score mappings has been defined for unsupported publishers, using the same methodology as the four supported frameworks. The user specifies the publisher's label, and the tool maps it to a claimed score using these pre-established criteria.

---

## 3. Measuring Difficulty: The Technique Scoring Scale

Objective difficulty is operationalised as the **hardest solving technique required to complete the puzzle without guessing**. This approach is standard in the Sudoku analysis literature and mirrors the methodology used by automated grading tools such as Sudoku Wiki.

> **Scoring principle:** A puzzle that requires an X-Wing at any point — regardless of how many simpler techniques were also applied — receives a score of 6 (X-Wing). Difficulty reflects the ceiling of the required technique, not an average across all steps taken.

### Technique scoring scale

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

If a submitted puzzle requires a technique not present on the scale — such as ALS-XZ or Sue de Coq — it is assigned a measured score of 10. This places it at the top of the advanced tier without distorting the scale. The result is noted as out of scope in the tool output, indicating that the true difficulty may exceed what the scale can precisely represent.

---

## 4. Converting Claimed Difficulty to a Numeric Score

Publisher difficulty labels are categorical. They describe relative difficulty within a publisher's own system, not a universal standard. To calculate a mismatch between claimed and measured difficulty, each label is converted to a single numeric score on the 1–10 technique scale. This conversion is built into the tool for each supported publisher.


> **Methodological note:** These mappings are not factual claims about publisher intent. They are calibrated anchor points defined in advance and applied consistently. A different mapping — equally reasonable — would produce different mismatch values. This is a documented design choice, not a finding.

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

### Other

| Label | Claimed score |
|---|---|
| Easy | 2 |
| Medium | 4 |
| Hard | 6 |

---

## 5. Mismatch Scoring Framework

The core output of the tool is the **mismatch value**, a signed integer representing the gap between what a publisher claims a puzzle's difficulty to be and what objective technique analysis reveals it to actually be.

### Formula

```
mismatch = measured_score − claimed_score
```

A positive value indicates the puzzle is harder than labelled (underrated). A negative value indicates it is easier than labelled (overrated). A value of zero indicates an accurate label.

### Verdict classification

| Mismatch value | Verdict | Plain-English meaning |
|---|---|---|
| 0 | Accurate | The label matches the measured difficulty |
| +1 | Slightly underrated | A little harder than the label suggests |
| +2 | Moderately underrated | Noticeably harder than the label suggests |
| +3 or more | Significantly underrated | Much harder than the label suggests — potentially misleading |
| −1 | Slightly overrated | A little easier than the label suggests |
| −2 | Moderately overrated | Noticeably easier than the label suggests |
| −3 or more | Significantly overrated | Much easier than the label suggests — potentially misleading |

> **Interpretive note:** Verdicts of "significantly underrated" or "significantly overrated" do not imply publisher intent to mislead. They describe the scale of the discrepancy between the label and the objective measurement, which may reflect editorial convention, audience calibration, or the inherent imprecision of categorical labels.

---

## 6. Limitations

Several design choices in this tool affect how results should be interpreted. Each is documented below.

### Results reflect individual puzzles, not publisher patterns

Because the tool analyses puzzles submitted one at a time by the user, any result reflects a single puzzle, not a statistically representative sample of a publisher's output. A single "Significantly underrated" verdict does not mean a publisher consistently mislabels puzzles at that tier. Patterns can only be inferred if a user submits multiple puzzles from the same publisher and tier.

### Tier count disparity across publishers

The NYT uses three difficulty tiers, while Sudoku.com and Times Sudoku use six. Publishers with more tiers have greater labelling precision, meaning their puzzles are constrained to narrower bands of expected difficulty. Mismatch magnitudes are therefore not directly comparable across publishers: a mismatch of +2 for a NYT puzzle carries different interpretive weight than a mismatch of +2 for a Times Sudoku puzzle.

### Claimed score mapping involves judgment

Converting categorical labels to numeric scores requires interpretive decisions. The mappings are defined in advance and held constant, but a different mapping — equally defensible — would produce different mismatch values. This is a documented design choice, not a factual claim about publisher intent.

### Out-of-scope technique handling

Puzzles requiring techniques beyond the defined scale are assigned a measured score of 10. This prevents scale distortion but means the score represents a floor rather than a precise measurement. The tool flags these cases explicitly in its output.

### Single-technique scoring model

Difficulty is assigned based on the hardest technique required, not a weighted average across all techniques applied. Two puzzles with the same maximum technique score may differ substantially in overall solving effort if one requires repeated advanced steps while the other requires it only once.
