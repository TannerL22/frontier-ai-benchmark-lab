"""Interactive product surface; provenance stays one level beneath comparisons."""
from html import escape
from pathlib import Path
import json

import plotly.graph_objects as go
import streamlit as st

from .core import Evidence, METHODS
from .explorer import product_evidence, support, broad_cohort, standings, domain_standings, robustness, comparison, release_changes
from .presentation import COLORS, theme_plotly, render_section, csv_export

TASKS = {
    "Build & debug": ("Coding", "⌘", "Repositories, terminals and coding agents"),
    "Think like a scientist": ("Science", "✧", "Scientific reasoning, diagnosis and lab decisions"),
    "Get work done": ("Professional", "↗", "Work products, automation and professional tasks"),
    "Know & reason": ("Knowledge", "◇", "Knowledge, reasoning and factual reliability"),
    "Handle long context": ("Context", "≋", "Reading and reasoning over long inputs"),
    "See & create": ("Multimodal", "◉", "Visual reasoning and interactive scene creation"),
    "Play & strategize": ("Games", "♜", "Game and strategy evaluations"),
}
PROVIDERS = {"Claude":"Anthropic", "GPT":"OpenAI", "Gemini":"Google", "Muse":"Meta"}
ACCENTS = {"Anthropic":"#efbb87", "OpenAI":"#77dac4", "Google":"#9bbcff", "Meta":"#c6a8ff"}
CSS = """
.front-hero {position:relative; overflow:hidden; padding:2.4rem; border:1px solid #9b9cff38; border-radius:22px; background:radial-gradient(ellipse at 95% 20%,#866de431,transparent 58%),linear-gradient(125deg,#171e30,#11151e); margin-bottom:.4rem}
.front-hero:after {content:'✧'; position:absolute; right:6%; top:-45px; font-size:280px; color:#b0a1ff16; pointer-events:none; transform:rotate(12deg)}
.front-hero h1 {font-size:clamp(2.1rem,4vw,3.4rem)!important; line-height:1.08; letter-spacing:-.055em; max-width:800px; margin:.7rem 0 .8rem; position:relative; z-index:1}
.front-hero p {max-width:700px; color:#b9c2d5; font-size:1.03rem; margin:.5rem 0 1.5rem}
.front-hero em {font-style:normal; color:#b7acff}
.front-kicker {color:#c4b4ff; font:600 .68rem var(--font-mono); letter-spacing:.14em; text-transform:uppercase}
.breadth-strip {display:flex; flex-wrap:wrap; gap:.65rem 1.7rem; position:relative; z-index:1}
.breadth-strip span {font-size:.78rem; color:#aab6cc}.breadth-strip strong {color:#eef0f7; font-size:1.15rem; padding-right:.3rem}
.front-fresh {font-size:.72rem; color:#91d8c5; margin-top:1.2rem; max-width:800px; position:relative; z-index:1}
.leader-grid {display:grid; grid-template-columns:1.22fr 1fr 1fr; gap:14px; margin:.3rem 0 1.2rem}
.model-card {border:1px solid #343c50; border-radius:17px; padding:1.4rem; background:linear-gradient(140deg,#1b2130,#11151e); position:relative; overflow:hidden; transition:transform .2s,border-color .2s}
.model-card:hover {transform:translateY(-3px); border-color:var(--model-accent)}
.model-card.primary {border-color:#b8a77c70; background:radial-gradient(ellipse at 100% 0,#d2a46020,transparent 65%),#171c27}
.card-top {display:flex; align-items:center; justify-content:space-between; color:var(--model-accent); font:600 .66rem var(--font-mono); text-transform:uppercase; letter-spacing:.06em}
.rank-orb {display:grid; place-items:center; height:38px; width:38px; border:1px solid #ffffff20; border-radius:50%; font-size:.92rem; background:#ffffff06}
.model-card h3 {font-size:1.35rem!important; margin:1rem 0 .2rem}.model-card p {font-size:.81rem; color:#adb8cb; margin:.4rem 0 1.2rem; min-height:2.6rem}
.card-support {display:flex; gap:1rem; font-size:.72rem; color:#9caac0}.card-support b {font-size:.9rem; color:#e9eef8; display:block}
.leader-note {padding:.8rem 1.1rem; border-left:3px solid #77dac4; background:#77dac40a; border-radius:0 10px 10px 0; color:#c4cfdd; font-size:.85rem; margin:.5rem 0}
.task-pick {display:flex; gap:1rem; align-items:center; padding:1rem 1.3rem; border:1px solid #9b9cff40; background:linear-gradient(110deg,#9b9cff15,#55d6be06); border-radius:14px; margin:.4rem 0 1rem}
.task-icon {font-size:2.3rem; color:#b3afff; width:50px; text-align:center}.task-pick h3 {margin:0}.task-pick p {margin:.2rem 0 0; color:#a6b3c7; font-size:.81rem}
.story-grid {display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:.6rem 0 1rem}
.story-card {border:1px solid #2e3a4e; border-radius:13px; padding:1.2rem; background:#141a26}.story-card .glyph {font-size:1.6rem; color:#b7abff}.story-card h3 {margin:.5rem 0}.story-card p {font-size:.8rem; color:#abb9cd; margin:.3rem 0}
.mini-label {font:500 .65rem var(--font-mono); color:#7ed9c3; text-transform:uppercase; letter-spacing:.06em}
.contenders {padding:1rem 1.3rem; border:1px dashed #5a4b77; border-radius:12px; font-size:.85rem; color:#bdb4d0}
@media(max-width:900px) {.leader-grid {grid-template-columns:1fr}.story-grid {grid-template-columns:1fr 1fr}.front-hero {padding:1.5rem}.front-hero:after {right:-40px;font-size:200px}.model-card p {min-height:0}}
@media(max-width:500px) {.story-grid {grid-template-columns:1fr}.breadth-strip {gap:.6rem 1rem}}
@media(prefers-reduced-motion:reduce) {.model-card {transition:none}.model-card:hover {transform:none}}
"""


