"""Evidence-first Streamlit interface; global aggregation is an optional experiment."""
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from frontierlab.core import Evidence, METHODS
from frontierlab.analysis import (
    PAIR_BASELINES, coverage, contributions, deletion_sensitivity,
    genealogy_evidence, selected_rows, validation_records,
)
from frontierlab.presentation import csv_export, system_record

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
st.set_page_config(page_title="Frontier AI Benchmark Lab", page_icon="📊", layout="wide")


@st.cache_resource
def load_data(version):
    return Evidence(RELEASES[version])


@st.cache_data
def held_out(version, mode):
    return validation_records(load_data(version), mode)


@st.cache_data
def sensitivity(version, method, mode, ids):
    return deletion_sensitivity(load_data(version), method, mode, ids)


def source_link(url, label="Original source"):
    st.link_button(label, url)


def show_observation(evidence, row, model):
    detail = system_record(evidence, row, model)
    st.markdown("**" + model + "**")
    st.caption(detail["evidence_status"].replace("_", " ").capitalize())
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


st.sidebar.title("Frontier AI Lab")
version = st.sidebar.radio("Evidence release", list(RELEASES))
page = st.sidebar.radio("Explore", PAGES)
ev = load_data(version)
st.sidebar.caption("Reported systems and selected tasks. Coverage, configuration and source quality determine what can be inferred.")
st.caption(version + " · Evidence cutoff: " + ev.config.get("evidence_cutoff", ev.config["as_of"]))
if ev.catalog is None:
    st.info("Historical snapshot. Detailed run metadata is available in the v5.2 evidence review; historical inputs and formulas remain frozen.")

if page == "Evidence coverage":
    st.title("Compare what was actually evaluated")
    st.write("Start with task coverage and source records. These results describe selected reported systems; they do not establish a universal model winner.")
    rows = coverage(ev)
    a, b, c = st.columns(3)
    a.metric("Model identities", len(ev.models))
    b.metric("Recorded results", len(ev.score_records))
    c.metric("Evaluator labels", len(ev.evaluators))
    st.warning("Single-evaluator evidence and unobserved domains limit broad comparisons. A missing result means no evidence entered in this release, not zero capability.")
    domains = list(ev.domain_weights)
    matrix = pd.DataFrame(rows).set_index("Model")[domains]
    fig = px.imshow(matrix, text_auto=True, aspect="auto", color_continuous_scale="Blues",
                    labels={"color": "Recorded rows"})
    fig.update_layout(height=460, margin=dict(t=10, l=0, r=0, b=0))
    st.plotly_chart(fig, width="stretch")
    st.dataframe([{k: v for k, v in row.items() if k not in domains} for row in rows],
                 hide_index=True, width="stretch")
    st.caption("Counts are result rows and source labels, not independent sample sizes.")
    model = st.selectbox("Inspect model coverage", ev.models)
    record = next(row for row in rows if row["Model"] == model)
    st.write("Sources:", record["Source coverage"])
    st.write("Unobserved domains:", record["Missing domains"])
    if ev.catalog:
        st.subheader("What has been checked")
        statuses = ev.catalog.status_counts()
        st.dataframe([{"Evidence status": key.replace("_", " "), "Included observations": value}
                      for key, value in statuses.items()], hide_index=True, width="stretch")
        st.caption("Numeric corroboration checks the displayed number. It does not certify exact run identity or equal budgets. Source captures here are curated transcriptions, not archived original webpages.")
    st.download_button("Download coverage", csv_export(rows), "coverage.csv", "text/csv")

