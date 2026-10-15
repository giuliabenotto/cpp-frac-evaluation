# CPP + FrAC Reproducibility Package

This repository contains the reproducibility package for the functional evaluation of the **Collocation Processing Profile (CPP)** described in the associated paper. The experiment tests whether process-level information represented with CPP, P-Plan, and PROV-O makes methodological conditions directly queryable alongside FrAC collocation observations.

This revised version replaces the original toy corpora with a substantially larger, deterministic synthetic dataset. The four competency questions preserve the same methodological objectives and expected results. This aligned edition updates their vocabulary IRIs and measure identifiers; see the alignment notes below.

## 1. Revised dataset

The package contains two controlled English corpus snapshots with different collocational frequency profiles:

| Corpus | Sentences | Word tokens | `rain` tokens |
|---|---:|---:|---:|
| Corpus A | 17,616 | 171,736 | 6,936 |
| Corpus B | 17,620 | 171,764 | 6,940 |

Each corpus contains **24 controlled adjective--`rain` patterns** plus standalone adjective occurrences, standalone `rain` occurrences, and neutral filler sentences. Of these 24 patterns, five are used as explicit FrAC evaluation candidates:

- `heavy rain`
- `torrential rain`
- `intermittent rain`
- `soaking rain`
- `seasonal rain`

The five candidates were selected to cover different score behaviours: clearly above threshold, near threshold, crossing the threshold when the context window is widened, and below threshold. The remaining controlled adjective--`rain` patterns act as corpus background/distractors and contribute to the corpus marginals used in score calculation.

The corpora are generated deterministically by `scripts/build_dataset.py`. For each controlled adjective, the generator creates:

1. occurrences within five tokens of `rain`;
2. additional occurrences at distances six to ten tokens from `rain`;
3. standalone adjective occurrences outside a `rain` context;
4. additional `rain`-only and neutral filler sentences.

The logDice values stored in RDF are therefore no longer arbitrary scores. They are calculated directly from the generated corpus frequencies using:

```text
logDice(x,y) = 14 + log2(2 * f(x,y) / (f(x) + f(y)))
```

where `f(x,y)` is computed with the configured 5-token or 10-token sentence-bounded window. Detailed corpus and collocate counts are provided in:

- `corpus/corpus_statistics.csv`
- `corpus/collocate_statistics.csv`

## 2. RDF evaluation design

The RDF graphs contain the same **38 FrAC collocation observations distributed across eight runs**.

- `data/baseline_frac.ttl` contains FrAC observations, corpus references, corpus-derived logDice scores, and human-readable descriptions of the extraction procedure.
- `data/cpp_enriched.ttl` contains the same observations plus structured CPP/P-Plan/PROV-O information about runs, software, human agents, corpus and index bindings, context-window parameters, sentence constraints, ordering, minimum frequency, POS pattern, and association measure.

The eight runs deliberately vary methodological conditions:

| Run | Corpus | Software | Window | Min. freq. | Analyst | Special role |
|---|---|---|---:|---:|---|---|
| r1 | A | Extractor v1 | 5/5 | 3 | A | reference configuration |
| r2 | A | Extractor v1 | 10/10 | 3 | B | wider-window comparison |
| r3 | B | Extractor v1 | 5/5 | 3 | A | cross-corpus counterpart of r1 |
| r4 | B | Extractor v1 | 10/10 | 3 | B | cross-corpus counterpart of r2 |
| r5 | A | Extractor v1 | 5/5 | 10 | C | stricter minimum frequency |
| r6 | B | Extractor v2 | 5/5 | 3 | A | incompatible software version |
| r7 | A | Extractor v1 | left=5 | 3 | B | right window intentionally undocumented |
| r8 | B | Extractor v1 | 5/5 | 10 | C | cross-corpus counterpart of r5 |

The stricter minimum-frequency runs omit candidates whose observed frequency does not reach 10. Run r7 preserves an intentionally incomplete provenance record so that protocol completeness remains testable.