def inject():
    st.html('<style>' + CSS + '</style>')


def provider(name):
    return next(value for prefix,value in PROVIDERS.items() if name.startswith(prefix))


def accent(name):
    return ACCENTS[provider(name)]


def hero(evidence, release_id, new=False):
    inject()
    title = 'Fresh on the <em>frontier.</em>' if new else 'A wider view of the<br><em>AI frontier.</em>'
    description = 'New tests. New perspectives. See what changed in the models we follow.' if new else 'Discover the leading models, find your task specialist, and see how well the leaders hold up across a broader mix of tests.'
    fresh = '<div class="front-fresh">NEW IN v5.4 &nbsp; ✧ 3D creation · rare-disease diagnosis · wet-lab decisions · another coding-agent perspective</div>' if any(r.id == "B063" for r in evidence.rows) else ''
    st.html(f'<div class="front-hero"><div class="front-kicker">Frontier AI Lab · {escape(release_id)} · {escape(evidence.config["as_of"])}</div><h1>{title}</h1><p>{description}</p><div class="breadth-strip"><span><strong>{len(evidence.models)}</strong> models</span><span><strong>{len(evidence.families)}</strong> benchmark families</span><span><strong>{len(evidence.rows)}</strong> evaluations</span><span><strong>{len(evidence.evaluators)}</strong> evaluator labels</span><span><strong>{len(evidence.score_records)}</strong> results</span></div>{fresh}</div>')


@st.cache_data
def report(data_dir, provisional):
    evidence = product_evidence(Evidence(Path(data_dir)),provisional)
    cohort = broad_cohort(evidence)
    tables = {m:standings(evidence,cohort,m) for m in METHODS}
    return dict(cohort=cohort, tables=tables,
                source_checks={m:robustness(evidence,cohort,m) for m in METHODS},
                family_checks={m:robustness(evidence,cohort,m,"family") for m in METHODS})


