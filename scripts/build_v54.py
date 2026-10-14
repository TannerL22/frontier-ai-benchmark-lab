"""Curate the 14 October expansion without rewriting earlier releases.

Numbers are rounded publisher transcriptions reviewed in UPDATES_REVIEW.
This script performs no model calls or live scraping.
"""
from pathlib import Path
from statistics import pstdev
import csv
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/v5_4"
DATE = "2026-10-14"
AA = "https://artificialanalysis.ai/evaluations/"
NEW = [
    dict(id="B063", name="AA-3D v1.0", evaluator="AA", domain="Multimodal", family="aa-3d_v1.0", unit="elo", floor=100,
         url=AA + "aa-3d", published="2026-10-12", creator="Artificial Analysis", version="v1.0", judge="Recruited human panel",
         config="Stirrup; 55 briefs; one attempt; 250 turns; three hours; 4 CPU / 8 GB / no GPU",
         metric="Bradley-Terry preference Elo over eligible functioning scenes; not task completion rate",
         values={"Claude Opus 5.5":1190, "GPT-6 Astra":1165, "GPT-6.1 Sol":1114, "Claude Fable 5.1":1131, "Claude Sonnet 5.5":1194},
         intervals={"Claude Opus 5.5":[1155,1225], "GPT-6 Astra":[1131,1199], "GPT-6.1 Sol":[1081,1148], "Claude Fable 5.1":[1098,1165], "Claude Sonnet 5.5":[1160,1228]}, samples=55, trials=1),
    dict(id="B064", name="FrontierCode 1.1 · AA execution", evaluator="AA", domain="Coding", family="frontiercode", unit="pct", floor=5,
         url=AA + "frontiercode", published="2026-10-12", creator="Cognition", version="1.1 Main (100 of 150 tasks)", judge="GPT-6 Luna medium rubric judge",
         config="Stirrup; 100 Main tasks; three attempts; 250 turns; command timeout 7200 seconds",
         metric="Mean task rubric score across attempts; blocking failure or trajectory violation scores zero, remaining attempts score 70–100",
         values={"Claude Opus 5.5":52.2, "GPT-6 Astra":47.0, "GPT-6.1 Sol":49.1, "Claude Fable 5.1":49.0, "Claude Sonnet 5.5":45.8, "Gemini 4 Argon":42.6}, samples=100, trials=3),
    dict(id="B065", name="RareBench 0.1", evaluator="Gamow", domain="Science", family="rarebench_v0.1", unit="pct", floor=5,
         url="https://gamowlabs.com/rarebench-0-1", published="2026-08-17", creator="Gamow Labs", version="0.1 · 122 cases", judge="Published causal-recall scoring",
         config="122 rare-disease cases; vendor agent harnesses; Argon EAP / Antigravity Science",
         metric="Rank@K complete causal recall, K equals required causal findings; invalid outputs fail; published rounded percentages",
         values={"Claude Opus 5.5":51.6, "GPT-6.1 Sol":32.0, "Claude Fable 5.1":40.2, "Claude Sonnet 5.5":40.2, "Gemini 4 Argon":57.4, "Muse Wonder":18.9}, samples=122, trials="unknown"),
    dict(id="B066", name="LabBench · wet-lab decisions", evaluator="Gamow", domain="Science", family="labbench", unit="pct", floor=5,
         url="https://gamowlabs.com/labbench-benchmarking-ai-wet-lab-decisions", published="2026-09-28", creator="Gamow Labs", version="20 held-out tasks", judge="Human-reviewed binary rubric criteria",
         config="20 held-out wet-lab tasks; one attempt; vendor agent harnesses; Argon EAP / Antigravity",
         metric="Mean fraction of 20–22 binary rubric criteria passed per task; not percentage of tasks solved",
         values={"Claude Opus 5.5":40.5, "GPT-6 Astra":40.8, "Gemini 4 Argon":52.2}, samples=20, trials=1),
]


