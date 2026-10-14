"""Evidence-first Streamlit interface; global aggregation is an optional experiment."""
from pathlib import Path
import json
import subprocess

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frontierlab.core import Evidence, METHODS
from frontierlab.analysis import (
    PAIR_BASELINES, coverage, contributions, deletion_sensitivity,
    genealogy_evidence, selected_rows, validation_records,
)
from frontierlab.integrity import verify_manifest
from frontierlab.prospective_ops import verify_publication
from frontierlab.presentation import (
    COLORS, badge, csv_export, identity_columns, inject_lab_theme_css, rank_shift,
    render_audit_callout, render_hero, render_kpi_grid, render_section,
    system_record, theme_plotly,
)

ROOT = Path(__file__).resolve().parent
RELEASES = {
    "v5.3 · Source follow-up": ROOT / "data" / "v5_3",
    "v5.2 · Evidence review": ROOT / "data" / "v5_2",
    "v5.1 · Original eight-model release": ROOT / "data" / "v5_1",
    "v4.2 · Frozen six-model reference": ROOT / "data",
}
PAGES = [
    "Evidence coverage", "Compare recorded results", "Evidence details",
    "Validation", "Release notes", "Aggregation experiments", "Research programme",
]
st.set_page_config(page_title="Frontier AI · Research Observatory", page_icon="◈", layout="wide")
inject_lab_theme_css()


@st.cache_resource
def load_data(version):
    return Evidence(RELEASES[version])


@st.cache_data
def held_out(version, mode):
    return validation_records(load_data(version), mode)


@st.cache_data
def sensitivity(version, method, mode, ids):
    return deletion_sensitivity(load_data(version), method, mode, ids)


def read_json(relative):
    path = ROOT / relative
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data
def checked_integrity(fingerprint):
    # The cache key includes every input's size/mtime, not just the manifest.
    try:
        manifest = verify_manifest(ROOT, ROOT / "snapshots/canonical_integrity_manifest.json")
        return True, len(manifest["sha256"]), "All canonical release input hashes match."
    except (OSError, ValueError, KeyError) as error:
        return False, 0, str(error)


def integrity_status():
    path = ROOT / "snapshots/canonical_integrity_manifest.json"
    try:
        manifest = json.loads(path.read_text())
        files = [path] + [ROOT / relative for relative in manifest["sha256"]]
        fingerprint = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)
        return checked_integrity(fingerprint)
    except (OSError, ValueError, KeyError) as error:
        return False, 0, str(error)


def plot(fig, height=440):
    st.plotly_chart(theme_plotly(fig, height=height), width="stretch", config={"displaylogo": False})


def scoped_ids(evidence, ids):
    selected = st.session_state.get("context_evaluators_" + evidence.data_dir.name, evidence.evaluators)
    return [i for i in ids if evidence.rows[i].evaluator in selected]


def visible_models(evidence):
    key = evidence.data_dir.name
    providers = st.session_state.get("context_providers_" + key, sorted({r["developer"] for r in evidence.model_registry}))
    openness = st.session_state.get("context_openness_" + key, "All access types")
    minimum = st.session_state.get("context_coverage_" + key, 0)
    registry = {r["model_name"]: r for r in evidence.model_registry}
    rows = coverage(evidence, scoped_ids(evidence, range(len(evidence.rows))))
    count = len(scoped_ids(evidence, range(len(evidence.rows))))
    return [row["Model"] for row in rows if registry[row["Model"]]["developer"] in providers
            and (openness == "All access types" or registry[row["Model"]].get("weight_access", "Not recorded") == openness)
            and (100 * row["Recorded results"] / count if count else 0) >= minimum]


def searchable_table(rows, label, key, configs=None, status_field=None):
    search = st.text_input(label, placeholder="Search model, benchmark, source or identifier…", key=key)
    selected = rows
    if status_field and rows:
        status = st.selectbox("Verification status", ["All statuses"] + sorted({str(r.get(status_field, "unknown")) for r in rows}), key=key + "_status")
        if status != "All statuses":
            selected = [r for r in selected if str(r.get(status_field, "unknown")) == status]
    if search.strip():
        selected = [r for r in selected if search.casefold() in " ".join(str(v) for v in r.values()).casefold()]
    st.caption(f"{len(selected):,} / {len(rows):,} records · filters apply to this table")
    if selected:
        st.dataframe(selected, hide_index=True, width="stretch", column_config={**identity_columns(), **(configs or {})})
    else:
        st.info("No records match this search. Clear the filters to restore the table.")
    return selected


def audit_workspace():
    render_audit_callout("Canonical release inputs", integrity_detail, "Verified" if integrity_ok else "Failed", "verified" if integrity_ok else "issue")
    for name, filename in [("Original implementation checks", "outputs/verification.json"), ("Source and research operations checks", "outputs/operations_verification.json")]:
        report = read_json(filename)
        if report:
            tests = report.get("full_pytest", {}).get("passed", "unknown")
            render_audit_callout(name, f"Recorded on {report.get('date', 'unknown')}: {tests} tests passed. This is a saved verification report, not a live CI check.", "Recorded", "neutral")
            with st.expander("Inspect " + name.lower()):
                st.json(report)


