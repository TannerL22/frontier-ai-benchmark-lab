"""Public registration cutoff, review gating and an explicit acquisition ledger."""
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from .integrity import verify_manifest
from .study import score_future, timestamp


def verify_publication(root, publication):
    root = Path(root)
    if publication.get("status") != "publicly_registered_awaiting_future_outcomes":
        raise ValueError("The study needs an actual public registration")
    if not publication.get("registration_url", "").startswith("https://github.com/TannerL22/frontier-ai-benchmark-lab/issues/"):
        raise ValueError("Unknown registration location")
    start = timestamp(publication["public_registered_at"])
    end = timestamp(publication["collection_ends_at"])
    if end != start + timedelta(days=180):
        raise ValueError("The registered collection window must remain 180 days")
    bundle = root / publication["bundle_path"]
    verify_manifest(bundle, bundle / "seal.json")
    registration = json.loads((bundle / "registration.json").read_text())
    if publication["forecast_sha256"] != registration["forecast_sha256"]:
        raise ValueError("The public forecast commitment disagrees with the sealed bundle")
    if timestamp(registration["sealed_at"]) > start:
        raise ValueError("Forecasts were not sealed before public registration")
    # Verify exactly the public frozen inputs even after later software changes.
    commit = publication["frozen_input_commit"]
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("A full immutable input commit is required")
    for path, expected in registration["input_sha256"].items():
        blob = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, check=True, capture_output=True).stdout
        canonical = blob.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != expected:
            raise ValueError(f"Frozen Git input disagrees with the public commitment: {path}")
    return registration


@contextmanager
def registered_input_snapshot(root, publication, registration):
    """Give the unchanged scorer its original inputs after unrelated UI updates.

    Public registration verification has already checked the Git commitment.
    Locally sealed preparation bundles continue to verify their current root.
    """
    commit = publication.get("frozen_input_commit")
    if not commit:
        yield Path(root)
        return
    # The UI is not a scoring dependency. Every other registered live input
    # still has to match, preventing this adapter from permitting engine retuning.
    verify_manifest(root, {"sha256": {path: expected for path, expected in registration["input_sha256"].items()
                                     if path != "src/frontierlab/presentation.py"}})
    with tempfile.TemporaryDirectory(prefix="frontier-registered-inputs-") as directory:
        snapshot = Path(directory).resolve()
        for relative in registration["input_sha256"]:
            path = (snapshot / relative).resolve()
            if not path.is_relative_to(snapshot):
                raise ValueError("Registered input path escapes snapshot")
            blob = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root,
                                  check=True, capture_output=True).stdout
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        verify_manifest(snapshot, {"sha256": registration["input_sha256"]})
        yield snapshot


def score_registered(root, publication, proposals, now=None):
    root = Path(root)
    registration = verify_publication(root, publication)
    start, end = timestamp(publication["public_registered_at"]), timestamp(publication["collection_ends_at"])
    now = datetime.now(timezone.utc) if now is None else now
    eligible, dispositions = [], []
    for number, row in enumerate(proposals, 1):
        if not isinstance(row, dict):
            dispositions.append({"proposal_number": number, "benchmark_id": None, "source_url": None,
                                 "status": "retained_not_scored", "reason": "Proposal must be a JSON object"})
            continue
        reason = ""
        try:
            published, acquired = timestamp(row["published_at"]), timestamp(row["acquired_at"])
            if not start < published <= end:
                raise ValueError("Publication outside the registered future-outcome window")
            if acquired < start or acquired < published or acquired > now or published > now:
                raise ValueError("Acquisition must follow publication and registration, and cannot be in the future")
            if row.get("prior_exposure") is not False:
                raise ValueError("Prior exposure is present or not explicitly assessed")
            if row.get("reviewer_id") != publication["independent_reviewer_id"]:
                raise ValueError("Independent eligibility review is pending from the designated reviewer")
            if not acquired <= timestamp(row["reviewed_at"]) <= now:
                raise ValueError("Eligibility review must follow acquisition and cannot be in the future")
            if row.get("review_accepted") is not True or not row.get("review_reason"):
                raise ValueError("Independent eligibility review has not accepted this outcome")
            eligible.append(row)
        except (KeyError, TypeError, ValueError) as error:
            reason = str(error)
        dispositions.append({"proposal_number": number, "benchmark_id": row.get("benchmark_id"),
                             "source_url": row.get("source_url"), "status": "eligible_for_structural_checks" if not reason else "retained_not_scored",
                             "reason": reason})
    # Original method, forecast and scoring mappings are unchanged.
    with registered_input_snapshot(root, publication, registration) as inputs:
        report = score_future(inputs, root / publication["bundle_path"], eligible)
    for rejection in report["rejected_outcomes"]:
        target = eligible[rejection["row"] - 1]
        for disposition in dispositions:
            if disposition["benchmark_id"] == target.get("benchmark_id") and disposition["status"] == "eligible_for_structural_checks":
                disposition.update(status="retained_not_scored", reason=rejection["reason"])
                break
    report.update(public_registered_at=publication["public_registered_at"], collection_ends_at=publication["collection_ends_at"],
                  registration_url=publication["registration_url"], proposal_count=len(proposals), acquisition_ledger=dispositions,
                  independent_reviewer_id=publication["independent_reviewer_id"],
                  study_status="awaiting_future_outcomes" if not proposals else "review_or_scoring_in_progress")
    return report