elif page == "Compare recorded results":
    st.title("Evidence for a model pair")
    st.write("Compare co-recorded task scores and inspect the systems behind them. Matching tasks does not establish matching harnesses, populations or resource budgets.")
    a, b = st.columns(2)
    model_a = a.selectbox("Model A", ev.models, index=0)
    model_b = b.selectbox("Model B", ev.models, index=6 if len(ev.models) > 6 else len(ev.models) - 1)
    domain = st.selectbox("Task domain", ["All domains"] + list(ev.domain_weights))
    evaluator = st.selectbox("Evaluator", ["All evaluators"] + ev.evaluators)
    provisional = st.checkbox("Include AA results labelled under review", value=False)
    if model_a == model_b:
        st.info("Choose two different model identities.")
    else:
        ia, ib = ev.models.index(model_a), ev.models.index(model_b)
        ids = selected_rows(ev, None if domain == "All domains" else [domain],
                            None if evaluator == "All evaluators" else [evaluator], provisional)
        shared = [ev.rows[i] for i in ids if ev.rows[i].scores[ia] is not None and ev.rows[i].scores[ib] is not None]
        st.metric("Co-recorded rows in this selection", len(shared))
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
            st.dataframe(table, hide_index=True, width="stretch")
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
    st.title("Inspect the evidence")
    evaluator = st.selectbox("Source organisation", ["All evaluators"] + ev.evaluators)
    domain = st.selectbox("Capability domain", ["All domains"] + list(ev.domain_weights))
    ids = selected_rows(ev, None if domain == "All domains" else [domain],
                        None if evaluator == "All evaluators" else [evaluator])
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
        available = [model for i, model in enumerate(ev.models) if row.scores[i] is not None]
        model = st.selectbox("Recorded system", available)
        st.metric("Published result", row.scores[ev.models.index(model)])
        show_observation(ev, row, model)
        absent = [model for model in ev.models if model not in available]
        if absent:
            st.write("Missing from this release:", ", ".join(absent))
        if ev.catalog:
            excluded = [o for o in ev.catalog.observations if o["benchmark_id"] == row.id and not o["included"]]
            for observation in excluded:
                with st.expander("Excluded alternative configuration"):
                    st.json(observation)
                    st.json(ev.catalog.systems[observation["system_id"]])

elif page == "Validation":
    st.title("Which evidence predicts other tasks?")
    st.warning("Retrospective holdouts among the selected model identities. These results are exploratory and do not validate future releases or general intelligence.")
    modes = {"Benchmark family": "family", "Evaluator": "evaluator", "Capability domain": "domain",
             "Broader task ancestry (sensitivity)": "genealogy"}
    label = st.selectbox("Withhold all evidence from one", list(modes))
    mode = modes[label]
    threshold = st.selectbox("Exclude observed margins at or below", [0.0, 0.10, 0.25])
    st.caption("Thresholds use the release's experimental normalization units, not standard errors.")
    records = held_out(version, mode)
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
    st.plotly_chart(fig, width="stretch")
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"Family/group mean accuracy": st.column_config.NumberColumn(format="%.3f"),
                                "Coverage": st.column_config.NumberColumn(format="%.3f")})
    st.info("Accuracy is conditional on predicted cases. Compare coverage as well as accuracy. Disconnected components are never aligned; identifiable comparisons within a component can still be predicted.")
    method = st.selectbox("Inspect holdout groups", all_methods)
    st.dataframe(summaries[method]["folds"], hide_index=True, width="stretch")
    st.write("Abstention reasons:", summaries[method]["abstention_reasons"] or "None")
    with st.expander("Prediction coverage by model"):
        model_rows = []
        for model in ev.models:
            summary = ev.macro_accuracy([r for r in records if model in (r["model_a"], r["model_b"])], mode, method, threshold)
            model_rows.append({"Model": model, "Attempted": summary["attempted_pair_count"],
                               "Predicted": summary["pair_count"], "Abstained": summary["abstained_pair_count"],
                               "Conditional group accuracy": summary["macro"]})
        st.dataframe(model_rows, hide_index=True, width="stretch")
    st.caption("Model pairs from the same benchmark are correlated. Pair counts are not independent sample sizes. Broader ancestry is a sensitivity assumption, not proof of duplicated tasks.")
    st.download_button("Download holdout predictions", csv_export(records), "holdout_predictions.csv", "text/csv")