def source_audit():
    report = read_json("reviews/source_review_2026_10_13.json")
    if not report:
        st.info("No dated source follow-up report is available.")
        return
    render_section("Dated source follow-up", "13 Oct 2026 · v5.3 review context")
    counts = report["summary"]
    render_kpi_grid([
        {"label": "Inherited investigated", "value": counts["inherited_reviewed"], "status": "Source follow-up", "caption": "Checks of inherited observation records"},
        {"label": "Matching numbers", "value": counts["inherited_numbers_matching"], "status": "Corroborated", "tone": "verified", "caption": "Exact historical run conditions remain incomplete"},
        {"label": "Source revisions", "value": counts["inherited_current_source_differences"], "status": "Dated revisions", "caption": "A source update versus prior error is unestablished"},
        {"label": "Historical population gap", "value": counts["inherited_different_dated_population"], "status": "Unresolved", "tone": "pending", "caption": "Another dated leaderboard cannot replace the snapshot"},
    ])
    sources = {s["source_id"]: s for s in report["sources"]}
    models_by_id = ev.catalog.models if ev.catalog else {}
    records = [{"Benchmark": r["benchmark_id"], "Model": models_by_id.get(r["model_id"], {}).get("model_name", r["model_id"]),
                "Stored score": r.get("stored_score"), "Source score": r.get("score"), "Status": r["result"],
                "Qualification": r["qualification"], "Source": sources.get(r["source_id"], {}).get("url", "")}
               for r in report["observations"]]
    searchable_table(records, "Search source audit", "audit_search", status_field="Status", configs={
        "Source": st.column_config.LinkColumn(), "Stored score": st.column_config.NumberColumn(format="%.2f"), "Source score": st.column_config.NumberColumn(format="%.2f")})
    st.caption("The ledger displays the follow-up audit, including different source dates. It does not replace the selected release's calculation inputs. Full reader captures are retained locally; original webpage bytes were not archived.")
    with st.expander("Source captures and digests"):
        searchable_table([{k: str(v) for k, v in s.items() if k != "reported_profile_defaults"} for s in report["sources"]], "Search source captures", "capture_search", configs={"url": st.column_config.LinkColumn()})
    with st.expander("Original 12 Oct corroboration ledger"):
        path = ROOT / "snapshots/source_corroboration_2026_10_12.csv"
        if path.exists():
            frame = pd.read_csv(path).astype(object)
            searchable_table(frame.where(pd.notna(frame), None).to_dict("records"), "Search earlier corroborations", "earlier_capture_search")


def sync_main_policy():
    st.session_state["context_weighting"] = st.session_state["experiment_method"]


def sync_context_policy():
    st.session_state["experiment_method"] = st.session_state["context_weighting"]
    if st.session_state["context_weighting"] == METHODS[2]:
        st.session_state["advanced_weighting"] = True


@st.cache_data(ttl=60)
def publication_check(fingerprint):
    record = read_json("studies/prospective_v1/publication.json")
    try:
        verify_publication(ROOT, record)
        return True, "Forecast hashes and frozen Git inputs match the public commitment."
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        return False, "Full publication verification is unavailable: " + str(error)


def source_link(url, label="Original source"):
    st.link_button(label, url)


def show_observation(evidence, row, model):
    detail = system_record(evidence, row, model)
    render_section(model)
    st.html(badge(detail["evidence_status"].replace("_", " "),
                  "verified" if detail["evidence_status"] == "numeric_corroborated" else "pending"))
    system = detail["system"]
    st.write("Reasoning:", system["reasoning_effort"], " · Harness:", system["harness"])
    with st.expander("Tested configuration and source record"):
        st.json(system)
        st.write("Recorded task/trial counts:", detail.get("sample_count", "unknown"), "/", detail.get("trial_count", "unknown"))
        st.write("Original run ID:", detail["original_run_id"])
        st.write("Inclusion decision:", detail["inclusion_reason"])
        st.write("Source record:", detail["source"]["capture_type"].replace("_", " "))
        st.write("Source observed on:", detail["source"]["observed_on"])
        st.write(detail["source"]["qualification"])
        st.write("Uncertainty:", detail["uncertainty"])
        if detail.get("derivation"):
            st.json(detail["derivation"])
    source_link(detail["source"]["url"])
    return detail


st.sidebar.html('<div class="lab-brand"><span class="lab-mark">◈</span><span>Frontier AI Lab</span></div><div class="lab-eyebrow">Release & dataset</div>')
version = st.sidebar.radio("Evidence release", list(RELEASES))
st.sidebar.html('<div class="lab-eyebrow">Workspace</div>')
page = st.sidebar.radio("Explore", PAGES)
ev = load_data(version)
models = visible_models(ev)
integrity_ok, integrity_count, integrity_detail = integrity_status()
release = read_json(ev.data_dir.relative_to(ROOT) / "release.json")
release_id = release.get("id", version.split(" · ")[0])
render_hero("Frontier AI Benchmark Lab", "A research observatory for reported AI systems. Trace the evidence, inspect what is missing, and test what generalizes.",
            release=release_id, status="Inputs verified" if integrity_ok else "Integrity check failed", tone="verified" if integrity_ok else "issue",
            context=[("Evidence cutoff", ev.config.get("evidence_cutoff", ev.config["as_of"])),
                     ("Benchmark rows", len(ev.rows)), ("Evaluators", len(ev.evaluators)), ("Workspace", page)])
if not integrity_ok:
    st.error(integrity_detail)
if not models:
    st.info("No model identities match the global display filters. Reset the filters in the sidebar to restore the view.")
if ev.catalog is None:
    st.info("Historical snapshot. Detailed run metadata is available in the v5.2 evidence review; historical inputs and formulas remain frozen.")

