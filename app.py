"""Frontier AI Benchmark Lab v5.1 interactive dashboard.

Local launch: pip install -e '.[app,dev]' && streamlit run app.py
"""
from pathlib import Path
from io import StringIO
import csv
import numpy as np
import streamlit as st
import plotly.express as px
from frontierlab.core import Evidence, METHODS

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Frontier AI Benchmark Lab', page_icon='📊', layout='wide')

@st.cache_resource
def load_data(version):
    directory=ROOT/'data'/('v5_1' if version=='v5.1 · Eight-model expansion' else '')
    return Evidence(directory)

@st.cache_data
def validation(mode):
    frozen=load_data('v4.2 · Frozen six-model benchmark')
    return frozen.cv_pairs(mode)

st.sidebar.title('Frontier AI Lab')
version=st.sidebar.radio('Evidence release',['v5.1 · Eight-model expansion','v4.2 · Frozen six-model benchmark'])
ev=load_data(version)
method=st.sidebar.selectbox('Ranking method',METHODS,index=0)
page=st.sidebar.radio('Workspace',['Leaderboard','Matched model comparisons','Evidence explorer','Methodology validation','Muse release audit'])
st.sidebar.caption('The original six-model reference is frozen. v5.1 is an independent-scores-only expansion; all models use published best-available settings, not standardised compute.')

if page=='Leaderboard':
    st.title('Frontier AI Benchmark Lab')
    st.caption('Release: '+version+' | Relative score anchored at Opus 5.5 = 100, NOT percent intelligence')
    scores=ev.index(ev.all_fit(method))
    sorted_scores=sorted(scores.items(),key=lambda x:-x[1])
    metrics=st.columns(4)
    metrics[0].metric('Model variants',len(ev.models))
    metrics[1].metric('Underlying benchmark rows',len(ev.rows))
    metrics[2].metric('Unique benchmark families',len(ev.families))
    metrics[3].metric('Original evaluators',len(ev.evaluators))
    chart_data=[{'Model':m,'Score':sc} for m,sc in sorted_scores]
    fig=px.bar(chart_data,x='Score',y='Model',orientation='h',text='Score')
    fig.update_traces(texttemplate='%{x:.2f}',textposition='outside')
    fig.update_layout(yaxis={'categoryorder':'total ascending'},height=460,margin=dict(l=0,r=45,t=15,b=0))
    fig.update_xaxes(range=[min(scores.values())-4,max(scores.values())+5],title='Relative score (arbitrary reference scale)')
    st.plotly_chart(fig,use_container_width=True)
    rows=[]
    for i,(model,value) in enumerate(sorted_scores,1):
        j=ev.models.index(model)
        used=[b for b in ev.rows if b.scores[j] is not None]
        rows.append({'Position':i,'Model':model,'Index score':round(value,3),'Observed benchmarks':len(used),
                     'Distinct evaluators':len({b.evaluator for b in used}),
                     'Evidence status':'Launch-day limited coverage' if model.startswith('Muse Wonder') else 'Historical multi-evaluator evidence'})
    st.dataframe(rows,hide_index=True,use_container_width=True)
    if len(ev.models)==8:
        st.warning('New Muse models have exactly 10 independent AA tests each, and no verified scores from the other 8 evaluator groups yet. Their rankings can move sharply as additional independent evidence arrives. Equal-budget performance is not established.')
    st.info('All methods are compared with the same underlying scores. The eight-model index is REFITTED using additional observations and is not numerically interchangeable with the frozen six-model index.')

elif page=='Matched model comparisons':
    st.title('Head-to-head evidence')
    c1,c2=st.columns(2)
    a=c1.selectbox('Model A',ev.models,index=0)
    b=c2.selectbox('Model B',ev.models,index=len(ev.models)-1)
    if a==b:
        st.warning('Select two different models.')
    else:
        i,j=ev.models.index(a),ev.models.index(b)
        rows=[]
        for x in ev.rows:
            if x.scores[i] is None or x.scores[j] is None:continue
            rows.append({'Benchmark':x.name,'Evaluator':x.evaluator,'Domain':x.domain,'Family':x.family,
                         f'{a} score':x.scores[i],f'{b} score':x.scores[j],'Raw units':x.unit,
                         'Standardised B − A':float((x.scores[j]-x.scores[i])/x.denominator),
                         'Original source':x.source,'Configuration':x.config})
        st.metric('Mutually evaluated benchmark rows',len(rows))
        if rows:
            st.dataframe(sorted(rows,key=lambda x:x['Standardised B − A']),hide_index=True,use_container_width=True,
                         column_config={'Original source':st.column_config.LinkColumn()})
            stream=StringIO();wr=csv.DictWriter(stream,fieldnames=rows[0].keys());wr.writeheader();wr.writerows(rows)
            st.download_button('Download matched evidence (CSV)',stream.getvalue(),file_name='model_comparison.csv',mime='text/csv')
        if a.startswith('Muse Wonder') or b.startswith('Muse Wonder'):
            st.caption('All currently matched tests involving Muse variants originate from Artificial Analysis; they are not independent publisher confirmations.')