def explorer(evidence, visible):
    controls,options = st.columns([1,1])
    method = controls.selectbox("Your lens", list(METHODS), key="explorer_method", help="Equal families gives each task family equal weight. Equal domains gives the seven capability categories equal weight. The historical convention uses declared domain and evaluator weights.")
    provisional = options.toggle("Include EAP and publisher-review results", value=False, key="explorer_provisional",
                            help="Includes earlier Argon EAP science results and AA SciCode/CritPt results labelled under review. It does not certify those runs as today's public API.")
    view = product_evidence(evidence,provisional)
    details = report(str(evidence.data_dir),provisional)
    table = details["tables"][method]
    displayed = [r for r in table if r["Model"] in visible]
    render_section("The front-runners", "Overall comparison · broadly evaluated models")
    if table:
        leader = table[0]["Model"]
        agreement = sum(bool(t) and t[0]["Model"] == leader for t in details["tables"].values())
        source = details["source_checks"][method]
        cards = []
        for row in displayed[:3]:
            name = row["Model"]
            organisation = provider(name)
            strengths = [d for d in view.domain_weights if (t := domain_standings(view,d,method)) and t[0]["Model"] == name]
            line = "Leads " + ", ".join(strengths[:3]).lower() if strengths else "A broad contender across this portfolio"
            cards.append(f'<article class="model-card {"primary" if row["Rank"] == 1 else ""}" style="--model-accent:{ACCENTS[organisation]}"><div class="card-top"><span>{escape(organisation)} · {"Overall leader" if row["Rank"] == 1 else "Front-runner"}</span><span class="rank-orb">#{row["Rank"]}</span></div><h3>{escape(name)}</h3><p>{escape(line)}</p><div class="card-support"><span><b>{row["results"]}</b>results</span><span><b>{row["evaluators"]}</b>evaluators</span><span><b>{row["domains"]}/7</b>domains</span></div></article>')
        if cards:
            st.html('<div class="leader-grid">' + ''.join(cards) + '</div>')
        st.html(f'<div class="leader-note"><strong>{escape(leader)}</strong> leads under {agreement}/{len(METHODS)} weighting lenses and stays first in {source["first"]}/{source["scenarios"]} evaluator-removal checks using this lens.</div>')
        st.caption("More varied evidence makes this conclusion easier to stress-test. Removal counts describe sensitivity, not the probability that a model is best.")
    else:
        st.info("This release does not connect a broad comparison cohort. Explore the recorded results instead.")
    with st.expander("See the complete standings & comparison rules"):
        st.write("Broad cohort: at least 20 recorded results, 3 evaluator labels and 6 capability domains. These reporting thresholds are independent of score. Model filters only change displayed cards; they do not refit or rerank the cohort.")
        st.dataframe([dict(Rank=r["Rank"], Model=r["Model"], **{"Reference index":round(r["Index"],1), "Results":r["results"], "Evaluators":r["evaluators"], "Domains":r["domains"]}) for r in displayed], hide_index=True, width="stretch")
        st.caption("Reference index is an experimental summary with Opus = 100, not an intelligence percentage. Different task metrics use fixed scales. It describes these reported systems; task coverage and harnesses differ. Scores are not comparable across releases.")
        full = standings(view,view.models,method)
        if full:
            st.write("All-model experiment, including sparse contenders")
            st.dataframe([dict(Model=r["Model"], Rank=r["Rank"], **{"Reference index":round(r["Index"],1), "Results":r["results"], "Evaluators":r["evaluators"]}) for r in full], hide_index=True, width="stretch")
    sparse = [m for m in evidence.models if m not in details["cohort"] and m in visible]
    if sparse:
        st.html('<div class="contenders"><strong>Contenders to watch</strong> · ' + escape(' · '.join(f'{m}: {support(view,m)["results"]} results / {support(view,m)["evaluators"]} evaluators' for m in sparse)) + '<br>Promising results, with less evidence across the wider portfolio. Their all-model experiment is available above.</div>')

    render_section("Make it your frontier", "Choose a mission · challenge a ranking · compare rivals")
    task_tab, shake_tab, duel_tab = st.tabs(["Find my task specialist", "Shake the leaderboard", "Head-to-head"])
    with task_tab:
        task = st.selectbox("What do you want to do?", list(TASKS), key="explorer_task")
        domain,glyph,description = TASKS[task]
        ranks = domain_standings(view,domain,method)
        shown = [r for r in ranks if r["Model"] in visible]
        if ranks:
            winner = ranks[0]
            st.html(f'<div class="task-pick"><span class="task-icon">{glyph}</span><div><div class="mini-label">{escape(domain)} leader · {escape(method)}</div><h3>{escape(winner["Model"])}</h3><p>{escape(description)} · {winner["results"]} recorded results / {winner["evaluators"]} evaluator labels</p></div></div>')
            fig = go.Figure(go.Bar(y=[r["Model"] for r in reversed(shown)], x=[r["Index"]-winner["Index"] for r in reversed(shown)], orientation="h", marker_color=[accent(r["Model"]) for r in reversed(shown)], customdata=[[r["results"],r["evaluators"]] for r in reversed(shown)], hovertemplate="%{y}<br>Relative gap: %{x:.1f}<br>%{customdata[0]} results · %{customdata[1]} evaluators<extra></extra>"))
            fig.update_layout(xaxis_title="Relative index gap to this domain's leader", yaxis_title=None)
            st.plotly_chart(theme_plotly(fig,height=340), width="stretch", config={"displaylogo":False})
            st.caption("Within-domain fit among broad-cohort models with a recorded result in this domain. Missing results are omitted; an unavailable or disconnected model gets no inferred rank. Task and harness coverage varies.")
        else:
            st.info("No connected comparison is available for this domain.")
        with st.expander("Browse the tests behind this mission"):
            rows = [dict(Test=r.name, Evaluator=r.evaluator, Family=r.family, Source=r.source) for r in view.rows if r.domain == domain]
            st.dataframe(rows, hide_index=True, width="stretch", column_config={"Source":st.column_config.LinkColumn()})
    with shake_tab:
        st.write("Would the conclusion survive without one evaluator? Pull a source out and watch the order change.")
        removed = st.selectbox("Take one evaluator out", ["Keep everyone"] + sorted({r.evaluator for r in view.rows}), key="explorer_remove")
        ids = [i for i,r in enumerate(view.rows) if r.evaluator != removed]
        scenario = standings(view,details["cohort"],method,ids)
        baseline = {r["Model"]:r["Rank"] for r in table}
        if scenario:
            movements = []
            for row in scenario:
                if row["Model"] not in visible:
                    continue
                shift = baseline[row["Model"]] - row["Rank"]
                movement = "—" if shift == 0 else ("↑ " if shift > 0 else "↓ ") + str(abs(shift))
                movements.append(dict(Rank=row["Rank"], Model=row["Model"], Movement=movement,
                                      **{"Results left":row["results"], "Evaluators left":row["evaluators"]}))
            st.dataframe(movements, hide_index=True,width="stretch")
        else:
            st.info("This removal disconnects the comparison graph. A joint ranking would be unsupported.")
        family = details["family_checks"][method]
        st.caption(f'Family-removal checks: the baseline leader stays first in {family["first"]}/{family["scenarios"]}; {family.get("disconnected",0)} disconnected scenarios. The cohort and normalization scales stay fixed in every removal.')
    with duel_tab:
        available = [m for m in view.models if m in visible]
        if len(available) >= 2:
            left,right = st.columns(2)
            a = left.selectbox("In this corner",available,key="duel_a")
            b = right.selectbox("The challenger",available,index=1,key="duel_b")
            duel = comparison(view,a,b)
            if a == b:
                st.info("Choose two different models to start a comparison.")
            elif duel:
                wins_a = sum(r["Winner"] == a for r in duel)
                wins_b = sum(r["Winner"] == b for r in duel)
                st.write(f'**{a}** leads {wins_a} shared result rows · **{b}** leads {wins_b} · {len(duel)-wins_a-wins_b} ties')
                st.caption("Point-estimate row counts, not a probability of winning. Related executions and unequal task coverage make these counts descriptive.")
                chosen = st.selectbox("Arena", ["All domains"] + list(view.domain_weights),key="duel_domain")
                selected = [r for r in duel if chosen == "All domains" or r["Domain"] == chosen]
                if selected:
                    fig = go.Figure(go.Bar(y=[r["Benchmark"] for r in selected],x=[max(-2,min(2,r["Margin"])) for r in selected],orientation="h",marker_color=[COLORS[1] if r["Margin"] > 0 else COLORS[0] for r in selected],customdata=[[r["A"],r["B"],r["Domain"]] for r in selected],hovertemplate="%{y}<br>A: %{customdata[0]} · B: %{customdata[1]}<br>%{customdata[2]}<extra></extra>"))
                    fig.add_vline(x=0,line_color="#8693aa")
                    fig.update_layout(xaxis_title=f"← {b} leads | {a} leads → · normalized margin, clipped at ±2", yaxis_title=None)
                    st.plotly_chart(theme_plotly(fig,height=max(340,len(selected)*25+90)),width="stretch",config={"displaylogo":False})
                    with st.expander("Raw results & sources"):
                        st.dataframe(selected,hide_index=True,width="stretch",column_config={"Source":st.column_config.LinkColumn()})
                    st.download_button("Save this matchup",csv_export(selected),"frontier_matchup.csv","text/csv")
                else:
                    st.info("No shared recorded results in this arena.")
            else:
                st.info("These models have no shared recorded results.")
        else:
            st.info("Show at least two models to explore a matchup.")


