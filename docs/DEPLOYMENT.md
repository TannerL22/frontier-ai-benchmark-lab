# Deploy the interactive app

## Recommended: Streamlit Community Cloud

The app includes Python calculations, SciPy and a Streamlit server. GitHub Pages serves static assets and **cannot run a Python server**. Streamlit Community Cloud is the suitable low-maintenance deployment choice.

1. Sign in at **https://share.streamlit.io** with GitHub.
2. Select **Create app** → **I have an app**.
3. Enter repository `TannerL22/frontier-ai-benchmark-lab`, branch `main`, entrypoint `app.py`.
4. Optionally select a memorable public subdomain.
5. Deploy. The root-level `requirements.txt` installs `frontierlab`, `streamlit` and `plotly`.

The app is a public research dashboard if deployed publicly. **Do not add private API keys or unpublished datasets to tracked files.** Community Cloud supports a private secrets interface if required later.

### Verification

Run locally before deployment:

```bash
python -m pip install -e '.[app,dev]'
python -m pytest -q -m 'not slow'
python scripts/reproduce_v51.py
streamlit run app.py
```

If deployment fails, inspect the Community Cloud application logs. In particular, verify that `frontierlab` imports correctly: the `-e .` line in `requirements.txt` installs the package from `src/`.

### What about GitHub Pages?

Pages can host a **separate static summary, methodology guide or precomputed read-only chart**. It cannot host the interactive Python scoring/cross-validation engine. We deliberately avoid maintaining a second static leaderboard until there is a reliable export-and-publish pipeline to prevent stale or contradictory rankings.

## GitHub Actions

`.github/workflows/ci.yml` checks package installation, unit tests, and reproduction from both data releases on each push and pull request. GitHub actions are not a substitute for Streamlit hosting.

Read: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
