#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
DATA = ROOT / "data"
QUERIES = ROOT / "queries"
EXPECTED = ROOT / "expected_results"
RESULTS = ROOT / "results"
QUERY_WORKER = ROOT / "scripts" / "query_worker.py"

QUERY_FILES = [
    "q0_control_above_threshold.rq",
    "cq1_protocol_filter.rq",
    "cq2_collaborative_difference.rq",
    "cq3_cross_corpus_compatible.rq",
    "cq4_stability_across_configurations.rq",
]
PREFIXES = {
    "https://example.org/cpp-eval/": "ex:",
    "https://ilc.cnr.it/klab/ontology/cpp#": "cpp:",
    "https://ilc.cnr.it/klab/ontology/cooccurrence-measures#": "collscore:",
    "http://www.w3.org/ns/lemon/frac#": "frac:",
    "http://www.lexinfo.net/ontology/3.0/lexinfo#": "lexinfo:",
    "http://www.w3.org/ns/prov#": "prov:",
    "http://purl.org/net/p-plan#": "p-plan:",
}

FRAC = Namespace("http://www.w3.org/ns/lemon/frac#")
TOKEN_RE = re.compile(r"[A-Za-z]+")
MIN_CORPUS_TOKENS = 100_000
MIN_CORPUS_SENTENCES = 10_000
MIN_OBSERVATIONS = 35


def load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def compact(term) -> str:
    if term is None:
        return ""
    if isinstance(term, URIRef):
        value = str(term)
        for base, prefix in PREFIXES.items():
            if value.startswith(base):
                return prefix + value[len(base):]
        return value
    if isinstance(term, Literal):
        return str(term)
    return str(term)


def execute_isolated(graph_path: Path, query_path: Path):
    completed = subprocess.run(
        [sys.executable, str(QUERY_WORKER), str(graph_path), str(query_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    payload = json.loads(completed.stdout)
    return payload["headers"], payload["rows"]


def write_csv(path: Path, headers: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    return rows[0], rows[1:]


def assert_equal(actual_headers, actual_rows, expected_path: Path, label: str) -> None:
    expected_headers, expected_rows = read_csv(expected_path)
    if actual_headers != expected_headers or actual_rows != expected_rows:
        raise AssertionError(
            f"{label} does not match {expected_path.name}.\n"
            f"Expected: {expected_headers} / {expected_rows}\n"
            f"Actual:   {actual_headers} / {actual_rows}"
        )


def corpus_size(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    sentences = sum(1 for line in text.splitlines() if line.strip())
    tokens = len(TOKEN_RE.findall(text))
    return sentences, tokens


def validate_dataset_scale(baseline: Graph, enriched: Graph) -> None:
    print("Dataset scale checks")
    for corpus_name in ["corpus_a.txt", "corpus_b.txt"]:
        path = CORPUS / corpus_name
        sentences, tokens = corpus_size(path)
        if sentences < MIN_CORPUS_SENTENCES:
            raise AssertionError(
                f"{corpus_name} is too small: {sentences} sentences; "
                f"expected at least {MIN_CORPUS_SENTENCES}."
            )
        if tokens < MIN_CORPUS_TOKENS:
            raise AssertionError(
                f"{corpus_name} is too small: {tokens} tokens; "
                f"expected at least {MIN_CORPUS_TOKENS}."
            )
        print(f"  {corpus_name}: {sentences:,} sentences, {tokens:,} tokens")

    baseline_obs = set(baseline.subjects(RDF.type, FRAC.Collocation))
    enriched_obs = set(enriched.subjects(RDF.type, FRAC.Collocation))
    if baseline_obs != enriched_obs:
        raise AssertionError("Baseline and CPP graphs do not contain the same collocation observations.")
    if len(enriched_obs) < MIN_OBSERVATIONS:
        raise AssertionError(
            f"RDF dataset is too small: {len(enriched_obs)} observations; "
            f"expected at least {MIN_OBSERVATIONS}."
        )
    print(f"  RDF collocation observations: {len(enriched_obs)}")
    print()


def main() -> int:
    baseline = load_graph(DATA / "baseline_frac.ttl")
    enriched = load_graph(DATA / "cpp_enriched.ttl")
    RESULTS.mkdir(exist_ok=True)

    print(f"Loaded baseline graph: {len(baseline)} triples")
    print(f"Loaded CPP graph:      {len(enriched)} triples")
    print()

    validate_dataset_scale(baseline, enriched)

    # Run each graph/query evaluation in its own subprocess. Join-heavy CQ2 and CQ3
    # are independent and can execute concurrently; this avoids RDFLib cross-query
    # planner state and keeps the SPARQL text and RDF data unchanged.
    query_results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for query_name in QUERY_FILES:
            query_path = QUERIES / query_name
            futures[("baseline", query_name)] = pool.submit(
                execute_isolated, DATA / "baseline_frac.ttl", query_path
            )
            futures[("cpp", query_name)] = pool.submit(
                execute_isolated, DATA / "cpp_enriched.ttl", query_path
            )
        for key, future in futures.items():
            query_results[key] = future.result()

    # Control query must return exactly the same linguistic/statistical results.
    control_name = QUERY_FILES[0]
    b_headers, b_rows = query_results[("baseline", control_name)]
    c_headers, c_rows = query_results[("cpp", control_name)]
    if b_headers != c_headers or b_rows != c_rows:
        raise AssertionError("Control query differs between baseline and CPP graphs.")
    assert_equal(c_headers, c_rows, EXPECTED / "q0_control_above_threshold.csv", "Control query")
    write_csv(RESULTS / "q0_control_above_threshold.csv", c_headers, c_rows)
    print(f"PASS control: {len(c_rows)} identical observations in baseline and CPP graphs")

    # Method-aware competency questions must be unavailable as structured answers in baseline
    # and must match the expected snapshots in the CPP graph.
    for query_name in QUERY_FILES[1:]:
        b_headers, b_rows = query_results[("baseline", query_name)]
        if b_rows:
            raise AssertionError(f"Baseline unexpectedly returned rows for {query_name}: {b_rows}")

        c_headers, c_rows = query_results[("cpp", query_name)]
        expected_path = EXPECTED / query_name.replace(".rq", ".csv")
        assert_equal(c_headers, c_rows, expected_path, query_name)
        write_csv(RESULTS / query_name.replace(".rq", ".csv"), c_headers, c_rows)
        print(f"PASS {query_name}: baseline=0 rows, CPP={len(c_rows)} rows")

    print("\nAll reproducibility tests passed.")
    print(f"Actual CSV outputs were written to: {RESULTS}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TEST FAILURE: {exc}", file=sys.stderr)
        raise
