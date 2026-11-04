"""Write the Power BI Project (PBIP) in powerbi/: a TMDL semantic model and a PBIR report.

PBIP is Power BI Desktop's text-based project format (open TariffComparison.pbip in Desktop).
The JSON files are validated against Microsoft's published schemas by tests/test_powerbi.py.
Data comes from powerbi/data/*.csv (scripts/build_powerbi_data.py); the DataLocation parameter
points at those files, either a URL (default: this repository on GitHub) or a local folder.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
NAME = "TariffComparison"
SM = PBI / f"{NAME}.SemanticModel"
RP = PBI / f"{NAME}.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
DEFAULT_DATA = "https://raw.githubusercontent.com/geethan-sannidhi/residential-rate-tariff-comparison/main/powerbi/data/"
NS = uuid.UUID("6f1d4c1e-3b0a-4f6e-9a57-2f1c0b7d9e10")
T = "\t"


def gid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def wjson(path, obj):
    write(path, json.dumps(obj, indent=2) + "\n")


# ------------------------------------------------------------------ semantic model (TMDL)
def m_csv(file, types):
    """Power Query (M) that reads one CSV from DataLocation (URL or local folder)."""
    tlist = ", ".join(f'{{"{c}", {t}}}' for c, t in types)
    lines = [
        "let",
        f'    Raw = if Text.StartsWith(DataLocation, "http") then Web.Contents(DataLocation & "{file}") else File.Contents(DataLocation & "{file}"),',
        '    Source = Csv.Document(Raw, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{tlist}}}, "en-US")',
        "in",
        "    Typed",
    ]
    return lines


M_TYPE = {"string": "type text", "int64": "Int64.Type", "double": "type number", "boolean": "type logical"}


def table_tmdl(name, columns, partition_m, measures=(), hidden=(), sort_by=None, fmt=None):
    """columns: list of (name, dataType). Returns TMDL text for one table."""
    q = (lambda s: f"'{s}'" if (" " in s or not s.isidentifier()) else s)
    out = [f"table {q(name)}", f"{T}lineageTag: {gid('table', name)}", ""]
    for mname, expr, mfmt, desc in measures:
        body = expr.strip().splitlines()
        if desc:
            out.append(f"{T}/// {desc}")
        if len(body) == 1:
            out.append(f"{T}measure {q(mname)} = {body[0]}")
        else:
            out.append(f"{T}measure {q(mname)} =")
            out += [f"{T * 3}{ln}" for ln in body]
        if mfmt:
            out.append(f"{T * 2}formatString: {mfmt}")
        out.append(f"{T * 2}lineageTag: {gid('measure', name, mname)}")
        out.append("")
    for cname, dtype in columns:
        out.append(f"{T}column {q(cname)}")
        out.append(f"{T * 2}dataType: {dtype}")
        if fmt and cname in fmt:
            out.append(f"{T * 2}formatString: {fmt[cname]}")
        if cname in hidden:
            out.append(f"{T * 2}isHidden")
        out.append(f"{T * 2}lineageTag: {gid('column', name, cname)}")
        out.append(f"{T * 2}summarizeBy: none")
        out.append(f"{T * 2}sourceColumn: {cname}")
        if sort_by and cname in sort_by:
            out.append(f"{T * 2}sortByColumn: {sort_by[cname]}")
        out.append("")
    out.append(f"{T}partition {q(name)} = m")
    out.append(f"{T * 2}mode: import")
    out.append(f"{T * 2}source =")
    out += [f"{T * 4}{ln}" for ln in partition_m]
    out.append("")
    return "\n".join(out) + "\n"


def build_model():
    write(SM / "definition" / "database.tmdl", f"database {NAME}\n{T}compatibilityLevel: 1567\n")
    tables = ["Utilities", "Bills", "Components", "Months", "Usage Level", "Validation"]
    q = (lambda s: f"'{s}'" if " " in s else s)
    write(SM / "definition" / "model.tmdl", "\n".join([
        "model Model",
        f"{T}culture: en-US",
        f"{T}defaultPowerBIDataSourceVersion: powerBI_V3",
        f"{T}sourceQueryCulture: en-US",
        f"{T}dataAccessOptions",
        f"{T * 2}legacyRedirects",
        f"{T * 2}returnErrorValuesAsNull",
        "",
        *[f"ref table {q(t)}" for t in tables],
        "",
    ]))
    write(SM / "definition" / "expressions.tmdl", "\n".join([
        f'expression DataLocation = "{DEFAULT_DATA}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"{T}lineageTag: {gid('expression', 'DataLocation')}",
        "",
        f"{T}annotation PBI_ResultType = Text",
        "",
    ]))

    util_cols = [("tariff_key", "string"), ("utility", "string"), ("short_name", "string"), ("schedule", "string"),
                 ("type", "string"), ("jurisdiction", "string"), ("effective", "string"), ("seasonal", "boolean"),
                 ("demand_level_charge", "boolean"), ("tiered", "boolean"), ("source_1", "string")]
    write(SM / "definition" / "tables" / "Utilities.tmdl", table_tmdl(
        "Utilities", util_cols, m_csv("utilities.csv", [(c, M_TYPE[t]) for c, t in util_cols]),
        hidden={"tariff_key"}))

    bill_cols = [("tariff_key", "string"), ("kwh", "int64"), ("month", "int64"), ("total_bill", "double"),
                 ("customer_charge", "double"), ("demand_level_charge", "double"), ("energy_non_fuel", "double"),
                 ("fuel", "double"), ("other_clauses", "double"), ("minimum_adjustment", "double")]
    money = r"\$#,0.00"
    measures = [
        ("Monthly Bill", "AVERAGE ( Bills[total_bill] )", money,
         "Average monthly bill across the months in context. With no month filter this is the 12-month average, which matters for Duke's seasonal rates."),
        ("Selected kWh", "SELECTEDVALUE ( 'Usage Level'[kWh], 1000 )", "#,0",
         "Usage chosen in the Usage Level slicer; 1,000 kWh when nothing or several values are selected."),
        ("Bill at Selected Usage", "\n".join([
            "VAR k = [Selected kWh]",
            "RETURN",
            "    CALCULATE ( [Monthly Bill], Bills[kwh] = k )"]), money, "Monthly bill at the usage chosen in the slicer."),
        ("Cents per kWh at Selected Usage", "\n".join([
            "VAR k = [Selected kWh]",
            "RETURN",
            "    IF ( k > 0, DIVIDE ( [Bill at Selected Usage], k ) * 100 )"]), "0.00", "All-in cents per kWh at the selected usage."),
        ("Lowest Bill at Selected Usage", "MINX ( ALLSELECTED ( Utilities[utility] ), [Bill at Selected Usage] )", money,
         "Lowest bill among the utilities currently shown."),
        ("Difference vs Lowest", "\n".join([
            "IF (",
            "    HASONEVALUE ( Utilities[utility] ),",
            "    [Bill at Selected Usage] - [Lowest Bill at Selected Usage]",
            ")"]), money, "How much more this utility's bill is than the lowest one shown."),
        ("Rank (1 = lowest)", "\n".join([
            "IF (",
            "    HASONEVALUE ( Utilities[utility] ),",
            "    RANKX ( ALLSELECTED ( Utilities[utility] ), [Bill at Selected Usage], , ASC, DENSE )",
            ")"]), "0", None),
        ("Fuel Share at Selected Usage", "\n".join([
            "VAR k = [Selected kWh]",
            "RETURN",
            "    DIVIDE ( CALCULATE ( AVERAGE ( Bills[fuel] ), Bills[kwh] = k ), [Bill at Selected Usage] )"]),
         "0.0%", "Share of the bill that is fuel or purchased-power cost."),
    ]
    write(SM / "definition" / "tables" / "Bills.tmdl", table_tmdl(
        "Bills", bill_cols, m_csv("bills.csv", [(c, M_TYPE[t]) for c, t in bill_cols]), measures=measures,
        hidden={"tariff_key", "month"}, fmt={"kwh": "#,0"}))

    comp_cols = [("tariff_key", "string"), ("kwh", "int64"), ("month", "int64"), ("component", "string"), ("amount", "double")]
    comp_measures = [("Component at Selected Usage", "\n".join([
        "VAR k = [Selected kWh]",
        "RETURN",
        "    DIVIDE (",
        "        CALCULATE ( SUM ( Components[amount] ), Components[kwh] = k ),",
        "        CALCULATE ( DISTINCTCOUNT ( Components[month] ), Components[kwh] = k )",
        "    )"]), money, "Average monthly dollars for each bill component at the selected usage.")]
    write(SM / "definition" / "tables" / "Components.tmdl", table_tmdl(
        "Components", comp_cols, m_csv("components.csv", [(c, M_TYPE[t]) for c, t in comp_cols]),
        measures=comp_measures, hidden={"tariff_key", "month", "kwh"}))

    months_m = [
        "let",
        '    Names = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"},',
        '    Rows = List.Transform({1..12}, each {_, Names{_ - 1}, if List.Contains({12, 1, 2}, _) then "Winter (Dec-Feb)" else "Mar-Nov"}),',
        "    Result = #table(type table [month = Int64.Type, month_name = text, season = text], Rows)",
        "in",
        "    Result",
    ]
    write(SM / "definition" / "tables" / "Months.tmdl", table_tmdl(
        "Months", [("month", "int64"), ("month_name", "string"), ("season", "string")], months_m,
        hidden={"month"}, sort_by={"month_name": "month"}))

    usage_m = [
        "let",
        "    Result = #table(type table [kWh = Int64.Type], List.Transform({0..60}, each {_ * 50}))",
        "in",
        "    Result",
    ]
    write(SM / "definition" / "tables" / "Usage Level.tmdl", table_tmdl(
        "Usage Level", [("kWh", "int64")], usage_m, fmt={"kWh": "#,0"}))

    val_cols = [("tariff_key", "string"), ("kwh", "int64"), ("calculator", "double"), ("published", "double"),
                ("difference", "double"), ("source", "string"), ("note", "string")]
    write(SM / "definition" / "tables" / "Validation.tmdl", table_tmdl(
        "Validation", val_cols, m_csv("validation.csv", [(c, M_TYPE[t]) for c, t in val_cols]),
        hidden={"tariff_key"}, fmt={"calculator": money, "published": money, "difference": money, "kwh": "#,0"}))

    rels = [("Bills", "tariff_key", "Utilities", "tariff_key"), ("Components", "tariff_key", "Utilities", "tariff_key"),
            ("Validation", "tariff_key", "Utilities", "tariff_key"), ("Bills", "month", "Months", "month"),
            ("Components", "month", "Months", "month")]
    rel_txt = []
    for ft, fc, tt, tc in rels:
        rel_txt += [f"relationship {gid('rel', ft, fc, tt, tc)}", f"{T}fromColumn: {ft}.{fc}", f"{T}toColumn: {tt}.{tc}", ""]
    write(SM / "definition" / "relationships.tmdl", "\n".join(rel_txt))

    wjson(SM / "definition.pbism", {"$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
                                    "version": "4.0", "settings": {}})
    wjson(SM / ".platform", {"$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
                             "metadata": {"type": "SemanticModel", "displayName": NAME},
                             "config": {"version": "2.0", "logicalId": gid("logical", "model")}})


# ------------------------------------------------------------------ report (PBIR)
def col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas(entity, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def proj(field, display=None):
    kind = "Column" if "Column" in field else "Measure"
    e, p = field[kind]["Expression"]["SourceRef"]["Entity"], field[kind]["Property"]
    out = {"field": field, "queryRef": f"{e}.{p}", "nativeQueryRef": p}
    if display:
        out["displayName"] = display
    return out


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def title(text):
    return {"title": [{"properties": {"show": lit("true"), "text": lit("'" + text.replace("'", "''") + "'")}}]}


def visual(page, name, vtype, x, y, w, h, roles, titletext=None, sort=None, objects=None, z=0):
    v = {"visualType": vtype, "query": {"queryState": {r: {"projections": ps} for r, ps in roles.items()}},
         "drillFilterOtherVisuals": True}
    if sort:
        v["query"]["sortDefinition"] = {"sort": sort, "isDefaultSort": False}
    if objects:
        v["objects"] = objects
    if titletext:
        v["visualContainerObjects"] = title(titletext)
    wjson(RP / "definition" / "pages" / page / "visuals" / name / "visual.json", {
        "$schema": f"{SCHEMA}/item/report/definition/visualContainer/1.0.0/schema.json",
        "name": name, "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z}, "visual": v})


def build_report():
    wjson(RP / "definition.pbir", {"$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
                                   "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    wjson(RP / ".platform", {"$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
                             "metadata": {"type": "Report", "displayName": NAME},
                             "config": {"version": "2.0", "logicalId": gid("logical", "report")}})
    wjson(RP / "definition" / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                                               "version": "1.0.0"})
    theme = "TariffTheme.json"
    wjson(RP / "definition" / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {"customTheme": {"name": theme, "reportVersionAtImport": "5.59", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": theme, "path": theme, "type": "CustomTheme"}]}],
    })
    # Validated reference palette (8 categorical slots, light mode); see docs/POWERBI.md.
    wjson(RP / "StaticResources" / "RegisteredResources" / theme, {
        "name": "Tariff comparison",
        "dataColors": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
        "background": "#FFFFFF", "foreground": "#0B0B0B", "tableAccent": "#2a78d6",
    })
    pages = ["comparison", "sources"]
    wjson(RP / "definition" / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": pages, "activePageName": pages[0]})

    def page(name, display):
        wjson(RP / "definition" / "pages" / name / "page.json", {
            "$schema": f"{SCHEMA}/item/report/definition/page/1.0.0/schema.json",
            "name": name, "displayName": display, "displayOption": "FitToPage", "height": 720, "width": 1280})

    page("comparison", "Bill comparison")
    dropdown = {"data": [{"properties": {"mode": lit("'Dropdown'")}}],
                "selection": [{"properties": {"singleSelect": lit("true")}}]}
    visual("comparison", "usageSlicer", "slicer", 16, 16, 220, 72,
           {"Values": [proj(col("Usage Level", "kWh"), "Monthly usage (kWh)")]}, objects=dropdown, z=1)
    visual("comparison", "monthSlicer", "slicer", 252, 16, 220, 72,
           {"Values": [proj(col("Months", "month_name"), "Billing month (blank = 12-month average)")]},
           objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]}, z=2)
    visual("comparison", "typeSlicer", "slicer", 488, 16, 220, 72,
           {"Values": [proj(col("Utilities", "type"), "Utility type")]},
           objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]}, z=3)
    visual("comparison", "billBar", "clusteredBarChart", 16, 100, 600, 300,
           {"Category": [proj(col("Utilities", "short_name"), "Utility")],
            "Y": [proj(meas("Bills", "Bill at Selected Usage"), "Monthly bill")]},
           titletext="Monthly bill at the selected usage (before taxes and fees)",
           sort=[{"field": meas("Bills", "Bill at Selected Usage"), "direction": "Ascending"}], z=4)
    visual("comparison", "componentBar", "barChart", 632, 100, 632, 300,
           {"Category": [proj(col("Utilities", "short_name"), "Utility")],
            "Series": [proj(col("Components", "component"), "Component")],
            "Y": [proj(meas("Components", "Component at Selected Usage"), "Dollars per month")]},
           titletext="What makes up the bill at the selected usage", z=5)
    visual("comparison", "billLine", "lineChart", 16, 412, 600, 292,
           {"Category": [proj(col("Bills", "kwh"), "Monthly usage (kWh)")],
            "Series": [proj(col("Utilities", "short_name"), "Utility")],
            "Y": [proj(meas("Bills", "Monthly Bill"), "Monthly bill")]},
           titletext="Monthly bill by usage, 0-3,000 kWh", z=6)
    visual("comparison", "detailTable", "tableEx", 632, 412, 632, 292,
           {"Values": [proj(col("Utilities", "utility"), "Utility"),
                       proj(col("Utilities", "type"), "Type"),
                       proj(meas("Bills", "Bill at Selected Usage"), "Bill"),
                       proj(meas("Bills", "Cents per kWh at Selected Usage"), "Cents/kWh"),
                       proj(meas("Bills", "Difference vs Lowest"), "vs. lowest"),
                       proj(meas("Bills", "Fuel Share at Selected Usage"), "Fuel share"),
                       proj(col("Utilities", "effective"), "Rates effective")]},
           titletext="Detail at the selected usage",
           sort=[{"field": meas("Bills", "Bill at Selected Usage"), "direction": "Ascending"}], z=7)

    page("sources", "Sources and validation")
    visual("sources", "sourcesTable", "tableEx", 16, 16, 1248, 330,
           {"Values": [proj(col("Utilities", "utility"), "Utility"),
                       proj(col("Utilities", "schedule"), "Schedule"),
                       proj(col("Utilities", "jurisdiction"), "Regulation"),
                       proj(col("Utilities", "effective"), "Effective"),
                       proj(col("Utilities", "source_1"), "Primary source")]},
           titletext="Rate schedules and sources (full source lists and notes are in the repository's data files)", z=1)
    visual("sources", "validationTable", "tableEx", 16, 362, 1248, 342,
           {"Values": [proj(col("Utilities", "short_name"), "Utility"),
                       proj(col("Validation", "kwh"), "kWh"),
                       proj(col("Validation", "calculator"), "Calculator"),
                       proj(col("Validation", "published"), "Published"),
                       proj(col("Validation", "difference"), "Difference"),
                       proj(col("Validation", "source"), "Source"),
                       proj(col("Validation", "note"), "Note")]},
           titletext="Calculator vs. independently published bills (PSC and FMEA)", z=2)


def build_shortcut():
    wjson(PBI / f"{NAME}.pbip", {"$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                                 "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                 "settings": {"enableAutoRecovery": True}})
    write(PBI / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")


if __name__ == "__main__":
    build_model()
    build_report()
    build_shortcut()
    n = sum(1 for _ in PBI.rglob("*") if _.is_file() and "data" not in _.parts)
    print(f"wrote Power BI project: {n} files in powerbi/")