if page == "Evidence coverage":
    render_section("Compare what was actually evaluated", "Observed records · no inferred scores")
    st.write("Start with task coverage and source records. These results describe selected reported systems; they do not establish a universal model winner.")
    ids = scoped_ids(ev, range(len(ev.rows)))
    rows = [r for r in coverage(ev, ids) if r["Model"] in models]
    observed = sum(r["Recorded results"] for r in rows)
    slots = len(ids) * len(models)
    statuses = ev.catalog.status_counts() if ev.catalog else {}
    corroborated = statuses.get("numeric_corroborated", 0) + statuses.get("provisional_numeric_corroborated", 0)
    render_kpi_grid([
        {"label": "Model identities", "value": len(models), "status": "Display selection", "caption": f"{len(ev.models)} identities in the frozen roster"},
        {"label": "Recorded results", "value": f"{observed:,}", "status": "Observed", "tone": "verified", "caption": "Selected model–benchmark records"},
        {"label": "Evidence coverage", "value": f"{observed / slots:.1%}" if slots else "—", "status": "Reporting coverage", "caption": "Recorded cells / selected possible cells"},
        {"label": "Numeric corroborations", "value": f"{corroborated:,}" if ev.catalog else "—", "status": "Release-wide", "tone": "verified" if ev.catalog else "pending", "caption": "Includes provisional records; excludes reconstructions"},
        {"label": "Canonical inputs", "value": integrity_count if integrity_ok else "—", "status": "Hashes match" if integrity_ok else "Check failed", "tone": "verified" if integrity_ok else "issue", "caption": "Across all four preserved releases"},
    ])
    st.warning("Single-evaluator evidence and unobserved domains limit broad comparisons. A missing result means no evidence entered in this release, not zero capability.")
    domains = list(ev.domain_weights)
    render_section("Coverage atlas", "Missing evidence never implies zero capability")
    domain_tab, task_tab = st.tabs(["Domain coverage", "Benchmark coverage"])
    if rows:
        with domain_tab:
            matrix = pd.DataFrame(rows).set_index("Model")[domains]
            fig = px.imshow(matrix, text_auto=True, aspect="auto", color_continuous_scale=["#151b28", "#575fa0", "#b1b4ff"],
                            labels={"color": "Recorded rows", "x": "Capability domain", "y": "Model"})
            fig.update_traces(hovertemplate="%{y}<br>%{x}<br>Recorded rows: %{z}<extra></extra>")
            plot(fig, 430)
        with task_tab:
            matrix = pd.DataFrame({ev.rows[i].id: [int(ev.rows[i].scores[ev.models.index(m)] is not None) for m in models] for i in ids}, index=models)
            if not matrix.empty:
                fig = px.imshow(matrix, aspect="auto", color_continuous_scale=["#151b28", "#55d6be"], zmin=0, zmax=1,
                                labels={"color": "Recorded", "x": "Benchmark ID", "y": "Model"})
                fig.update_layout(coloraxis_colorbar=dict(tickvals=[0, 1], ticktext=["Missing", "Observed"]))
                fig.update_traces(hovertemplate="%{y}<br>Benchmark: %{x}<br>Recorded (0/1): %{z}<extra></extra>")
                plot(fig, 430)
            else:
                st.info("No benchmarks remain in the evaluator selection.")
    for row in rows:
        row["Coverage %"] = 100 * row["Recorded results"] / len(ids) if ids else None
    st.dataframe([{k: v for k, v in row.items() if k not in domains} for row in rows], hide_index=True, width="stretch",
                 column_config={**identity_columns(), "Coverage %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, color="#55d6be")})
    st.caption("Counts are result rows and source labels, not independent sample sizes.")
    if models:
        model = st.selectbox("Inspect model coverage", models)
        record = next(row for row in rows if row["Model"] == model)
        left, right = st.columns(2)
        with left:
            render_audit_callout("Recorded evaluator labels", record["Source coverage"] or "No recorded source", "Observed", "neutral")
        with right:
            render_audit_callout("Unobserved domains", record["Missing domains"], "Missingness", "pending")
    if ev.catalog:
        st.subheader("What has been checked")
        statuses = ev.catalog.status_counts()
        st.dataframe([{"Evidence status": key.replace("_", " "), "Included observations": value}
                      for key, value in statuses.items()], hide_index=True, width="stretch")
        st.caption("Numeric corroboration checks the displayed number. It does not certify exact run identity or equal budgets. Source captures here are curated transcriptions, not archived original webpages.")
    st.download_button("Download coverage", csv_export(rows), "coverage.csv", "text/csv")

elif page == "Compare recorded results":
    render_section("Evidence for a model pair", "Published values · original metric units")
    st.write("Compare co-recorded task scores and inspect the systems behind them. Matching tasks does not establish matching harnesses, populations or resource budgets.")
    a, b = st.columns(2)
    model_a = a.selectbox("Model A", models, index=0 if models else None)
    model_b = b.selectbox("Model B", models, index=min(6, len(models) - 1) if models else None)
    domain = st.selectbox("Task domain", ["All domains"] + list(ev.domain_weights))
    evaluator = st.selectbox("Evaluator", ["All evaluators"] + ev.evaluators)
    provisional = st.checkbox("Include AA results labelled under review", value=False)
    if not model_a or not model_b:
        st.info("Restore at least two models with the global display filters.")
    elif model_a == model_b:
        st.info("Choose two different model identities.")
    else:
        ia, ib = ev.models.index(model_a), ev.models.index(model_b)
        ids = scoped_ids(ev, selected_rows(ev, None if domain == "All domains" else [domain],
                            None if evaluator == "All evaluators" else [evaluator], provisional))
        shared = [ev.rows[i] for i in ids if ev.rows[i].scores[ia] is not None and ev.rows[i].scores[ib] is not None]
        render_kpi_grid([
            {"label": "Co-recorded rows", "value": len(shared), "status": "Observed", "tone": "verified", "caption": "Both identities have a reported result"},
            {"label": "Evaluator labels", "value": len({r.evaluator for r in shared}), "status": "Selected sources", "caption": "Source labels are not independent samples"},
            {"label": "Task families", "value": len({r.family for r in shared}), "status": "Shared selection", "caption": "Reported populations and budgets may differ"},
            {"label": "Inferred results", "value": "0", "status": "Observed only", "caption": "No score filled into a missing evidence cell"},
        ])
        sources = sorted({row.evaluator for row in shared})
        if len(sources) == 1:
            st.warning("All selected evidence comes from " + sources[0] + ". This is a source-specific comparison.")
        if any(row.id == "B032" for row in shared):
            st.info("Agent Arena reflects different live-session populations; these are observational system results.")
        table = [{
            "Benchmark": row.name, "Domain": row.domain, "Evaluator": row.evaluator,
            "A result": row.scores[ia], "B result": row.scores[ib], "Metric": row.unit,
            "A evidence": system_record(ev, row, model_a)["evidence_status"].replace("_", " "),
            "B evidence": system_record(ev, row, model_b)["evidence_status"].replace("_", " "),
        } for row in shared]
        if table:
            st.caption("A: " + model_a + " · B: " + model_b + ". Point estimates alone do not establish statistical superiority.")
            searchable_table(table, "Search recorded comparisons", "pair_search", configs={
                "A result": st.column_config.NumberColumn(format="%.2f"), "B result": st.column_config.NumberColumn(format="%.2f")})
            chosen = st.selectbox("Inspect a comparison", shared, format_func=lambda row: row.name)
            if ev.catalog:
                meta = next(r for r in ev.csv_rows("benchmarks.csv") if r["benchmark_id"] == chosen.id)
                st.write("Metric definition:", meta["metric_definition"])
            left, right = st.columns(2)
            with left:
                show_observation(ev, chosen, model_a)
            with right:
                show_observation(ev, chosen, model_b)
            st.download_button("Download selected results", csv_export(table), "recorded_comparison.csv", "text/csv")
        else:
            st.info("No shared recorded results for this selection. No score is inferred.")

elif page == "Evidence details":
    render_section("Inspect the evidence", "Run conditions · provenance · inclusion decisions")
    evaluator = st.selectbox("Source organisation", ["All evaluators"] + ev.evaluators)
    domain = st.selectbox("Capability domain", ["All domains"] + list(ev.domain_weights))
    ids = scoped_ids(ev, selected_rows(ev, None if domain == "All domains" else [domain],
                        None if evaluator == "All evaluators" else [evaluator]))
    rows = [ev.rows[i] for i in ids]
    if not rows:
        st.info("No evidence for the selected filters.")
    else:
        row = st.selectbox("Benchmark", rows, format_func=lambda value: value.name)
        st.write(row.domain + " · " + row.evaluator + " · " + row.unit)
        st.write("Reported conditions:", row.config)
        st.write("Source caveats:", row.provenance)
        st.write("Related evidence:", row.overlap_notes or "No overlap assessment recorded")
        if ev.catalog:
            meta = next(r for r in ev.csv_rows("benchmarks.csv") if r["benchmark_id"] == row.id)
            st.write("Metric:", meta["metric_definition"])
            st.write("Broader ancestry:", meta["genealogy_id"], "—", meta["genealogy_note"])
        available = [model for i, model in enumerate(ev.models) if row.scores[i] is not None and model in models]
        if available:
            model = st.selectbox("Recorded system", available)
            detail = system_record(ev, row, model)
            render_kpi_grid([
                {"label": "Published result", "value": f"{row.scores[ev.models.index(model)]:.2f}", "status": row.unit, "caption": "Original source metric; no cross-task normalization"},
                {"label": "Benchmark ID", "value": row.id, "status": "Observed", "tone": "verified", "caption": row.name},
                {"label": "Run identity", "value": detail["original_run_id"], "status": "Recorded metadata", "tone": "pending", "caption": "Unknown values remain explicit"},
                {"label": "Source date", "value": detail["source"]["observed_on"], "status": "Source record", "caption": "Capture date does not certify evaluation date"},
            ])
            show_observation(ev, row, model)
        else:
            st.info("No recorded systems for this benchmark match the global display filters.")
        absent = [model for model in ev.models if model not in available]
        if absent:
            st.write("Missing from this release:", ", ".join(absent))
        if ev.catalog:
            excluded = [o for o in ev.catalog.observations if o["benchmark_id"] == row.id and not o["included"]]
            for observation in excluded:
                with st.expander("Excluded alternative configuration"):
                    st.json(observation)
                    st.json(ev.catalog.systems[observation["system_id"]])
    if ev.catalog:
        render_section("Observation explorer", "Search the selected source and domain")
        records = []
        selected_benchmarks = {ev.rows[i].id for i in ids}
        for observation in ev.catalog.observations:
            name = ev.catalog.models[observation["model_id"]]["model_name"]
            if observation["benchmark_id"] in selected_benchmarks and name in models:
                source = ev.catalog.sources[observation["source_id"]]
                records.append({"Benchmark": observation["benchmark_id"], "Model": name, "Score": observation["score"],
                                "Status": observation["evidence_status"], "Included": observation["included"],
                                "System ID": observation["system_id"], "Source": source["url"], "Source date": source["observed_on"],
                                "Trial count": str(observation["trial_count"]), "Sample count": str(observation["sample_count"])})
        searchable_table(records, "Search observations", "observation_search", status_field="Status",
                         configs={"Source": st.column_config.LinkColumn(), "Score": st.column_config.NumberColumn(format="%.2f")})
        with st.expander("Missing-evidence ledger"):
            searchable_table(ev.catalog.missingness, "Search missing evidence", "missing_search")

elif page == "Validation":
    render_section("Which evidence predicts other tasks?", "Retrospective holdouts · conditional accuracy")
    st.warning("Retrospective holdouts among the selected model identities. These results are exploratory and do not validate future releases or general intelligence.")
    modes = {"Benchmark family": "family", "Evaluator": "evaluator", "Capability domain": "domain",
             "Broader task ancestry (sensitivity)": "genealogy"}
    label = st.selectbox("Withhold all evidence from one", list(modes))
    mode = modes[label]
    threshold = st.selectbox("Exclude observed margins at or below", [0.0, 0.10, 0.25])
    st.caption("Thresholds use the release's experimental normalization units, not standard errors.")
    selected_evaluators = st.session_state.get("context_evaluators_" + ev.data_dir.name, ev.evaluators)
    records = [r for r in held_out(version, mode) if r["model_a"] in models and r["model_b"] in models and r["evaluator"] in selected_evaluators]
    maximum_abstention = st.session_state.get("context_abstention_" + ev.data_dir.name, 100)
    diagnostic_method = st.session_state.get("validation_method", METHODS[0])
    if maximum_abstention < 100:
        eligible_models = []
        for model in models:
            attempted = [r for r in records if model in (r["model_a"], r["model_b"]) and abs(r["observed_margin_norm"]) > threshold]
            if attempted and 100 * sum(r[diagnostic_method] is None for r in attempted) / len(attempted) <= maximum_abstention:
                eligible_models.append(model)
        records = [r for r in records if r["model_a"] in eligible_models and r["model_b"] in eligible_models]
        st.caption(f"Display includes models with at most {maximum_abstention}% pair abstention under {diagnostic_method}; training fits remain unchanged.")
    all_methods = METHODS + PAIR_BASELINES
    summaries = {method: ev.macro_accuracy(records, mode, method, threshold) for method in all_methods}
    table = [{
        "Method": method, "Family/group mean accuracy": result["macro"],
        "Predicted": result["pair_count"], "Attempted": result["attempted_pair_count"],
        "Abstained": result["abstained_pair_count"], "Coverage": result["prediction_coverage"],
        "Scored groups": result["fold_count"], "Attempted groups": result["attempted_fold_count"],
    } for method, result in summaries.items()]
    fig = px.bar(table, x="Method", y="Family/group mean accuracy", range_y=[0, 1], text_auto=".1%")
    fig.add_hline(y=0.5, line_dash="dash", annotation_text="Random-direction reference: 50%")
    plot(fig)
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"Family/group mean accuracy": st.column_config.NumberColumn(format="%.3f"),
                                "Coverage": st.column_config.NumberColumn(format="%.3f")})
    st.info("Accuracy is conditional on predicted cases. Compare coverage as well as accuracy. Disconnected components are never aligned; identifiable comparisons within a component can still be predicted.")
    method = st.selectbox("Inspect holdout groups", all_methods, key="validation_method")
    summary = summaries[method]
    render_kpi_grid([
        {"label": "Group mean accuracy", "value": f"{summary['macro']:.1%}" if summary["macro"] is not None else "—", "status": "Conditional", "caption": "Unweighted mean across scored holdout groups"},
        {"label": "Prediction coverage", "value": f"{summary['prediction_coverage']:.1%}" if summary["prediction_coverage"] is not None else "—", "status": "Predicted / attempted", "caption": "Accuracy excludes abstained comparisons"},
        {"label": "Abstained pairs", "value": f"{summary['abstained_pair_count']:,}", "status": "Retained", "tone": "pending", "caption": "Disconnected comparisons are never aligned"},
        {"label": "Scored groups", "value": summary["fold_count"], "status": f"of {summary['attempted_fold_count']} attempted", "caption": "Pair counts are correlated within tasks"},
    ])
    groups_tab, residual_tab, abstention_tab = st.tabs(["Holdout groups", "Predicted vs observed", "Coverage & abstention"])
    with groups_tab:
        st.dataframe(summary["folds"], hide_index=True, width="stretch", column_config={
            "accuracy": st.column_config.ProgressColumn(format="%.3f", min_value=0, max_value=1)})
    with residual_tab:
        predicted = [{"Observed margin": r["observed_margin_norm"], "Predicted margin": r[method],
                      "Residual": r[method] - r["observed_margin_norm"], "Benchmark": r["benchmark"],
                      "Pair": r["model_a"] + " / " + r["model_b"], "Domain": r["domain"]}
                     for r in records if r[method] is not None and abs(r["observed_margin_norm"]) > threshold]
        if predicted:
            frame = pd.DataFrame(predicted)
            fig = px.scatter(frame, x="Observed margin", y="Predicted margin", color="Domain", opacity=.6,
                             hover_data={"Benchmark": True, "Pair": True, "Residual": ":.3f", "Observed margin": ":.3f", "Predicted margin": ":.3f"})
            low, high = min(frame["Observed margin"].min(), frame["Predicted margin"].min()), max(frame["Observed margin"].max(), frame["Predicted margin"].max())
            fig.add_trace(go.Scatter(x=[low, high], y=[low, high], mode="lines", name="Identity reference", line=dict(dash="dash", color="#a0aabc"), hoverinfo="skip"))
            fig.add_hline(y=0, line_width=1, line_color="#394153")
            fig.add_vline(x=0, line_width=1, line_color="#394153")
            plot(fig, 480)
            st.caption("Holdout pair margins in experimental normalization units. This is a residual diagnostic, not calibrated probability or a prediction of raw benchmark scores.")
            fig = px.histogram(frame, x="Residual", nbins=30, color_discrete_sequence=[COLORS[0]])
            fig.add_vline(x=0, line_dash="dash")
            plot(fig, 260)
        else:
            st.info("No identifiable holdout predictions remain for this selection.")
        if version.startswith("v4.2"):
            with st.expander("Frozen v4.2 nested probability calibration"):
                calibration = pd.read_csv(ROOT / "outputs/calibrated_predictions.csv")
                calibration = calibration[calibration["method"] == method].copy()
                if not calibration.empty:
                    calibration["Probability bin"] = (calibration["p_b_wins"] * 10).clip(upper=9).astype(int) / 10
                    curve = calibration.groupby("Probability bin", observed=True).agg(predicted=("p_b_wins", "mean"), observed=("observed_b_wins", "mean"), pairs=("p_b_wins", "size")).reset_index()
                    fig = px.scatter(curve, x="predicted", y="observed", size="pairs", range_x=[0, 1], range_y=[0, 1], hover_data=["pairs"], labels={"predicted": "Mean predicted P(B wins)", "observed": "Observed fraction B wins"})
                    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Identity reference", line=dict(dash="dash", color="#a0aabc")))
                    plot(fig)
                    st.caption("Descriptive probability bins; correlated pairs are not independent calibration samples. Frozen six-model v4.2 outputs only.")
                else:
                    st.info("No nested probability calibration was fitted for this baseline.")
    with abstention_tab:
        heatmap = []
        for model in models:
            model_records = [r for r in records if model in (r["model_a"], r["model_b"])]
            for fold in summaries[method]["folds"]:
                attempted = [r for r in model_records if r["fold"] == fold["fold"] and abs(r["observed_margin_norm"]) > threshold]
                heatmap.append({"Model": model, "Group": fold["fold"], "Abstention %": 100 * sum(r[method] is None for r in attempted) / len(attempted) if attempted else None})
        if heatmap:
            matrix = pd.DataFrame(heatmap).pivot(index="Model", columns="Group", values="Abstention %")
            fig = px.imshow(matrix, aspect="auto", zmin=0, zmax=100, color_continuous_scale=["#1c413e", "#e9b969", "#ee8ea6"], labels={"color": "Abstention %"})
            fig.update_traces(hovertemplate="%{y}<br>Group: %{x}<br>Abstained pairs: %{z:.1f}%<extra></extra>")
            plot(fig, 430)
            st.caption("Empty cells mean no attempted non-tied comparisons; 0% means every attempted comparison was predicted.")
    st.write("Abstention reasons:", summaries[method]["abstention_reasons"] or "None")
    with st.expander("Prediction coverage by model"):
        model_rows = []
        for model in models:
            summary = ev.macro_accuracy([r for r in records if model in (r["model_a"], r["model_b"])], mode, method, threshold)
            model_rows.append({"Model": model, "Attempted": summary["attempted_pair_count"],
                               "Predicted": summary["pair_count"], "Abstained": summary["abstained_pair_count"],
                               "Conditional group accuracy": summary["macro"]})
        st.dataframe(model_rows, hide_index=True, width="stretch")
    st.caption("Model pairs from the same benchmark are correlated. Pair counts are not independent sample sizes. Broader ancestry is a sensitivity assumption, not proof of duplicated tasks.")
    st.download_button("Download holdout predictions", csv_export(records), "holdout_predictions.csv", "text/csv")