elif page=='Evidence explorer':
    st.title('Benchmark provenance explorer')
    domains=sorted({r.domain for r in ev.rows})
    evaluators=sorted({r.evaluator for r in ev.rows})
    selected_domains=st.multiselect('Capability domains',domains,default=domains)
    selected_evaluators=st.multiselect('Evaluators',evaluators,default=evaluators)
    rows=[{'ID':r.id,'Benchmark':r.name,'Family':r.family,'Original evaluator':r.evaluator,'Domain':r.domain,
           'Model coverage':sum(x is not None for x in r.scores),'Unit':r.unit,'Run configuration':r.config,
           'Source URL':r.source,'Provenance / caveats':r.provenance,'Overlap notes':r.overlap_notes}
          for r in ev.rows if r.domain in selected_domains and r.evaluator in selected_evaluators]
    st.dataframe(rows,hide_index=True,use_container_width=True,column_config={'Source URL':st.column_config.LinkColumn()})
    if len(ev.models)==8:
        st.subheader('New Meta observations')
        p=ROOT/'data'/'v5_1'/'source_audit.csv'
        with p.open(newline='') as f: st.dataframe(list(csv.DictReader(f)),hide_index=True,use_container_width=True,
            column_config={'source_url':st.column_config.LinkColumn()})

elif page=='Methodology validation':
    st.title('Held-out prediction methodology')
    st.caption('The historically cross-validated six-model v4.2 dataset is used here, unchanged. New Muse models were NOT part of those held-out validation studies.')
    frozen=load_data('v4.2 · Frozen six-model benchmark')
    mode=st.selectbox('Leave-one-group-out',['family','evaluator','domain'])
    threshold=st.selectbox('Exclude observed differences up to these normalized units',[0.,0.10,0.25])
    recs=validation(mode)
    results=[]
    for method_name in METHODS:
        metrics=frozen.macro_accuracy(recs,mode,method_name,threshold)
        results.append({'Method':method_name,'Macro directional accuracy':metrics['macro'],
                        'Held-out comparisons':metrics['pair_count'],'Held-out groups':metrics['fold_count']})
    st.plotly_chart(px.bar(results,x='Method',y='Macro directional accuracy',range_y=[0,1],text_auto='.1%'),use_container_width=True)
    st.dataframe(results,hide_index=True,use_container_width=True)
    st.info('These are retrospective group-holdouts, not prospective proof that a method can predict the next model release.')

elif page=='Muse release audit':
    st.title('Muse Wonder / Wonder Full · 12 October 2026')
    st.markdown('Two verified Meta model identities, separate from historical GPT and Claude variants.')
    st.subheader('Original benchmark data')
    latest=load_data('v5.1 · Eight-model expansion')
    aa=[r for r in latest.rows if r.evaluator=='AA']
    tab=[]
    for r in aa:
        idx1=latest.models.index('Muse Wonder Full');idx2=latest.models.index('Muse Wonder')
        tab.append({'Underlying AA evaluation':r.name,'Wonder Full':r.scores[idx1], 'Wonder':r.scores[idx2],
                    'Metric':r.unit,'Original publisher':r.evaluator,'Benchmark family':r.family})
    st.dataframe(tab,hide_index=True,use_container_width=True)
    st.subheader('Composite scores — for external comparison only')
    aa_external=[x for x in latest.external if x['publisher']=='Artificial Analysis' and x['metric'].startswith('Intelligence Index')]
    st.dataframe(sorted(aa_external,key=lambda x:-float(x['score'])),hide_index=True,use_container_width=True,
                 column_config={'source_url':st.column_config.LinkColumn()})
    st.warning('The Artificial Analysis Intelligence Index and Coding Agents Index are NEVER inserted as benchmark observations. Meta self-evaluated claims are not input scores. SciCode and CritPt are under review by AA.')
    st.markdown('[Primary AA analysis](https://artificialanalysis.ai/articles/muse-wonder) · [Meta model release](https://research.meta.ai/blog/muse-wonder)')