## 3. Competency questions

The four original competency questions are retained in their methodological intent, with vocabulary identifiers updated to match the current ontologies:

1. **Protocol-aware selection:** Which collocation candidates satisfy both a statistical threshold and an explicitly defined extraction protocol?
2. **Collaborative diagnosis:** When two lexicographers obtain different scores for the same candidate on the same corpus, which recorded methodological differences distinguish their runs?
3. **Controlled cross-corpus comparison:** Which observations from two corpora can be compared while keeping the recorded methodological conditions constant?
4. **Stability across configurations:** Which candidates remain above a threshold across a predefined set of alternative extraction configurations?

A fifth query is used as a control. It asks only for collocations whose logDice score is at least 7. The control must return exactly the same observations from the FrAC baseline and from the CPP-enriched graph.

### Repository structure

```text
.
├── corpus/
│   ├── corpus_a.txt
│   ├── corpus_b.txt
│   ├── corpus_statistics.csv
│   └── collocate_statistics.csv
├── data/
│   ├── baseline_frac.ttl
│   └── cpp_enriched.ttl
├── queries/
│   ├── q0_control_above_threshold.rq
│   ├── cq1_protocol_filter.rq
│   ├── cq2_collaborative_difference.rq
│   ├── cq3_cross_corpus_compatible.rq
│   └── cq4_stability_across_configurations.rq
├── expected_results/
│   └── *.csv
├── results/
│   └── .gitkeep
├── scripts/
│   ├── build_dataset.py
│   ├── query_worker.py
│   └── run_tests.py
├── .github/workflows/tests.yml
├── ontology/
│   ├── cpp.owl
│   └── collocation-score.owl
├── ALIGNMENT_REPORT.md
├── CITATION.cff
├── LICENSE-CODE
├── LICENSE-DATA
├── requirements.txt
└── README.md
```

## 4. Reproducing the evaluation

### Requirements

- Python 3.10 or newer
- `pip`
- Internet access only for the initial installation of the Python dependency

The package uses **RDFLib 7.5.0**, pinned in `requirements.txt`.

### Step 1: create a virtual environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 2: install the dependency

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 3: optionally regenerate the dataset

The distributed corpus and RDF files are already generated. To recreate them deterministically from the specification:

```bash
python scripts/build_dataset.py
```

The generator also rewrites the two corpus-statistics CSV files.

### Step 4: run the complete evaluation

```bash
python scripts/run_tests.py
```

Before the SPARQL assertions, the runner now performs explicit scale checks requiring each corpus to contain at least 100,000 word tokens and 10,000 sentences and requiring the RDF graphs to contain at least 35 matching FrAC observations.

A successful run ends with results equivalent to:

```text
PASS control: 23 identical observations in baseline and CPP graphs
PASS cq1_protocol_filter.rq: baseline=0 rows, CPP=3 rows
PASS cq2_collaborative_difference.rq: baseline=0 rows, CPP=10 rows
PASS cq3_cross_corpus_compatible.rq: baseline=0 rows, CPP=14 rows
PASS cq4_stability_across_configurations.rq: baseline=0 rows, CPP=3 rows

All reproducibility tests passed.
```

The script writes the actual query outputs as CSV files under `results/` and compares each CPP result with the corresponding snapshot under `expected_results/`. Any difference causes the test runner to fail.

The methodological competency queries are also executed against the FrAC baseline. Their expected baseline result is zero structured bindings because the required process relations are not represented as queryable graph relations there; the methodological conditions are available only in human-readable descriptions. This does **not** mean that the information is absent to a human reader, but that it cannot be recovered by these structured SPARQL queries without additional conventions or text-processing logic.

> Note: compared with the early toy package, the competency questions retain their methodological intent. The present query files were updated to use the current CPP and CollScore IRIs; they are not byte-identical to the historical query files.

## 5. Expected results