elif page == "Release notes":
    render_section("Release scope and decisions", "Versioned inputs · dated review trail")
    st.write(ev.config.get("note", "Frozen historical reference"))
    scope_tab, source_tab, integrity_tab = st.tabs(["Scope & decisions", "Source audit", "Integrity & verification"])
    with scope_tab:
        if ev.catalog:
            render_audit_callout("Release scope", release["scope"], release["status"].replace("_", " "), "neutral")
            with st.expander("Full release record"):
                st.json(release)
            for decision in ev.catalog.decisions:
                with st.container(border=True):
                    render_section(decision["id"] + " · " + decision["decision"])
                    st.write(decision["basis"])
                    st.caption(decision["date"] + " · " + decision["review_status"])
            left, right = st.columns(2)
            left.download_button("Download observation records", (ev.data_dir / "observations.jsonl").read_text(encoding="utf-8"), "observations.jsonl", "application/x-ndjson")
            right.download_button("Download missing-evidence reasons", (ev.data_dir / "missingness.csv").read_text(encoding="utf-8"), "missingness.csv", "text/csv")
        else:
            st.info("This release is retained exactly as published. Use v5.2 for the documented correction decisions and record-level qualifications.")
    with source_tab:
        source_audit()
    with integrity_tab:
        audit_workspace()
    with st.expander("Publisher indices: external context only"):
        st.dataframe(ev.external, hide_index=True, width="stretch",
                     column_config={"source_url": st.column_config.LinkColumn()})
        st.caption("These composites are excluded from calculation inputs. Agreement is not independent validation when constituent evidence overlaps.")

