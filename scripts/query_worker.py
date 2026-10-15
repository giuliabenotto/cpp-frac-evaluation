#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Graph, Literal, URIRef

PREFIXES = {
    "https://example.org/cpp-eval/": "ex:",
    "https://ilc.cnr.it/klab/ontology/cpp#": "cpp:",
    "https://ilc.cnr.it/klab/ontology/cooccurrence-measures#": "collscore:",
    "http://www.w3.org/ns/lemon/frac#": "frac:",
    "http://www.lexinfo.net/ontology/3.0/lexinfo#": "lexinfo:",
    "http://www.w3.org/ns/prov#": "prov:",
    "http://purl.org/net/p-plan#": "p-plan:",
}


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


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: query_worker.py GRAPH.ttl QUERY.rq")

    graph_path = Path(sys.argv[1])
    query_path = Path(sys.argv[2])

    graph = Graph()
    graph.parse(graph_path, format="turtle")
    result = graph.query(query_path.read_text(encoding="utf-8"))

    payload = {
        "headers": [str(v) for v in result.vars],
        "rows": [[compact(value) for value in row] for row in result],
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
