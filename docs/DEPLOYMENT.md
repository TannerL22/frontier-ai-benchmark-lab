# Verification and deployment

The existing Streamlit entry point remains `app.py`. `requirements.txt` loads the complete `requirements-lock.txt` resolution. Use Python 3.12 for the declared Linux CI/deployment check, or the locally exercised Python 3.14.2 environment. The editable project supports Python 3.11+. Direct pins are also available in `constraints.txt`; updating any resolution requires a new clean install and checks. Starlette 0.49.3 is explicitly constrained: the unconstrained 1.8.0 resolver result changed response ordering used by Streamlit 1.57 media middleware. An HTTP-protocol regression test covers both gzip and identity media responses.

Before release, run:

```bash
python -m pip install -r requirements-lock.txt
python -m pip check
python scripts/check_release.py
python scripts/prospective_study.py verify
python scripts/prospective_registry.py verify
python -m pytest -q
python scripts/reproduce.py --calibration
python scripts/reproduce_v51.py
python scripts/reproduce_v52.py
python scripts/reproduce_v53.py
python scripts/app_smoke.py
python scripts/artifact_pilot.py oracle-demo
```

Local Windows checks place test temporary files in the workspace (`pytest --basetemp=.test-tmp-unique`) to avoid sandbox cleanup restrictions. The app smoke script exercises 21 page/release combinations and four material interactions. CI archives outputs and the clearly labelled free oracle demonstration for 90 days; retain milestone artifacts separately when longer preservation is needed.

For a preview, run `streamlit run app.py --server.address 127.0.0.1`. Review the draft branch and merge only after source/scientific decisions are accepted. An existing Streamlit deployment tracking main may redeploy upon merge; preparing a branch or pull request does not itself change the live app. No provider secrets or paid runs are required. This change does not create a monitoring automation or claim a deployment-security audit.
