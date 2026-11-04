"""Checks on the Power BI project (powerbi/).

Power BI Desktop isn't available here, so these tests check what can be checked without it:
- every PBIP/PBIR JSON file validates against Microsoft's published schema (vendored copies in
  reference/powerbi-schemas, fetched from developer.microsoft.com/json-schemas/fabric);
- the TMDL model is internally consistent: tab indentation, referenced tables exist, relationship
  columns exist, every Table[column] and [measure] used in DAX exists;
- every field a visual binds to exists in the model;
- the CSVs the model loads have exactly the columns the model declares.
"""
import csv
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
SM = PBI / "TariffComparison.SemanticModel" / "definition"
RP = PBI / "TariffComparison.Report"
SCHEMAS = ROOT / "reference" / "powerbi-schemas"
PREFIX = "https://developer.microsoft.com/json-schemas/fabric/"


def _registry():
    resources = []
    for f in SCHEMAS.rglob("schema.json"):
        uri = PREFIX + f.relative_to(SCHEMAS).as_posix()
        resources.append((uri, Resource.from_contents(json.loads(f.read_text()))))
    return Registry().with_resources(resources)


REGISTRY = _registry()


def parse_model():
    """Minimal TMDL reader: tables -> columns, measures (with DAX), partition source text."""
    tables = {}
    for f in sorted((SM / "tables").glob("*.tmdl")):
        text = f.read_text()
        name = re.match(r"table (?:'([^']+)'|(\S+))", text).group(1) or re.match(r"table (\S+)", text).group(1)
        cols = re.findall(r"^\tcolumn (?:'([^']+)'|(\S+))", text, re.M)
        cols = [a or b for a, b in cols]
        measures = {}
        for m in re.finditer(r"^\tmeasure (?:'([^']+)'|(\S+)) =(.*?)(?=^\t\t[a-zA-Z]+:|^\t\S|\Z)", text, re.M | re.S):
            measures[m.group(1) or m.group(2)] = m.group(3)
        tables[name] = {"columns": cols, "measures": measures, "text": text, "file": f}
    return tables


class Schemas(unittest.TestCase):
    def test_all_json_files_validate(self):
        files = [p for p in PBI.rglob("*") if p.is_file() and (p.suffix in (".json", ".pbir", ".pbism", ".pbip") or p.name == ".platform")
                 and "data" not in p.relative_to(PBI).parts and "StaticResources" not in p.parts]
        self.assertGreater(len(files), 15)
        for f in files:
            with self.subTest(file=str(f.relative_to(PBI))):
                doc = json.loads(f.read_text())
                self.assertIn("$schema", doc)
                schema = REGISTRY.get_or_retrieve(doc["$schema"]).value.contents
                errors = sorted(Draft7Validator(schema, registry=REGISTRY).iter_errors(doc), key=str)
                self.assertEqual([], [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors])

    def test_pbir_and_pbism_versions_select_text_formats(self):
        # definition.pbir 4.0 = PBIR report folder; definition.pbism 4.0 = TMDL model folder
        self.assertEqual(json.loads((RP / "definition.pbir").read_text())["version"], "4.0")
        self.assertEqual(json.loads((SM.parent / "definition.pbism").read_text())["version"], "4.0")

    def test_theme_registered(self):
        report = json.loads((RP / "definition" / "report.json").read_text())
        name = report["themeCollection"]["customTheme"]["name"]
        self.assertTrue((RP / "StaticResources" / "RegisteredResources" / name).exists())


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = parse_model()

    def test_indentation_is_tabs(self):
        # structure is indented with tabs; spaces may only follow the tabs (inside M/DAX bodies)
        for f in SM.rglob("*.tmdl"):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if line.strip():
                    with self.subTest(file=f.name, line=i):
                        self.assertRegex(line, r"^\t* *\S")

    def test_model_refs_match_table_files(self):
        refs = re.findall(r"^ref table (?:'([^']+)'|(\S+))", (SM / "model.tmdl").read_text(), re.M)
        self.assertEqual(sorted(a or b for a, b in refs), sorted(self.tables))

    def test_relationship_columns_exist(self):
        for ft, fc, tt, tc in re.findall(r"fromColumn: (\w+)\.(\w+)\n\ttoColumn: (\w+)\.(\w+)", (SM / "relationships.tmdl").read_text()):
            self.assertIn(fc, self.tables[ft]["columns"])
            self.assertIn(tc, self.tables[tt]["columns"])

    def test_dax_references_exist(self):
        all_measures = {m for t in self.tables.values() for m in t["measures"]}
        for tname, t in self.tables.items():
            for mname, dax in t["measures"].items():
                with self.subTest(measure=mname):
                    for tab, c in re.findall(r"(?:'([^']+)'|\b([A-Za-z_]\w*))\[([^\]]+)\]", dax) and \
                            [((a or b), c) for a, b, c in re.findall(r"(?:'([^']+)'|\b([A-Za-z_]\w*))\[([^\]]+)\]", dax)]:
                        self.assertIn(tab, self.tables, f"table {tab}")
                        self.assertIn(c, self.tables[tab]["columns"], f"{tab}[{c}]")
                    for ref in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", dax):
                        self.assertIn(ref, all_measures, f"[{ref}]")

    def test_csv_headers_match_declared_columns(self):
        for tname, t in self.tables.items():
            m = re.search(r'DataLocation & "([\w.]+\.csv)"', t["text"])
            if not m:
                continue
            with open(PBI / "data" / m.group(1)) as fh:
                header = next(csv.reader(fh))
            with self.subTest(table=tname):
                self.assertEqual(header, t["columns"])

    def test_default_data_location_matches_repo_layout(self):
        text = (SM / "expressions.tmdl").read_text()
        self.assertIn("/main/powerbi/data/", text)


class ReportBindings(unittest.TestCase):
    def test_visual_fields_exist_in_model(self):
        tables = parse_model()
        visuals = list((RP / "definition" / "pages").rglob("visual.json"))
        self.assertGreaterEqual(len(visuals), 7)
        for v in visuals:
            doc = json.loads(v.read_text())
            fields = []

            def walk(o):
                if isinstance(o, dict):
                    for kind in ("Column", "Measure"):
                        if kind in o and "Property" in o[kind]:
                            fields.append((kind, o[kind]["Expression"]["SourceRef"]["Entity"], o[kind]["Property"]))
                    for x in o.values():
                        walk(x)
                elif isinstance(o, list):
                    for x in o:
                        walk(x)
            walk(doc)
            self.assertTrue(fields, v)
            for kind, ent, prop in fields:
                with self.subTest(visual=v.parent.name, field=f"{ent}.{prop}"):
                    self.assertIn(ent, tables)
                    pool = tables[ent]["columns"] if kind == "Column" else tables[ent]["measures"]
                    self.assertIn(prop, pool)

    def test_visual_positions_fit_page(self):
        for page in (RP / "definition" / "pages").iterdir():
            if not page.is_dir():
                continue
            p = json.loads((page / "page.json").read_text())
            for v in page.rglob("visual.json"):
                pos = json.loads(v.read_text())["position"]
                with self.subTest(visual=v.parent.name):
                    self.assertLessEqual(pos["x"] + pos["width"], p["width"])
                    self.assertLessEqual(pos["y"] + pos["height"], p["height"])


if __name__ == "__main__":
    unittest.main()
