# Alignment and reproduction report — 2026-10-15

## Sources

- Updated CPP: user-supplied `cpp(3).owl`, incorporated unchanged as `ontology/cpp.owl` (346 RDF triples, parsed as Turtle).
- CollScore: user-supplied `collocation score.owl`, incorporated unchanged as `ontology/collocation-score.owl` (699 RDF triples, parsed as RDF/XML).
- Base benchmark: `cpp-frac-reproducibility-expanded(1).zip`.

## Changes to the benchmark

1. Updated the CPP namespace in the generator, queries and URI formatters from `https://example.org/cpp/` to `https://ilc.cnr.it/klab/ontology/cpp#`.
2. Replaced observation-score predicates `lexinfo:logDice` with `collscore:logDice` (`https://ilc.cnr.it/klab/ontology/cooccurrence-measures#logDice`).
3. Updated the configured-measure set (`rdf:Bag`) to contain `collscore:LogDice`, the named measure individual, distinct from the numerical data property. Updated relevant query joins accordingly.
4. Regenerated both corpora and the two RDF data graphs. Left the control protocol, run design, thresholds, corpus profiles and expected CSV outputs unchanged.
5. Retained the provided ontologies byte for byte, without editing their internal declarations.

## Reproduction

From the package directory, with Python and requirements installed:

```bash
python scripts/build_dataset.py
python scripts/run_tests.py
```

Results of the execution:

| Test | Baseline | Enriched | Status |
|---|---:|---:|---|
| Q0 | 23 | 23 | PASS; identical rows |
| CQ1 | 0 | 3 | PASS |
| CQ2 | 0 | 10 | PASS |
| CQ3 | 0 | 14 | PASS |
| CQ4 | 0 | 3 | PASS |

Corpus A: 17,616 sentences, 165,477 tokens. Corpus B: 17,620 sentences, 165,525 tokens. Both graphs contain 38 FrAC collocation observations. Triple counts: 324 baseline, 601 enriched.

## Scope and remaining limitations

- The latest `cpp.owl` uses the ontology IRI `https://ilc.cnr.it/klab/ontology/cpp`, version IRI `https://ilc.cnr.it/klab/ontology/cpp/0.1.0`, and `rdfs:isDefinedBy` links under the CPP namespace; the previously reported `example.org/cpp` references are resolved.
- The enriched ABox is a functional evaluation dataset using CPP terms and P-Plan/PROV-O relations. It does not explicitly type all its instances with specialized CPP classes; a more comprehensive conformance demonstration would add such assertions and validation tests.
- Success of these SPARQL tests does not constitute an OWL 2 DL consistency check with imports resolved, nor a naturalistic linguistic evaluation.
- No license for the evaluation package is implied by the CC BY 4.0 license used in the separate CPP ontology repository. Choose a license for the benchmark before public release.

## Crime-focused regeneration — 2026-10-21

Both corpus snapshots were regenerated from the verb–crime sentence templates, with exact count checks across the 24 verb profiles (distance ≤5 / distance ≤10). The head `crime` occurs 6,936 times in Corpus A (165,477 tokens) and 6,940 times in Corpus B (165,525 tokens). The corpus cooccurrence profiles and logDice values were intentionally held numerically equal to those in the prior example; new lexical labels are not an independent linguistic evaluation. The five FrAC evaluation candidates are commit, report, investigate, prevent and solve. CPP configuration is VERB NOUN. Rebuild and test with the scripts before scientific submission.
