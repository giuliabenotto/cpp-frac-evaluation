#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
DATA_DIR = ROOT / "data"

CORPUS_COLLOCATES = [
    "commit", "report", "examine", "identify", "trace", "detect",
    "witness", "prosecute", "punish", "conceal", "organise", "plan",
    "admit", "investigate", "expose", "prevent", "combat", "reduce",
    "record", "discuss", "analyse", "solve", "mention", "classify",
]

# Five controlled verb-noun candidates represented as FrAC observations.
EVAL_COLLOCATES = ["commit", "report", "investigate", "prevent", "solve"]

# close = co-occurrences within five tokens of crime; extra = co-occurrences
# at distance six to ten. Profiles are held constant for reproducibility.
PROFILE = {
    "A": {
        "close": [180,145,120,110,95,82,70,65,58,52,48,42,38,34,30,26,22,18,15,13,11,9,6,4],
        "extra": [70,60,50,48,45,40,36,34,30,28,26,24,22,20,18,17,15,14,12,10,9,7,5,3],
    },
    "B": {
        "close": [165,160,100,118,110,75,62,72,54,60,41,46,45,28,35,20,25,17,18,11,14,8,9,5],
        "extra": [65,72,42,52,50,36,32,39,28,30,22,25,24,16,20,14,16,11,13,8,10,6,7,4],
    },
}

STANDALONE_VERB = 320
STANDALONE_CRIME = 5000
FILLER_SENTENCES = 3000

CLOSE_TEMPLATES = [
    "Investigators were instructed to {adj} a crime under the new protocol.",
    "The official guidelines explain how to {adj} a crime in this district.",
    "The trained officers expect to {adj} a crime during the current operation.",
    "The team discussed when to {adj} a crime within the reporting period.",
    "The manual describes the steps needed to {adj} a crime correctly.",
]

# Target distance: nine tokens (all within sentence boundaries).
DISTANT_TEMPLATES = [
    "Investigators decided to {adj} the case after carefully considering details of the crime.",
    "The officers agreed to {adj} the evidence after reviewing several aspects of the crime.",
    "The committee planned to {adj} the file after analysing multiple accounts of the crime.",
    "The analysts chose to {adj} the matter after examining available details of the crime.",
]

VERB_ONLY_TEMPLATES = [
    "Investigators agreed to {adj} the matter during the afternoon.",
    "The local officers decided to {adj} the evidence after the briefing.",
    "The team was instructed to {adj} the case without further discussion.",
    "The committee expects to {adj} the memorandum before the final meeting.",
]

CRIME_ONLY_TEMPLATES = [
    "The crime was recorded in the official register.",
    "A crime was mentioned during the public hearing.",
    "The crime remained under investigation for several months.",
    "The local archive contained a summary of the crime.",
    "The crime attracted attention from several organisations.",
]

FILLER_TEMPLATES = [
    "The archive was updated during the afternoon.",
    "Several officers attended the scheduled briefing.",
    "The committee reviewed its internal procedures.",
    "A public bulletin was published after the meeting.",
    "The records were stored in the regional database.",
    "The training session ended shortly before noon.",
]

TOKEN_RE = re.compile(r"[A-Za-z]+")


