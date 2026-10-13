"""Extract factual score records from captured primary-source reader/table views.

Captures stay outside the repository; only curated numeric records and digests
are published. Reader output is not original HTML or a verified original run.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MODELS = {"vals_opus": "claude-opus-5-5", "vals_astra": "gpt-6-astra", "vals_sol": "gpt-6-1-sol",
          "vals_fable": "claude-fable-5-1", "vals_sonnet": "claude-sonnet-5-5", "vals_argon": "gemini-4-argon"}
VALS = {"B016": "Code Migration", "B017": "CyberBench v1.1", "B018": "EMB", "B019": "Finance Agent (v2)",
        "B020": "Legal Research Bench", "B021": "MedCode", "B022": "MedScribe", "B023": "MysteryMechanism",
        "B024": "ProofBench v1.1", "B025": "SAGE", "B026": "SRE Bench", "B027": "Tax Agent Bench",
        "B028": "Vibe Code Bench v1.1", "B029": "Harvey's Legal Agent Benchmark", "B030": "ProgramBench",
        "B031": "Terminal-Bench Science", "B051": "IOI", "B052": "Public Benefits Bench v1.1",
        "B053": "CUA-bench", "B054": "Time Horizon Index: KSP"}
AA = {name: f"B{i:03}" for i, name in enumerate([
    "AA-Briefcase v1.1", "GDPval-AA v2.1", "AutomationBench-AA", "Terminal-Bench 4.0", "SciCode",
    "Humanity's Last Exam", "GDP.pdf", "CritPt", "AA-Omniscience", "AA-LCR v1.1"], 6)}


def reader_lines(text):
    text = re.sub(r"L\d+: ?", "\n", text)
    text = re.sub(r"cite[^†]+†([^]+)", lambda m: m[1].split("†")[0], text)
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_vals(text):
    lines = reader_lines(text)
    results = {}
    start = next(i for i, line in enumerate(lines) if line == "Benchmarks Accuracy Rankings")
    for bid, label in VALS.items():
        matches = [i for i, line in enumerate(lines) if i > start and line == label and i + 1 < len(lines)
                   and re.fullmatch(r"\d+(?:\.\d+)?%", lines[i + 1])]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous profile metric: {label}")
        if not matches:
            continue
        ix = matches[0]
        interval = float(lines[ix + 2][1:]) if ix + 2 < len(lines) and re.fullmatch(r"±\d+(?:\.\d+)?", lines[ix + 2]) else None
        results[bid] = {"score": float(lines[ix + 1][:-1]), "reported_plus_minus": interval,
                        "locator": label + " > Accuracy", "uncertainty_interpretation": "source-reported plus/minus; see methodology, never treated as paired uncertainty"}
    defaults = {}
    for label in ("Default Provider", "Temperature", "Max Output Tokens", "Reasoning Effort", "Compute Effort"):
        for line in lines:
            if line.startswith(label) and ":" in line:
                defaults[label] = line.split(":", 1)[1].strip()
    for label in ("Fallback Rate", "Refusal Rate"):
        matches = [line for line in lines if line.startswith(label)]
        if matches:
            defaults[label] = matches[0][len(label):].strip()
    return results, defaults


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reviews/source_review_2026_10_13.json")
    args = parser.parse_args()
    observations = [json.loads(line) for line in (ROOT / "data/v5_2/observations.jsonl").read_text().splitlines()]
    original = {(o["benchmark_id"], o["model_id"]): o for o in observations if o["included"]}
    records, sources = {}, []
    def source(path, url, capture_type, captured_at=None):
        sid = path.stem
        item = {"source_id": sid, "url": url, "capture_type": capture_type,
                "retrieved_at": captured_at or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "local_capture_filename": path.name,
                "artifact_scope": "Captured reader/visible table representation; not original webpage bytes; full reader capture retained locally"}
        sources.append(item)
        return sid
    def add(bid, mid, value, sid):
        if (bid, mid) not in original:
            return
        old = original[bid, mid]
        records[bid, mid] = {"benchmark_id": bid, "model_id": mid, "observation_id": old["observation_id"],
                            "stored_score": old["score"], **value, "source_id": sid,
                            "result": "number_matches" if old["score"] == value["score"] else "current_source_differs",
                            "qualification": "Numeric source corroboration; exact endpoint/run identity and equal budgets remain unestablished"}
    for filename, mid in MODELS.items():
        path = args.captures / (filename + ".txt")
        text = path.read_text(encoding="utf-8")
        url = text.splitlines()[0].rsplit("(", 1)[1][:-1]
        sid = source(path, url, "web_reader_capture")
        values, defaults = parse_vals(text)
        sources[-1]["reported_profile_defaults"] = defaults
        sources[-1]["defaults_qualification"] = "Profile defaults do not certify the conditions of every benchmark run"
        for bid, value in values.items():
            add(bid, mid, value, sid)
    for name in ("aa_five", "aa_argon"):
        path = args.captures / (name + ".json")
        capture = json.loads(path.read_text())
        sid = source(path, capture["url"], "browser_visible_table", capture["captured_at"])
        header = capture["rows"][0]
        mids = []
        for cell in header[1:]:
            display = {"Claude Opus 5.5": "claude-opus-5-5", "GPT-6 Astra": "gpt-6-astra", "GPT-6.1 Sol": "gpt-6-1-sol",
                       "Claude Fable 5.1": "claude-fable-5-1", "Claude Sonnet 5.5": "claude-sonnet-5-5", "Gemini 4 Argon": "gemini-4-argon"}
            mids.append(next(mid for name, mid in display.items() if name in cell))
        sources[-1]["reported_configurations"] = header[1:]
        for row in capture["rows"][1:]:
            if row[0] not in AA:
                continue
            for mid, value in zip(mids, row[1:]):
                add(AA[row[0]], mid, {"score": float(value.rstrip("%")), "locator": row[0] + " > " + mid,
                                     "reported_plus_minus": None, "uncertainty_interpretation": "not captured"}, sid)
    epoch = {"B042": "Earthborne Rangers (EBR-bench)", "B043": "Mystery Game Puzzles",
             "B044": "FrontierMath Tiers 1-3 (v2)", "B045": "FrontierMath Tier 4 (v2)",
             "B046": "Furniture Assembly Benchmark", "B047": "GPQA Diamond", "B049": "SimpleQA Verified"}
    for filename, name, mid in (("epoch_fable", "Claude Fable 5.1", "claude-fable-5-1"),
                                 ("epoch_sonnet", "Claude Sonnet 5.5", "claude-sonnet-5-5")):
        path = args.captures / (filename + ".txt")
        text = path.read_text(encoding="utf-8")
        sid = source(path, text.splitlines()[0].rsplit("(", 1)[1][:-1], "web_reader_capture")
        lines = reader_lines(text)
        header = next(line for line in lines if line.startswith("Domain") and "| Benchmark" in line)
        if name not in header.split("|")[2]:
            raise ValueError("Epoch target model is not the expected score column")
        for bid, label in epoch.items():
            candidates = [line for line in lines if "|" in line and (label + " Best score") in line]
            if len(candidates) > 1:
                raise ValueError("Ambiguous Epoch metric")
            if candidates:
                score = candidates[0].split("|")[2].strip()
                if re.fullmatch(r"\d+(?:\.\d+)?%", score):
                    add(bid, mid, {"score": float(score[:-1]), "locator": label + " > " + name + " score column",
                                   "reported_plus_minus": None, "uncertainty_interpretation": "not captured"}, sid)
    arena_path = args.captures / "arena_text.txt"
    arena_text = arena_path.read_text(encoding="utf-8")
    arena_sid = source(arena_path, "https://arena.ai/leaderboard/chat/text?scoring=raw", "web_reader_capture")
    arena_lines = reader_lines(arena_text)
    arena_candidates = [line for line in arena_lines if "gpt-6-astra-max" in line and "|" in line]
    if len(arena_candidates) == 1:
        fields = arena_candidates[0].split("|")
        value = re.match(r"(\d+)(?:±(\d+))?", fields[3].strip())
        if value:
            old = original["B062", "gpt-6-astra"]
            records["B062", "gpt-6-astra"] = {"benchmark_id": "B062", "model_id": "gpt-6-astra",
                "observation_id": old["observation_id"], "stored_score": old["score"], "score": float(value[1]),
                "source_id": arena_sid, "locator": "Text Arena overall > gpt-6-astra-max > score",
                "result": "different_dated_population", "source_population_date": "2026-10-13",
                "stored_population_date": "2026-10-08", "reported_plus_minus": float(value[2]) if value[2] else None,
                "qualification": "The current dated leaderboard cannot corroborate the Oct 8 snapshot; retain the historical uncertainty rather than substitute another population"}
    inherited = {(o["benchmark_id"], o["model_id"]) for o in original.values() if "inherited" in o["evidence_status"]}
    reviewed = inherited.intersection(records)
    summary = {"original_inherited": len(inherited), "inherited_reviewed": len(reviewed),
               "inherited_numbers_matching": sum(records[k]["result"] == "number_matches" for k in reviewed),
               "inherited_current_source_differences": sum(records[k]["result"] == "current_source_differs" for k in reviewed),
               "inherited_different_dated_population": sum(records[k]["result"] == "different_dated_population" for k in reviewed),
               "inherited_remaining": len(inherited - reviewed), "all_observations_reviewed": len(records)}
    output = {"review_id": "source_review_2026_10_13", "reviewed_on": "2026-10-13", "reviewer": "Codex source audit; not independent human review",
              "summary": summary, "sources": sources, "observations": list(records.values()),
              "remaining": [{"benchmark_id": bid, "model_id": mid, "reason": "not_yet_corroborated_in_this_followup"} for bid, mid in sorted(inherited - reviewed)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    for row in records.values():
        if row["result"] != "number_matches":
            print(row["benchmark_id"], row["model_id"], row["stored_score"], "->", row["score"])


if __name__ == "__main__":
    main()
