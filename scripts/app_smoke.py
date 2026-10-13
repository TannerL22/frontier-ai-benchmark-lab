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
    app.sidebar.radio[1].set_value("Aggregation experiments").run()
    app.checkbox[0].check().run()
    app.checkbox[2].check().run()
    app.selectbox[0].set_value("Super-Aggregate v4.2").run()
    record("v5.2", "Global advanced experiment")
    app.multiselect[0].set_value([]).run()
    assert any("cannot identify" in element.value for element in app.info)
    record("v5.2", "Empty portfolio")
    app.sidebar.radio[1].set_value("Compare recorded results").run()
    app.selectbox[1].set_value(app.selectbox[0].value).run()
    assert any("two different" in element.value for element in app.info)
    record("v5.2", "Identical pair")
    app.sidebar.radio[1].set_value("Validation").run()
    app.selectbox[0].set_value("Evaluator").run()
    record("v5.2", "Evaluator abstentions")
    output = ROOT / "outputs/app_smoke.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Passed {len(results)} app page/release and interaction checks")


if __name__ == "__main__":
    main()