def tokenise(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def render(template: str, adj: str) -> str:
    return template.format(adj=adj, Adj=adj.capitalize())


def build_corpus(label: str) -> tuple[str, dict]:
    profile = PROFILE[label]
    lines: list[str] = []

    for idx, adj in enumerate(CORPUS_COLLOCATES):
        close = profile["close"][idx]
        extra = profile["extra"][idx]
        for i in range(close):
            lines.append(render(CLOSE_TEMPLATES[(i + idx) % len(CLOSE_TEMPLATES)], adj))
        for i in range(extra):
            lines.append(render(DISTANT_TEMPLATES[(i + idx) % len(DISTANT_TEMPLATES)], adj))
        for i in range(STANDALONE_VERB):
            lines.append(render(VERB_ONLY_TEMPLATES[(i + idx) % len(VERB_ONLY_TEMPLATES)], adj))

    for i in range(STANDALONE_CRIME):
        lines.append(CRIME_ONLY_TEMPLATES[i % len(CRIME_ONLY_TEMPLATES)])
    for i in range(FILLER_SENTENCES):
        lines.append(FILLER_TEMPLATES[i % len(FILLER_TEMPLATES)])

    # Deterministic interleaving prevents the corpus from being grouped by collocate
    # without introducing randomness that could complicate exact regeneration.
    n = len(lines)
    step = 7919
    while math.gcd(step, n) != 1:
        step += 2
    permuted = [lines[(i * step) % n] for i in range(n)]
    text = "\n".join(permuted) + "\n"

    stats = analyse_corpus(text)
    return text, stats


def analyse_corpus(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.strip()]
    tokenised = [tokenise(line) for line in lines]
    all_tokens = [tok for sent in tokenised for tok in sent]

    crime_count = sum(tok == "crime" for tok in all_tokens)
    collocate_stats = {}
    for adj in CORPUS_COLLOCATES:
        total_adj = sum(tok == adj for tok in all_tokens)
        within5 = 0
        within10 = 0
        for sent in tokenised:
            crime_positions = [i for i, tok in enumerate(sent) if tok == "crime"]
            adj_positions = [i for i, tok in enumerate(sent) if tok == adj]
            for r in crime_positions:
                for a in adj_positions:
                    dist = abs(r - a)
                    if 0 < dist <= 5:
                        within5 += 1
                    if 0 < dist <= 10:
                        within10 += 1
        collocate_stats[adj] = {
            "frequency": total_adj,
            "within5": within5,
            "within10": within10,
        }

    return {
        "sentences": len(lines),
        "tokens": len(all_tokens),
        "crime": crime_count,
        "collocates": collocate_stats,
    }


def logdice(fxy: int, fx: int, fy: int) -> float:
    return 14.0 + math.log2((2.0 * fxy) / (fx + fy))


def score_table(stats: dict) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for adj in CORPUS_COLLOCATES:
        fx = stats["collocates"][adj]["frequency"]
        fy = stats["crime"]
        out[adj] = {
            5: round(logdice(stats["collocates"][adj]["within5"], fx, fy), 2),
            10: round(logdice(stats["collocates"][adj]["within10"], fx, fy), 2),
        }
    return out


def qname(value: str) -> str:
    return value.replace("-", "_")


def turtle_prefixes(include_cpp: bool = False) -> str:
    base = """@prefix : <https://example.org/cpp-eval/> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix frac: <http://www.w3.org/ns/lemon/frac#> .
@prefix lexinfo: <http://www.lexinfo.net/ontology/3.0/lexinfo#> .
@prefix collscore: <https://ilc.cnr.it/klab/ontology/cooccurrence-measures#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""
    if include_cpp:
        base += "@prefix cpp: <https://ilc.cnr.it/klab/ontology/cpp#> .\n@prefix p-plan: <http://purl.org/net/p-plan#> .\n"
    return base


RUNS = [
    # id, corpus, software, analyst, window, minimum frequency, record right window?
    ("r1", "A", "Extractor_v1", "Lexicographer_A", 5, 3, True),
    ("r2", "A", "Extractor_v1", "Lexicographer_B", 10, 3, True),
    ("r3", "B", "Extractor_v1", "Lexicographer_A", 5, 3, True),
    ("r4", "B", "Extractor_v1", "Lexicographer_B", 10, 3, True),
    ("r5", "A", "Extractor_v1", "Lexicographer_C", 5, 10, True),
    ("r6", "B", "Extractor_v2", "Lexicographer_A", 5, 3, True),
    ("r7", "A", "Extractor_v1", "Lexicographer_B", 5, 3, False),
    ("r8", "B", "Extractor_v1", "Lexicographer_C", 5, 10, True),
]


def observations_for_run(run, stats_by_corpus, scores_by_corpus):
    run_id, corpus, software, analyst, window, minimum_frequency, right_recorded = run
    result = []
    for adj in EVAL_COLLOCATES:
        freq_key = "within5" if window == 5 else "within10"
        cooc = stats_by_corpus[corpus]["collocates"][adj][freq_key]
        if cooc < minimum_frequency:
            continue
        result.append({
            "run": run_id,
            "corpus": corpus,
            "software": software,
            "analyst": analyst,
            "window": window,
            "minimum_frequency": minimum_frequency,
            "right_recorded": right_recorded,
            "collocate": adj,
            "score": scores_by_corpus[corpus][adj][window],
        })
    return result


def description_for(run) -> str:
    run_id, corpus, software, analyst, window, minimum_frequency, right_recorded = run
    if right_recorded:
        window_text = f"Symmetric {window}-token window"
    else:
        window_text = f"Left window {window}; right window not recorded"
    software_label = software.replace("Extractor_", "Extractor ").replace("_", " ")
    return (
        f"{window_text}; sentence-bounded; unordered; minimum frequency {minimum_frequency}; "
        f"POS pattern VERB NOUN; logDice; {software_label}."
    )


def write_common_entities(handle, stats_by_corpus):
    handle.write(':crime a frac:Observable ; rdfs:label "crime"@en .\n')
    for adj in CORPUS_COLLOCATES:
        handle.write(f':{qname(adj)} a frac:Observable ; rdfs:label "{adj}"@en .\n')
    handle.write("\n")
    for label in ["A", "B"]:
        stats = stats_by_corpus[label]
        handle.write(
            f':Corpus_{label} a prov:Entity ; rdfs:label "English synthetic corpus snapshot {label}"@en ; '
            f'prov:atLocation "corpus/corpus_{label.lower()}.txt" ; '
            f'dct:description "Deterministically generated evaluation corpus with {stats["sentences"]} sentences and {stats["tokens"]} word tokens."@en .\n'
        )
    handle.write("\n")


def write_observations(handle, observations, run_lookup):
    for run in RUNS:
        run_id = run[0]
        run_obs = [o for o in observations if o["run"] == run_id]
        handle.write(f"# Run {run_id} -- {description_for(run)}\n")
        desc = description_for(run)
        for obs in run_obs:
            adj = qname(obs["collocate"])
            score = f'{obs["score"]:.2f}'
            handle.write(
                f':obs_{run_id}_{adj} a frac:Collocation ;\n'
                f'    frac:head :crime ; rdfs:member :crime, :{adj} ; frac:observedIn :Corpus_{obs["corpus"]} ;\n'
                f'    collscore:logDice "{score}"^^xsd:decimal ;\n'
                f'    dct:description "{desc}"@en .\n'
            )
        handle.write("\n")


def write_baseline(path: Path, observations, stats_by_corpus):
    with path.open("w", encoding="utf-8") as handle:
        handle.write(turtle_prefixes(False) + "\n")
        write_common_entities(handle, stats_by_corpus)
        write_observations(handle, observations, {r[0]: r for r in RUNS})


def write_enriched(path: Path, observations, stats_by_corpus):
    with path.open("w", encoding="utf-8") as handle:
        handle.write(turtle_prefixes(True) + "\n")
        write_common_entities(handle, stats_by_corpus)
        write_observations(handle, observations, {r[0]: r for r in RUNS})

        handle.write("# CPP plan and shared variables\n")
        handle.write("cpp:collocationExtractionPlan a p-plan:Plan .\n")
        handle.write(
            "cpp:extractCollocations a p-plan:Step ;\n"
            "    p-plan:isStepOfPlan cpp:collocationExtractionPlan ;\n"
            "    p-plan:hasInputVar cpp:corpus, cpp:index, cpp:windowLeft, cpp:windowRight,\n"
            "        cpp:sentenceBoundary, cpp:ordered, cpp:minimumFrequency, cpp:posPattern, cpp:measures ;\n"
            "    p-plan:hasOutputVar cpp:collocationObservation .\n\n"
        )
        variables = [
            ("corpus", "corpus"), ("index", "index"), ("windowLeft", "left context window"),
            ("windowRight", "right context window"), ("sentenceBoundary", "sentence boundary"),
            ("ordered", "ordered co-occurrence"), ("minimumFrequency", "minimum co-occurrence frequency"),
            ("posPattern", "part-of-speech pattern"), ("measures", "association measures"),
            ("collocationObservation", "collocation observation"),
        ]
        for var, label in variables:
            handle.write(f'cpp:{var} a p-plan:Variable ; rdfs:label "{label}"@en .\n')

        handle.write("\n# Corpus and index bindings\n")
        for label in ["A", "B"]:
            handle.write(f':Corpus_{label} a p-plan:Entity ; p-plan:correspondsToVariable cpp:corpus .\n')
            handle.write(
                f':Index_{label} a p-plan:Entity, prov:Entity ; p-plan:correspondsToVariable cpp:index ; '
                f'prov:wasDerivedFrom :Corpus_{label} ; rdfs:label "Index built from Corpus {label}"@en .\n'
            )

        handle.write("\n# Software and human agents\n")
        handle.write(':Extractor_v1 a prov:SoftwareAgent ; rdfs:label "Collocation Extractor v1"@en .\n')
        handle.write(':Extractor_v2 a prov:SoftwareAgent ; rdfs:label "Collocation Extractor v2"@en .\n')
        handle.write(':Lexicographer_A a prov:Person ; rdfs:label "Lexicographer A"@en .\n')
        handle.write(':Lexicographer_B a prov:Person ; rdfs:label "Lexicographer B"@en .\n')
        handle.write(':Lexicographer_C a prov:Person ; rdfs:label "Lexicographer C"@en .\n')

        handle.write("\n# Shared parameter entities\n")
        handle.write(':windowLeft_5 a p-plan:Entity ; p-plan:correspondsToVariable cpp:windowLeft ; prov:value "5"^^xsd:integer .\n')
        handle.write(':windowRight_5 a p-plan:Entity ; p-plan:correspondsToVariable cpp:windowRight ; prov:value "5"^^xsd:integer .\n')
        handle.write(':windowLeft_10 a p-plan:Entity ; p-plan:correspondsToVariable cpp:windowLeft ; prov:value "10"^^xsd:integer .\n')
        handle.write(':windowRight_10 a p-plan:Entity ; p-plan:correspondsToVariable cpp:windowRight ; prov:value "10"^^xsd:integer .\n')
        handle.write(':sentenceBoundary_true a p-plan:Entity ; p-plan:correspondsToVariable cpp:sentenceBoundary ; prov:value true .\n')
        handle.write(':ordered_false a p-plan:Entity ; p-plan:correspondsToVariable cpp:ordered ; prov:value false .\n')
        handle.write(':minimumFrequency_3 a p-plan:Entity ; p-plan:correspondsToVariable cpp:minimumFrequency ; prov:value "3"^^xsd:integer .\n')
        handle.write(':minimumFrequency_10 a p-plan:Entity ; p-plan:correspondsToVariable cpp:minimumFrequency ; prov:value "10"^^xsd:integer .\n')
        handle.write(':posPattern_VERB_NOUN a p-plan:Entity, rdf:Seq ; p-plan:correspondsToVariable cpp:posPattern ; rdf:_1 lexinfo:verb ; rdf:_2 lexinfo:noun .\n')
        handle.write(':measure_logDice a p-plan:Entity, rdf:Bag ; p-plan:correspondsToVariable cpp:measures ; rdfs:member collscore:LogDice .\n')

        handle.write("\n# Runs\n")
        for run in RUNS:
            run_id, corpus, software, analyst, window, minfreq, right_recorded = run
            used = [
                f':Corpus_{corpus}', f':Index_{corpus}', f':windowLeft_{window}',
            ]
            if right_recorded:
                used.append(f':windowRight_{window}')
            used.extend([
                ':sentenceBoundary_true', ':ordered_false', f':minimumFrequency_{minfreq}',
                ':posPattern_VERB_NOUN', ':measure_logDice',
            ])
            obs_ids = [
                f':obs_{run_id}_{qname(o["collocate"])}'
                for o in observations if o["run"] == run_id
            ]
            handle.write(f':{run_id} a p-plan:Activity, prov:Activity ; p-plan:correspondsToStep cpp:extractCollocations ;\n')
            handle.write(f'    prov:used {", ".join(used)} ;\n')
            handle.write(f'    prov:wasAssociatedWith :{software}, :{analyst} ;\n')
            handle.write(f'    prov:generated {", ".join(obs_ids)} .\n')

        handle.write("\n# Link each observation to the run that generated it\n")
        for obs in observations:
            handle.write(f':obs_{obs["run"]}_{qname(obs["collocate"])} prov:wasGeneratedBy :{obs["run"]} .\n')


def write_stats(stats_by_corpus, scores_by_corpus):
    with (CORPUS_DIR / "corpus_statistics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["corpus", "sentences", "tokens", "crime_tokens"])
        for label in ["A", "B"]:
            s = stats_by_corpus[label]
            writer.writerow([f"Corpus_{label}", s["sentences"], s["tokens"], s["crime"]])

    with (CORPUS_DIR / "collocate_statistics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "collocate",
            "A_frequency", "A_within5", "A_within10", "A_logDice5", "A_logDice10",
            "B_frequency", "B_within5", "B_within10", "B_logDice5", "B_logDice10",
        ])
        for adj in CORPUS_COLLOCATES:
            a = stats_by_corpus["A"]["collocates"][adj]
            b = stats_by_corpus["B"]["collocates"][adj]
            writer.writerow([
                adj,
                a["frequency"], a["within5"], a["within10"], f'{scores_by_corpus["A"][adj][5]:.2f}', f'{scores_by_corpus["A"][adj][10]:.2f}',
                b["frequency"], b["within5"], b["within10"], f'{scores_by_corpus["B"][adj][5]:.2f}', f'{scores_by_corpus["B"][adj][10]:.2f}',
            ])


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    stats_by_corpus = {}
    for label in ["A", "B"]:
        text, stats = build_corpus(label)
        (CORPUS_DIR / f"corpus_{label.lower()}.txt").write_text(text, encoding="utf-8")
        stats_by_corpus[label] = stats

        # Exact design checks: the generated text must realise the requested counts.
        for idx, adj in enumerate(CORPUS_COLLOCATES):
            assert stats["collocates"][adj]["within5"] == PROFILE[label]["close"][idx]
            assert stats["collocates"][adj]["within10"] == PROFILE[label]["close"][idx] + PROFILE[label]["extra"][idx]
            assert stats["collocates"][adj]["frequency"] == PROFILE[label]["close"][idx] + PROFILE[label]["extra"][idx] + STANDALONE_VERB

    scores_by_corpus = {label: score_table(stats) for label, stats in stats_by_corpus.items()}

    observations = []
    for run in RUNS:
        observations.extend(observations_for_run(run, stats_by_corpus, scores_by_corpus))

    write_stats(stats_by_corpus, scores_by_corpus)
    write_baseline(DATA_DIR / "baseline_frac.ttl", observations, stats_by_corpus)
    write_enriched(DATA_DIR / "cpp_enriched.ttl", observations, stats_by_corpus)

    print("Generated corpus and RDF evaluation data")
    for label in ["A", "B"]:
        s = stats_by_corpus[label]
        print(f"Corpus {label}: {s['sentences']} sentences, {s['tokens']} tokens, {s['crime']} crime tokens")
    print(f"Controlled corpus collocates: {len(CORPUS_COLLOCATES)}")
    print(f"RDF evaluation collocates: {len(EVAL_COLLOCATES)}")
    print(f"Observations across {len(RUNS)} runs: {len(observations)}")


if __name__ == "__main__":
    main()