elif page == "Aggregation experiments":
    render_section("Conditional portfolio summaries", "Experimental fits · full roster retained")
    st.warning("These are optional experimental summaries of selected evidence. Their scale, weights and fitted roster are conventions; they do not provide intelligence percentages, calibrated confidence or universal ranks.")
    global_portfolio = st.checkbox("Explore the full heterogeneous portfolio", value=False)
    evaluator = "All evaluators" if global_portfolio else st.selectbox("Restrict to one evaluator", ev.evaluators, index=ev.evaluators.index("AA"))
    selected_domains = st.multiselect("Domains in this experiment", list(ev.domain_weights), default=list(ev.domain_weights))
    include_provisional = st.checkbox("Include provisional AA tasks in this experiment", value=False)
    advanced = st.checkbox("Include historical advanced weighting", value=False, key="advanced_weighting")
    methods = list(METHODS if advanced else METHODS[:2])
    if st.session_state.get("experiment_method") not in methods:
        st.session_state["experiment_method"] = st.session_state.get("context_weighting", methods[0]) if st.session_state.get("context_weighting", methods[0]) in methods else methods[0]
    method = st.selectbox("Weighting convention", methods, key="experiment_method", on_change=sync_main_policy)
    ids = scoped_ids(ev, selected_rows(ev, selected_domains, None if global_portfolio else [evaluator], include_provisional))
    st.dataframe([{k: value for k, value in row.items() if k in {"Model", "Recorded results", "Evaluators", "Missing domains", "Scope"}}
                  for row in coverage(ev, ids) if row["Model"] in models], hide_index=True, width="stretch", column_config=identity_columns())
    values = ev.index(ev.fit(ids, method))
    if values is None:
        st.info("This selection cannot identify a joint comparison of the whole roster. No global result is shown.")
    elif not models:
        st.info("No model identities match the display filters; restore models to inspect the fitted portfolio.")
    else:
        data = [{"Model": model, "Relative difference": value - 100} for model, value in values.items() if model in models]
        fig = px.scatter(data, x="Relative difference", y="Model", title="Difference from the reference system on this selected portfolio")
        fig.add_vline(x=0, line_dash="dash")
        fig.update_traces(marker_size=10)
        fig.update_traces(marker_color=COLORS[0], hovertemplate="%{y}<br>Relative difference: %{x:.2f}<extra></extra>")
        plot(fig, 450)
        render_section("Conditional ranking & capability matrix", "Fitted summaries · not observed benchmark scores")
        ranks = pd.Series(values).rank(ascending=False, method="min").astype(int).to_dict()
        model_coverage = {r["Model"]: r["Recorded results"] for r in coverage(ev, ids)}
        domain_scores = {d: ev.index(ev.fit([i for i in ids if ev.rows[i].domain == d], method)) for d in selected_domains}
        leaderboard = [{"Rank": ranks[model], "Model": model, "Reference index": value, "Relative difference": value - 100,
                        "Coverage %": 100 * model_coverage[model] / len(ids) if ids else 0,
                        "Evidence type": "Experimental fitted summary",
                        **{d + " Δ": domain_scores[d][model] - 100 if domain_scores[d] else None for d in selected_domains}}
                       for model, value in sorted(values.items(), key=lambda item: -item[1]) if model in models]
        configs = {**identity_columns(),
                   "Reference index": st.column_config.ProgressColumn(format="%.2f", min_value=min(0, min(values.values())), max_value=max(110, max(values.values())), help="Reference system = 100; the scale is a convention, not capability percent."),
                   "Relative difference": st.column_config.NumberColumn(format="%+.2f"),
                   "Coverage %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, color="#55d6be"),
                   **{d + " Δ": st.column_config.NumberColumn(format="%+.2f", help="Separate domain fit relative to the reference; blank if the whole roster is disconnected.") for d in selected_domains}}
        st.dataframe(leaderboard, hide_index=True, width="stretch", column_config=configs)
        st.caption("Reference: " + ev.anchor + ". Rounding does not imply measurement precision. Values should not be compared across releases.")
        with st.expander("Weight and normalization contributions"):
            contribution_rows = contributions(ev, ids, method)
            frame = pd.DataFrame(contribution_rows)
            if not frame.empty:
                grouped = frame.groupby(["Domain", "Evaluator"], as_index=False)[["Nominal weight", "Observed comparison mass"]].sum()
                left, right = st.columns(2)
                with left:
                    fig = px.bar(grouped, x="Domain", y="Nominal weight", color="Evaluator", barmode="stack", title="Nominal portfolio weight", hover_data={"Nominal weight": ":.3f"})
                    plot(fig, 340)
                with right:
                    fig = px.bar(grouped, x="Domain", y="Observed comparison mass", color="Evaluator", barmode="stack", title="Observed comparison mass", hover_data={"Observed comparison mass": ":.3f"})
                    plot(fig, 340)
                st.caption("Observed mass discounts missing model comparisons. Weight shares describe the selected portfolio, not a fitted score decomposition.")
            st.dataframe(contribution_rows, hide_index=True, width="stretch", column_config={**identity_columns(), "Nominal weight": st.column_config.NumberColumn(format="%.4f"), "Observed comparison mass": st.column_config.NumberColumn(format="%.4f")})
    if global_portfolio:
        with st.expander("Source and family removal sensitivity"):
            removed = st.selectbox("Remove one group at a time", ["evaluator", "family"])
            scenarios = sensitivity(version, method, removed, tuple(ids))
            baseline_ranks = pd.Series(values).rank(ascending=False, method="min").to_dict() if values else {}
            for group in {r["Removed group"] for r in scenarios}:
                group_rows = [r for r in scenarios if r["Removed group"] == group and r["Relative difference"] is not None]
                scenario_ranks = pd.Series({r["Model"]: r["Relative difference"] for r in group_rows}).rank(ascending=False, method="min").to_dict()
                for row in group_rows:
                    row["Rank shift"] = rank_shift(int(baseline_ranks[row["Model"]] - scenario_ranks[row["Model"]])) if baseline_ranks else "—"
            if scenarios:
                group = st.selectbox("Inspect removed group", sorted({r["Removed group"] for r in scenarios}))
                chosen = [r for r in scenarios if r["Removed group"] == group]
                available = [r for r in chosen if r["Relative difference"] is not None and r["Model"] in models]
                if available:
                    bars = [{**r, "Change from baseline": r["Relative difference"] - (values[r["Model"]] - 100)} for r in available]
                    fig = px.bar(bars, x="Change from baseline", y="Model", orientation="h", text="Rank shift", color_discrete_sequence=[COLORS[0]], hover_data={"Relative difference": ":.2f", "Change from baseline": ":.2f"})
                    fig.add_vline(x=0, line_dash="dash")
                    plot(fig)
                else:
                    st.info("No model identities match the display filters." if not models else "Removing this group disconnects the full roster; no joint rank or score change is inferred.")
                searchable_table(scenarios, "Search removal scenarios", "removal_search", configs={"Relative difference": st.column_config.NumberColumn(format="%+.2f")})
            st.caption("Ranges are sensitivity scenarios, not confidence intervals.")
            st.caption("Rank shifts compare unrounded full-roster fits under the same weighting convention. Display filters do not refit or rerank the roster.")
        if ev.catalog:
            with st.expander("Broader genealogy sensitivity"):
                alternate = genealogy_evidence(ev)
                scores = alternate.index(alternate.fit(ids, method))
                if scores:
                    st.dataframe([{"Model": model, "Relative difference": round(value - 100, 1)} for model, value in scores.items() if model in models],
                                 hide_index=True, width="stretch")
                st.caption("Alternative ancestry grouping; task duplication has not been established.")