| Test | FrAC baseline | FrAC + CPP | Interpretation |
|---|---:|---:|---|
| Control: logDice >= 7 | 23 rows | 23 rows | CPP enrichment does not alter the linguistic/statistical observations returned by a score-only query. |
| CQ1: protocol-aware selection | 0 structured rows | 3 rows | `heavy rain`, `torrential rain`, and `intermittent rain` satisfy both the score threshold and the complete target protocol. The incomplete-provenance run is excluded structurally. |
| CQ2: collaborative diagnosis | 0 structured rows | 10 rows | Five shared candidates are compared between r1 and r2; for each candidate, the two recorded differences are the left and right context windows (5 vs. 10 tokens). |
| CQ3: controlled cross-corpus comparison | 0 structured rows | 14 rows | Compatible pairs come from r1-r3, r2-r4, and r5-r8. The stricter r5-r8 pair contributes four candidates because `seasonal rain` does not meet the minimum-frequency threshold. Runs using another software version or incomplete provenance are excluded. |
| CQ4: stability across configurations | 0 structured rows | 3 rows | `heavy rain`, `torrential rain`, and `intermittent rain` remain at or above threshold in all three predefined runs r1, r2, and r5. |

The revised dataset preserves the original purpose of the evaluation while removing the most obvious toy-scale limitation. It remains a **controlled synthetic functional evaluation**, not an evaluation of extractor accuracy on a naturally sampled reference corpus. Its purpose is to test whether CPP adds method-aware queryability to FrAC observations under a substantially larger and internally coherent corpus setting.

## License and reuse

This reproducibility package uses separate licenses according to the material:

- **Python scripts** in `scripts/`: [MIT License](LICENSE-CODE).
- **Synthetic corpora, RDF evaluation data, CSVs, SPARQL queries, and original documentation**: [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-DATA).
- **Bundled ontology copies** in `ontology/`: consult the respective upstream repositories ([CPP](https://github.com/giuliabenotto/collocation-processing-profile) and [CollScore](https://github.com/giuliabenotto/collscore)) for applicable licensing and attribution.

For academic reuse, please also cite this repository via [CITATION.cff](CITATION.cff) and the associated article once published. Citation of the paper is requested as scholarly practice, but is not an additional legal condition of the licenses.

## Related resources

- [Collocation Processing Profile (CPP) ontology](https://github.com/giuliabenotto/collocation-processing-profile)
- [CollScore: A Vocabulary for Collocation Scoring Measures](https://github.com/giuliabenotto/collscore)

**Associated manuscript (working title):** *From Co-occurrence to Collocation: Bridging Corpus Evidence, Statistical Analysis, and Lexical Representation*. Full bibliographic details will be provided when available. The benchmark is a functional demonstration, not an independent evaluation of linguistic accuracy.

## Alignment with the published vocabularies (2026-10-15)

This release aligns the benchmark with the supplied updated CPP ontology and CollScore vocabulary:

- CPP namespace: `https://ilc.cnr.it/klab/ontology/cpp#`.
- Statistical score property: `collscore:logDice` (subproperty of `frac:cScore`).
- The configuration value for selected measures uses `collscore:LogDice` as the measure individual, distinct from the numeric scoring property.
- The original four competency-question **semantics** and Q0 control are maintained. Query source files have been updated to use the definitive identifiers; they are therefore not byte-identical to the historical queries.
- The original synthetic corpus generator, run specifications, ranking thresholds, and expected results are retained.
- Copies of the supplied CollScore ontology and the latest CPP ontology are provided in `ontology/` without modifying their content. The CPP copy is the 346-triple version supplied on 15 October 2026, whose namespace and `rdfs:isDefinedBy` statements use `https://ilc.cnr.it/klab/ontology/cpp#`. The benchmark uses the same namespace. Ontology imports and OWL-DL consistency require independent checking.

Reproduce with `python scripts/build_dataset.py` and `python scripts/run_tests.py`.
