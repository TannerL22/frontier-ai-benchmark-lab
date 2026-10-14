"""Exercise all pages/releases and material empty-selection branches."""
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    temporary = ROOT / ".smoke-tmp"
    temporary.mkdir(exist_ok=True)
    tempfile.tempdir = str(temporary)
    os.environ["TMP"] = str(temporary)
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90).run()
    results = []
    def record(version, page):
        exceptions = [str(x.value) for x in app.exception]
        results.append({"release": version, "page": page, "exceptions": exceptions})
        if exceptions:
            raise AssertionError(f"{version}/{page}: {exceptions}")
    for version in app.sidebar.radio[0].options:
        app.sidebar.radio[0].set_value(version).run()
        for page in app.sidebar.radio[1].options:
            app.sidebar.radio[1].set_value(page).run()
            record(version, page)
    app.sidebar.radio[0].set_value(app.sidebar.radio[0].options[0]).run()
    latest = app.sidebar.radio[0].value
    app.sidebar.radio[1].set_value("Frontier explorer").run()
    app.selectbox[0].set_value("Equal domains").run()
    app.toggle[0].set_value(True).run()
    next(x for x in app.selectbox if x.label == "Take one evaluator out").set_value("AA").run()
    record(latest, "Explorer weighting, EAP and source removal")
    a = next(x for x in app.selectbox if x.label == "In this corner")
    next(x for x in app.selectbox if x.label == "The challenger").set_value(a.value).run()
    assert any("two different" in element.value for element in app.info)
    record(latest, "Explorer identical duel")
    app.sidebar.radio[1].set_value("What’s new").run()
    app.selectbox[0].select_index(2).run()
    record(latest, "New science evaluation")
    next(x for x in app.selectbox if x.label == "Compare the releases through").set_value("Equal domains").run()
    record(latest, "Matched-cohort release change")
    app.sidebar.radio[1].set_value("Aggregation experiments").run()
    app.checkbox[0].check().run()
    app.checkbox[2].check().run()
    app.selectbox[0].set_value("Super-Aggregate v4.2").run()
    record(latest, "Global advanced experiment")
    app.multiselect[0].set_value([]).run()
    assert any("cannot identify" in element.value for element in app.info)
    record(latest, "Empty portfolio")
    app.sidebar.radio[1].set_value("Compare recorded results").run()
    app.selectbox[1].set_value(app.selectbox[0].value).run()
    assert any("two different" in element.value for element in app.info)
    record(latest, "Identical pair")
    app.sidebar.radio[1].set_value("Validation").run()
    app.selectbox[0].set_value("Evaluator").run()
    record(latest, "Evaluator abstentions")
    output = ROOT / "outputs/app_smoke.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Passed {len(results)} app page/release and interaction checks")


if __name__ == "__main__":
    main()