elif page == "Release notes":
    st.title("Release scope and decisions")
    st.write(ev.config.get("note", "Frozen historical reference"))
    if ev.catalog:
        st.json(json.loads((ev.data_dir / "release.json").read_text(encoding="utf-8")))
        for decision in ev.catalog.decisions:
            st.subheader(decision["id"] + " · " + decision["decision"])
            st.write(decision["basis"])
            st.caption(decision["date"] + " · " + decision["review_status"])
        st.download_button("Download observation records", (ev.data_dir / "observations.jsonl").read_text(encoding="utf-8"),
                           "observations.jsonl", "application/x-ndjson")
        st.download_button("Download missing-evidence reasons", (ev.data_dir / "missingness.csv").read_text(encoding="utf-8"),
                           "missingness.csv", "text/csv")
    else:
        st.info("This release is retained exactly as published. Use v5.2 for the documented correction decisions and record-level qualifications.")
    with st.expander("Publisher indices: external context only"):
        st.dataframe(ev.external, hide_index=True, width="stretch",
                     column_config={"source_url": st.column_config.LinkColumn()})
        st.caption("These composites are excluded from calculation inputs. Agreement is not independent validation when constituent evidence overlaps.")

elif page == "Aggregation experiments":
    st.title("Conditional portfolio summaries")
    st.warning("These are optional experimental summaries of selected evidence. Their scale, weights and fitted roster are conventions; they do not provide intelligence percentages, calibrated confidence or universal ranks.")
    global_portfolio = st.checkbox("Explore the full heterogeneous portfolio", value=False)
    evaluator = "All evaluators" if global_portfolio else st.selectbox("Restrict to one evaluator", ev.evaluators, index=ev.evaluators.index("AA"))
    selected_domains = st.multiselect("Domains in this experiment", list(ev.domain_weights), default=list(ev.domain_weights))
    include_provisional = st.checkbox("Include provisional AA tasks in this experiment", value=False)
    advanced = st.checkbox("Include historical advanced weighting", value=False)
    methods = list(METHODS if advanced else METHODS[:2])
    method = st.selectbox("Weighting convention", methods)
    ids = selected_rows(ev, selected_domains, None if global_portfolio else [evaluator], include_provisional)
    st.dataframe([{k: value for k, value in row.items() if k in {"Model", "Recorded results", "Evaluators", "Missing domains", "Scope"}}
                  for row in coverage(ev, ids)], hide_index=True, width="stretch")
    values = ev.index(ev.fit(ids, method))
    if values is None:
        st.info("This selection cannot identify a joint comparison of the whole roster. No global result is shown.")
    else:
        data = [{"Model": model, "Relative difference": round(value - 100, 1)} for model, value in values.items()]
        fig = px.scatter(data, x="Relative difference", y="Model", title="Difference from the reference system on this selected portfolio")
        fig.add_vline(x=0, line_dash="dash")
        fig.update_traces(marker_size=10)
        fig.update_layout(height=450)
        st.plotly_chart(fig, width="stretch")
        st.dataframe(data, hide_index=True, width="stretch")
        st.caption("Reference: " + ev.anchor + ". Rounding does not imply measurement precision. Values should not be compared across releases.")
        with st.expander("Weight and normalization contributions"):
            st.dataframe(contributions(ev, ids, method), hide_index=True, width="stretch")
    if global_portfolio:
        with st.expander("Source and family removal sensitivity"):
            removed = st.selectbox("Remove one group at a time", ["evaluator", "family"])
            st.dataframe(sensitivity(version, method, removed, tuple(ids)), hide_index=True, width="stretch")
            st.caption("Ranges are sensitivity scenarios, not confidence intervals.")
        if ev.catalog:
            with st.expander("Broader genealogy sensitivity"):
                alternate = genealogy_evidence(ev)
                scores = alternate.index(alternate.fit(ids, method))
                if scores:
                    st.dataframe([{"Model": model, "Relative difference": round(value - 100, 1)} for model, value in scores.items()],
                                 hide_index=True, width="stretch")
                st.caption("Alternative ancestry grouping; task duplication has not been established.")

elif page == "Research programme":
    st.title("Testing what generalizes")
    st.write("The next scientific step is a time-stamped prediction study and a narrow original workflow pilot.")
    st.info("No prospective outcomes or paid model runs have been collected. The prepared local pilot exercises the evaluator; an oracle demonstration is not an AI performance result.")
    publication = ROOT / "studies/prospective_v1/publication.json"
    if publication.exists():
        record = json.loads(publication.read_text())
        st.success("Prospective forecasts publicly registered. Independent eligibility review remains with the project owner.")
        st.link_button("Public study registration", record["registration_url"])
        st.write("Outcome window:", record["public_registered_at"], "to", record["collection_ends_at"])
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