def whats_new(evidence):
    added = [r for r in evidence.rows if r.id in {"B063","B064","B065","B066"}]
    if not added:
        st.info("This is a preserved earlier release. Select v5.4 to explore the expanded portfolio.")
        return
    st.html('<div class="leader-note"><strong>+3 families · +4 executions · +20 results.</strong> Beyond conventional reasoning tests: interactive 3D worlds, rare-disease diagnosis, wet-lab decisions and another coding-agent perspective.</div>')
    stories = [("◉","AA-3D","Create interactive 3D scenes. Human preferences rate eligible scenes."),("⌘","FrontierCode 1.1","Same Main task family, a new AA harness. Kept separate from Cognition's execution."),("✧","RareBench","Diagnose rare disease with complete causal recall across 122 cases."),("⌁","LabBench","Choose wet-lab actions across 20 held-out tasks. Rubric credit, not tasks solved.")]
    st.html('<div class="story-grid">' + ''.join(f'<article class="story-card"><span class="glyph">{icon}</span><h3>{title}</h3><p>{text}</p></article>' for icon,title,text in stories) + '</div>')
    render_section("Explore the new results", "Published scoreboard values · original metrics")
    selected_name = st.selectbox("Choose a new evaluation", [r.name for r in added],key="new_evaluation")
    selected = next(r for r in added if r.name == selected_name)
    rows = []
    for i,model in enumerate(evidence.models):
        if selected.scores[i] is not None:
            record = evidence.catalog.details(selected.id,model)
            interval = record["uncertainty"]["value"]
            rows.append(dict(Model=model, Result=selected.scores[i], Configuration=record["system"]["harness"], Status="EAP" if record["evidence_status"].startswith("provisional") else "Published", Interval=interval))
    rows.sort(key=lambda r:r["Result"])
    fig = go.Figure(go.Bar(y=[r["Model"] + (" · EAP" if r["Status"] == "EAP" else "") for r in rows],x=[r["Result"] for r in rows],orientation="h",marker_color=[accent(r["Model"]) for r in rows],text=[r["Result"] for r in rows],textposition="outside",error_x=dict(type="data",symmetric=False,array=[r["Interval"][1]-r["Result"] if r["Interval"] else 0 for r in rows],arrayminus=[r["Result"]-r["Interval"][0] if r["Interval"] else 0 for r in rows],color="#cdd8ec")))
    fig.update_layout(xaxis_title="Published preference Elo · 95% publisher intervals" if selected.unit == "elo" else "Published score (%)",yaxis_title=None)
    st.plotly_chart(theme_plotly(fig,height=390),width="stretch",config={"displaylogo":False})
    metadata = next(r for r in evidence.csv_rows("benchmarks.csv") if r["benchmark_id"] == selected.id)
    st.write(metadata["metric_definition"])
    if selected.id == "B063":
        st.caption("Sonnet has the highest point estimate in our roster; these intervals overlap substantially. This does not establish a clear statistical winner. Argon and both Muse Wonder identities are absent from the reviewed board.")
    if selected.id in {"B065","B066"}:
        st.caption("Argon was evaluated in EAP through Antigravity. Its public availability on 13 Oct does not certify that these earlier runs represent the public API.")
    st.link_button("Open the publisher's evaluation",selected.source)
    with st.expander("Run conditions, missing models & source records"):
        st.write(selected.config)
        st.dataframe(rows,hide_index=True,width="stretch")
        st.write("Not recorded:",", ".join(m for i,m in enumerate(evidence.models) if selected.scores[i] is None))
        st.json([evidence.catalog.details(selected.id,r["Model"]) for r in rows])
    render_section("Argon goes public", "Availability updated · historical scores preserved")
    st.write("Gemini 4 Argon is publicly available through the paid Gemini API / AI Studio, enterprise access and supported consumer subscriptions from 13 October 2026. The new AA FrontierCode row adds its 42.6% high-effort Stirrup result; AA-3D has no Argon result in the reviewed board.")
    st.link_button("Google's public model documentation","https://ai.google.dev/gemini-api/docs/models/gemini-4-argon")
    render_section("Are these already in AA's headline scores?", "Checked 14 Oct 2026")
    st.write("AA-3D and FrontierCode 1.1 are outside AA Intelligence Index v4.3.2's ten constituent evaluations. They are also outside Coding Agent Index v1.5's three constituents. Our portfolio includes the individual evaluations; the headline composites remain external context and are never added to the fit.")
    left,right = st.columns(2)
    left.link_button("AA Intelligence methodology","https://artificialanalysis.ai/methodology/intelligence-benchmarking")
    right.link_button("AA Coding Agent Index","https://artificialanalysis.ai/agents/coding-agents")
    render_section("Did the wider evidence change the order?", "v5.3 → v5.4 · same broad cohort · primary inclusion policy")
    before = product_evidence(Evidence(evidence.data_dir.parent / "v5_3"))
    current = product_evidence(evidence)
    lens = st.selectbox("Compare the releases through",list(METHODS),key="release_change_lens")
    changes = release_changes(before,current,broad_cohort(current),lens)
    if changes:
        leader = changes[0]
        st.write(f'**{leader["Model"]}** {"keeps the lead" if leader["Previous"] == 1 else "moves into the lead"}. Its primary comparison now includes {support(current,leader["Model"])["results"]} results from {support(current,leader["Model"])["evaluators"]} evaluator labels.')
        st.dataframe([dict(Model=r["Model"], **{"v5.3 rank":r["Previous"], "v5.4 rank":r["Current"], "Movement":"—" if r["Movement"] == 0 else ("↑ " if r["Movement"] > 0 else "↓ ") + str(abs(r["Movement"])), "New primary results":r["Added_results"]}) for r in changes],hide_index=True,width="stretch")
        st.caption("Ordinal changes under the same lens and cohort; reference index values are not compared across releases. Provisional EAP results are excluded here and can be explored with the homepage toggle.")
    st.caption("RareBench and LabBench are newly added here, rather than newly published today. All four additions predate the public forecast registration and stay outside the prospective outcome ledger.")