elif page == "Research programme":
    render_section("Testing what generalizes", "Prospective registry · original workflow pilot")
    st.write("The next scientific step is a time-stamped prediction study and a narrow original workflow pilot.")
    st.info("No prospective outcomes or paid model runs have been collected. The prepared local pilot exercises the evaluator; an oracle demonstration is not an AI performance result.")
    publication = ROOT / "studies/prospective_v1/publication.json"
    if publication.exists():
        record = json.loads(publication.read_text())
        bundle = ROOT / record["bundle_path"]
        try:
            verify_manifest(bundle, bundle / "seal.json")
            sealed = True
        except (OSError, ValueError, KeyError):
            sealed = False
        status = read_json("outputs/prospective_v1/status.json")
        render_kpi_grid([
            {"label": "Frozen forecasts", "value": f"{record['forecast_count']:,}", "status": "Sealed" if sealed else "Seal failed", "tone": "verified" if sealed else "issue", "caption": "Fixed v5.2 inputs; v5.3 revisions never retune them"},
            {"label": "Future outcomes", "value": status.get("accepted_outcome_count", 0), "status": "Awaiting acquisition", "tone": "pending", "caption": "Eligible outcomes accepted into the scoring report"},
            {"label": "Collection window", "value": "180 days", "status": "Publicly registered", "caption": "13 Oct 2026 – 11 Apr 2027"},
            {"label": "Paid model runs", "value": "0", "status": "Preparation only", "caption": "Human review and system conditions remain pending"},
        ])
        render_audit_callout("Public forecast commitment", "Public GitHub issue with server timestamp. Independent eligibility review remains with the project owner; this is not acceptance by an external registry.", "Sealed" if sealed else "Seal failed", "verified" if sealed else "issue", record["forecast_sha256"])
        st.link_button("Public study registration", record["registration_url"])
        st.write("Outcome window:", record["public_registered_at"], "to", record["collection_ends_at"])
        verification_files = [publication, bundle / "registration.json", bundle / "forecasts.jsonl", bundle / "seal.json"]
        fingerprint = tuple((str(p), p.stat().st_mtime_ns) for p in verification_files)
        publication_ok, publication_detail = publication_check(fingerprint)
        with st.expander("Registration verification & acquisition ledger"):
            render_audit_callout("Registered inputs and scoring rules", publication_detail, "Verified" if publication_ok else "Check unavailable", "verified" if publication_ok else "pending")
            proposals_path = ROOT / "studies/prospective_v1/outcome_proposals.jsonl"
            proposals = [json.loads(line) for line in proposals_path.read_text().splitlines() if line.strip()] if proposals_path.exists() else []
            if proposals:
                searchable_table([{k: str(v) for k, v in p.items()} for p in proposals], "Search outcome proposals", "proposal_search")
            else:
                st.info("The acquisition ledger is empty. No future outcome has been proposed or independently accepted.")
            st.json(record)
    review_packet = ROOT / "studies/artifact_pilot_v1/REVIEW_PACKET.md"
    if review_packet.exists():
        st.download_button("Download independent pilot review packet", review_packet.read_text(encoding="utf-8"),
                           "pilot_review_packet.md", "text/markdown")
    for name, path in [
        ("Prospective study protocol", ROOT / "studies" / "prospective_v1" / "protocol.json"),
        ("Original workflow pilot protocol", ROOT / "studies" / "artifact_pilot_v1" / "protocol.json"),
    ]:
        if path.exists():
            with st.expander(name):
                st.json(json.loads(path.read_text(encoding="utf-8")))
            st.download_button("Download " + name.lower(), path.read_text(encoding="utf-8"),
                               path.parent.name + "_protocol.json", "application/json")