def read_csv(name):
    with (TARGET / name).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(name, fields, rows):
    with (TARGET / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    if TARGET.exists():
        raise ValueError("v5.4 already exists; review changes explicitly rather than overwrite it")
    shutil.copytree(ROOT / "data/v5_3", TARGET)
    collections = {name:read_csv(name) for name in ("benchmarks.csv", "scores.csv", "systems.csv", "missingness.csv", "normalization_reference.csv")}
    identities = read_csv("model_identities.csv")[1]
    names = {r["model_name"]:r["model_id"] for r in identities}
    sources = [json.loads(x) for x in (TARGET / "sources.jsonl").read_text().splitlines()]
    observations = [json.loads(x) for x in (TARGET / "observations.jsonl").read_text().splitlines()]
    for item in NEW:
        bid = item["id"]
        meta = dict.fromkeys(collections["benchmarks.csv"][0], "")
        meta.update(benchmark_id=bid, benchmark_name=item["name"], evaluator=item["evaluator"], domain=item["domain"], family_id=item["family"],
                    unit=item["unit"], configuration=item["config"], scale_floor=item["floor"], source_url=item["url"],
                    provenance="Dated publisher transcription on 14 Oct 2026; exact provider snapshot and original run IDs remain unknown",
                    included="1", overlap_notes="Same Main task family as Cognition B036; split family weight between executions" if bid == "B064" else "Distinct family; task-level independence from the wider portfolio has not been certified",
                    direction="higher", genealogy_id=item["family"], genealogy_note="FrontierCode shared task ancestry" if bid == "B064" else "No broader relationship reviewed",
                    metric_definition=item["metric"], quality_status="recorded_with_limitations", benchmark_creator=item["creator"],
                    execution_operator=item["evaluator"], publishing_organisation=item["evaluator"], task_set_version=item["version"], judge_version=item["judge"])
        collections["benchmarks.csv"][1].append(meta)
        reference_values = [v for n,v in item["values"].items() if n not in ("Muse Wonder", "Muse Wonder Full")]
        denominator = max(item["floor"], pstdev(reference_values))
        collections["normalization_reference.csv"][1].append(dict(benchmark_id=bid, denominator=denominator, reference_release="v5.4 new-row fixed reference",
            reference_rule="max(floor, population SD of recorded original six-model identities); frozen at first inclusion; absent scores omitted"))
        for name,mid in names.items():
            if name not in item["values"]:
                collections["missingness.csv"][1].append(dict(benchmark_id=bid, model_id=mid, reason="not_listed_in_reviewed_scoreboard", qualification="No substitution from a different model identity; no score inferred"))
                continue
            score = item["values"][name]
            stem = bid.lower() + "-" + mid
            sid, source_id = "system-" + stem, "source-" + stem
            eap = item["evaluator"] == "Gamow" and name == "Gemini 4 Argon"
            status = "provisional_numeric_corroborated" if eap else "numeric_corroborated"
            collections["scores.csv"][1].append(dict(benchmark_id=bid, model_name=name, score=score, verified_source_url=item["url"], evidence_status=status))
            system = dict.fromkeys(collections["systems.csv"][0], "unknown")
            harness = "Stirrup" if item["evaluator"] == "AA" else ("Antigravity · Science" if eap and bid == "B065" else "Antigravity" if eap else "Codex" if name.startswith("GPT") else "Muse Code" if name.startswith("Muse") else "Claude Code")
            system.update(system_id=sid, model_id=mid, benchmark_id=bid, model_snapshot="EAP; exact snapshot unknown" if eap else "unknown", reasoning_effort=("high" if name == "Gemini 4 Argon" else "max") if item["evaluator"] == "AA" else "unknown",
                          harness=harness, fallback_policy="Default Fallback; exact policy unknown" if item["evaluator"] == "AA" and name.startswith("Claude") else "unknown",
                          resource_budget=item["config"], configuration_status="EAP" if eap else "partially_documented", reported_configuration=item["config"],
                          retry_policy=str(item["trials"]) + " attempt(s)", source_review_id="updates_review_2026_10_14", publisher_profile_defaults="{}", profile_defaults_scope="No unreported settings inferred")
            collections["systems.csv"][1].append(system)
            values = dict(benchmark_id=bid, model_name=name, score=score)
            source = dict(source_id=source_id, url=item["url"], corroboration_urls=["https://gamowlabs.com/benchmarks"] if item["evaluator"] == "Gamow" else [],
                          capture_type="auditor_transcription", observed_on=DATE, publication_date=item["published"], transcribed_values=values,
                          transcription_sha256=hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest(), original_html_sha256="not_captured",
                          qualification="Curated published rounded scoreboard transcription; not original HTML or equal-compute certification",
                          observation_locator=item["name"] + " > " + name, source_review_id="updates_review_2026_10_14")
            sources.append(source)
            interval = item.get("intervals", {}).get(name)
            uncertainty = dict(type="publisher_95_percent_elo_interval" if interval else "not_captured", value=interval,
                               qualification="Publisher sandwich interval on preference Elo; not uncertainty on our ranking" if interval else "No numeric task-level interval captured; RareBench displays Wilson whiskers")
            observations.append(dict(observation_id="observation-" + stem, benchmark_id=bid, model_id=mid, system_id=sid, source_id=source_id,
                score=score, evidence_status=status, included=True, inclusion_reason="Versioned portfolio expansion; EAP results retain provisional status" if eap else "Versioned portfolio expansion from reviewed publisher scoreboard",
                sample_count=item["samples"], trial_count=item["trials"], judge_version=item["judge"], original_run_id="unknown", uncertainty=uncertainty, source_review_id="updates_review_2026_10_14"))
    for filename,(fields,rows) in collections.items():
        write_csv(filename, fields, rows)
    for filename,records in (("sources.jsonl",sources),("observations.jsonl",observations)):
        (TARGET / filename).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    fields, registry = read_csv("models.csv")
    for row in registry:
        if row["model_name"] == "Gemini 4 Argon":
            row.update(released_on="2026-10-13", api_access="Public paid Gemini API / AI Studio; enterprise and supported consumer subscriptions", source_url="https://ai.google.dev/gemini-api/docs/models/gemini-4-argon")
    write_csv("models.csv", fields, registry)
    for row in identities:
        if row["model_name"] == "Gemini 4 Argon":
            row.update(released_on="2026-10-13", identity_qualification="Public availability 13 Oct; earlier EAP benchmark snapshots are not certified as the public endpoint")
    write_csv("model_identities.csv", read_csv("model_identities.csv")[0], identities)
    config = json.loads((TARGET / "config.json").read_text())
    config.update(version="v5.4-frontier-expansion-2026-10-14", as_of=DATE, evidence_cutoff=DATE, release_status="curated_expansion", expected_counts=dict(models=8, benchmarks=61, scores=326),
                  note="Four additional executions, three new families; Argon science EAP runs remain provisional. Earlier release and forecast inputs remain frozen.")
    (TARGET / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    release = dict(id="v5.4", status="curated_expansion", created_on=DATE, evidence_cutoff=DATE, included_observations=326, new_observations=20, new_families=3,
        scope="Selected reported systems across 61 evaluation rows / 59 families / 10 evaluator labels", exact_run_metadata="incomplete", independent_human_review="pending owner task/eligibility review",
        frozen_forecast_inputs="data/v5_2 unchanged", aa_composites="AA-3D and FrontierCode are not constituents of AA Intelligence Index v4.3.2 or Coding Agent Index v1.5 as reviewed on 14 Oct",
        added_benchmarks=[i["id"] for i in NEW])
    (TARGET / "release.json").write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    decisions = json.loads((TARGET / "decisions.json").read_text())
    for ident,decision,basis in [
        ("D054", "Add four executions, preserve shared FrontierCode family", "AA-3D, AA FrontierCode 1.1, RareBench and LabBench primary scoreboards; reviewed 14 Oct"),
        ("D055", "Retain Argon EAP labels for Gamow runs", "Public availability does not certify earlier EAP run equivalence"),
        ("D056", "Freeze new normalizers at first inclusion", "Original six-model recorded subset, max(scale floor, population SD); all earlier denominators unchanged"),
        ("D057", "Keep retrospective additions outside future study", "Publication dates precede public forecast registration"),
    ]:
        decisions.append(dict(id=ident, date=DATE, decision=decision, basis=basis, review_status="Maintainer curation; no independent run certification"))
    (TARGET / "decisions.json").write_text(json.dumps(decisions, indent=2) + "\n", encoding="utf-8")
    print("Prepared v5.4: 61 evaluation rows, 59 families, 326 observations")


if __name__ == "__main__":
    main()