# Add context controls after page widgets so the established page interaction
# order remains stable for saved sessions and the application smoke contract.
with st.sidebar:
    st.divider()
    st.html('<div class="lab-eyebrow">Aggregation policy</div>')
    st.selectbox("Portfolio weighting", list(METHODS), key="context_weighting", on_change=sync_context_policy)
    st.caption("Applied in Aggregation experiments. These conventions do not change observed scores.")
    with st.expander("Model & evaluator filters", expanded=False):
        key = ev.data_dir.name
        providers = sorted({r["developer"] for r in ev.model_registry})
        st.multiselect("Provider / organisation", providers, default=providers, key="context_providers_" + key)
        access = sorted({r.get("weight_access", "Not recorded") for r in ev.model_registry})
        st.selectbox("Weight access", ["All access types"] + access, key="context_openness_" + key,
                     help="Open/proprietary classifications are not captured in this release; no classification is inferred from the provider.")
        st.multiselect("Evaluator labels", ev.evaluators, default=ev.evaluators, key="context_evaluators_" + key)
        st.slider("Minimum reporting coverage (%)", 0, 100, 0, key="context_coverage_" + key)
        st.slider("Maximum holdout abstention (%)", 0, 100, 100, key="context_abstention_" + key,
                  help="In Validation, filters models by attempted-pair abstention for the selected method and holdout mode. Training fits are unchanged.")
        st.caption("Coverage uses the selected evaluator rows. Model filters change the displayed identities; the fitted training roster stays frozen.")
    st.html(badge(release_id) + " " + badge("Canonical inputs verified" if integrity_ok else "Integrity issue", "verified" if integrity_ok else "issue"))
    st.caption("Selected reported systems. Source quality, configuration and missing evidence determine what can be inferred.")

