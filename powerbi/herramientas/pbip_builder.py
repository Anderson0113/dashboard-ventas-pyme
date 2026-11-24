"""
Generador de proyectos de Power BI (.pbip) a partir de una especificación en Python.

Crea:
  <Nombre>.pbip
  <Nombre>.SemanticModel/  (definition.pbism + model.bim)
  <Nombre>.Report/         (definition.pbir + report.json)

Al abrir el .pbip en Power BI Desktop: Inicio > Actualizar para cargar los CSV,
y Archivo > Guardar como > .pbix si se quiere un solo archivo.
"""
import json
import shutil
import uuid
from pathlib import Path

# ----------------------------------------------------------------------------- modelo

TIPOS_M = {"string": "type text", "int64": "Int64.Type", "double": "type number",
           "dateTime": "type date", "boolean": "type logical"}


def tabla_csv(nombre, archivo, columnas, pasos_extra=None, oculta=False):
    """columnas: lista de (nombre, tipo, opciones dict)."""
    tipos = ", ".join(f'{{"{c}", {TIPOS_M[t]}}}' for c, t, *_ in columnas)
    m = [
        "let",
        f'    Origen = Csv.Document(File.Contents(RutaDatos & "\\{archivo}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),",
        f'    Tipos = Table.TransformColumnTypes(Encabezados, {{{tipos}}}, "en-US")',
    ]
    ultimo = "Tipos"
    for i, paso in enumerate(pasos_extra or []):
        m[-1] += ","
        m.append(f"    Paso{i} = {paso.replace('#PREV', ultimo)}")
        ultimo = f"Paso{i}"
    m += ["in", f"    {ultimo}"]
    return _tabla(nombre, columnas, m, oculta)


def tabla_m(nombre, columnas, m_lineas, oculta=False):
    return _tabla(nombre, columnas, m_lineas, oculta)


def _tabla(nombre, columnas, m_lineas, oculta):
    cols = []
    for c, t, *op in columnas:
        op = op[0] if op else {}
        col = {"name": op.get("como", c), "dataType": t, "sourceColumn": c, "summarizeBy": op.get("summarizeBy", "none"),
               "lineageTag": str(uuid.uuid4())}
        for k in ("formatString", "sortByColumn", "isHidden", "dataCategory"):
            if k in op:
                col[k] = op[k]
        cols.append(col)
    return {"name": nombre, "lineageTag": str(uuid.uuid4()), "columns": cols,
            "partitions": [{"name": nombre, "mode": "import", "source": {"type": "m", "expression": m_lineas}}],
            **({"isHidden": True} if oculta else {})}


def tabla_medidas(nombre, medidas):
    """medidas: lista de (nombre, expresion_dax, formato, carpeta)."""
    t = _tabla(nombre, [("_", "string", {"isHidden": True})],
               ["let", '    Origen = #table(type table [_ = text], {})', "in", "    Origen"], False)
    t["measures"] = [{"name": n, "expression": e.strip().split("\n") if "\n" in e.strip() else e.strip(),
                      "formatString": f, "displayFolder": d, "lineageTag": str(uuid.uuid4())}
                     for n, e, f, d in medidas]
    return t


def tabla_calendario(inicio, fin):
    a, b = inicio.split("-"), fin.split("-")
    m = [
        "let",
        f"    Inicio = #date({int(a[0])}, {int(a[1])}, {int(a[2])}),",
        f"    Fin = #date({int(b[0])}, {int(b[1])}, {int(b[2])}),",
        "    Fechas = List.Dates(Inicio, Duration.Days(Fin - Inicio) + 1, #duration(1, 0, 0, 0)),",
        '    Tabla = Table.FromList(Fechas, Splitter.SplitByNothing(), {"Fecha"}),',
        '    Tipo = Table.TransformColumnTypes(Tabla, {{"Fecha", type date}}),',
        '    Anio = Table.AddColumn(Tipo, "Año", each Date.Year([Fecha]), Int64.Type),',
        '    MesNum = Table.AddColumn(Anio, "MesNum", each Date.Year([Fecha]) * 100 + Date.Month([Fecha]), Int64.Type),',
        '    NombresMes = {"ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"},',
        '    Mes = Table.AddColumn(MesNum, "Mes", each NombresMes{Date.Month([Fecha]) - 1} & "-" & Text.From(Date.Year([Fecha])), type text),',
        '    Trimestre = Table.AddColumn(Mes, "Trimestre", each Text.From(Date.Year([Fecha])) & " T" & Text.From(Date.QuarterOfYear([Fecha])), type text),',
        '    InicioMes = Table.AddColumn(Trimestre, "Inicio de mes", each Date.StartOfMonth([Fecha]), type date)',
        "in",
        "    InicioMes",
    ]
    cols = [("Fecha", "dateTime", {"formatString": "dd/mm/yyyy"}), ("Año", "int64"), ("MesNum", "int64", {"isHidden": True}),
            ("Mes", "string", {"sortByColumn": "MesNum"}), ("Trimestre", "string"),
            ("Inicio de mes", "dateTime", {"formatString": "mmm yyyy"})]
    t = _tabla("Calendario", cols, m, False)
    t["dataCategory"] = "Time"
    for c in t["columns"]:
        if c["name"] == "Fecha":
            c["isKey"] = True
    return t


def relacion(desde, hacia, activa=True):
    (t1, c1), (t2, c2) = desde.split("."), hacia.split(".")
    r = {"name": str(uuid.uuid4()), "fromTable": t1, "fromColumn": c1, "toTable": t2, "toColumn": c2}
    if not activa:
        r["isActive"] = False
    return r


def modelo(tablas, relaciones, ruta_datos):
    return {
        "compatibilityLevel": 1567,
        "model": {
            "culture": "es-CO",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "es-CO",
            "tables": tablas,
            "relationships": relaciones,
            "expressions": [{
                "name": "RutaDatos", "kind": "m", "lineageTag": str(uuid.uuid4()),
                "expression": f'"{ruta_datos}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
            }],
            "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                            {"name": "PBI_ProTooling", "value": "[\"DevMode\"]"}],
        },
    }


# ----------------------------------------------------------------------------- reporte

TEMA_BASE = "CY24SU08"  # tema base estándar de Power BI (archivo junto a este script)
TEMA = "TemaPortafolio"  # tema propio con la paleta del portafolio


def _lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def colores_serie(entidad, columna, colores):
    """Color fijo por valor de la serie: {"Aliados": "#eb6834", ...}."""
    return {"dataPoint": [{"properties": {"fill": {"solid": {"color": _lit(f"'{c}'")}}},
                           "selector": {"data": [{"scopeId": {"Comparison": {
                               "ComparisonKind": 0,
                               "Left": {"Column": {"Expression": {"SourceRef": {"Entity": entidad}}, "Property": columna}},
                               "Right": {"Literal": {"Value": f"{v}L" if isinstance(v, int) else f"'{v}'"}}}}}]}}
                          for v, c in colores.items()]}


SIN_TOTALES_MATRIZ = {"subTotals": [{"properties": {"rowSubtotals": _lit("false"), "columnSubtotals": _lit("false")}}]}
SIN_TOTALES_TABLA = {"total": [{"properties": {"totals": _lit("false")}}]}


def escala_fondo(entidad, medida, minimo, maximo):
    """Formato condicional de fondo (degradado de dos colores) sobre una medida en tabla o matriz."""
    regla = {"FillRule": {"Input": {"Measure": {"Expression": {"SourceRef": {"Entity": entidad}}, "Property": medida}},
                          "FillRule": {"linearGradient2": {
                              "min": {"color": {"Literal": {"Value": f"'{minimo}'"}}},
                              "max": {"color": {"Literal": {"Value": f"'{maximo}'"}}},
                              "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}
    return {"values": [{"properties": {"backColor": {"solid": {"color": {"expr": regla}}}},
                        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                     "metadata": f"{entidad}.{medida}"}},
                       {"properties": {"fontSize": _lit("11D")}}],
            "columnHeaders": [{"properties": {"fontSize": _lit("11D")}}],
            "rowHeaders": [{"properties": {"fontSize": _lit("11D")}}]}


def decimales_tarjeta(n=1):
    return {"labels": [{"properties": {"labelPrecision": _lit(f"{n}L")}}]}


def color_unico(color, etiquetas=True):
    o = {"dataPoint": [{"properties": {"fill": {"solid": {"color": _lit(f"'{color}'")}}}}]}
    if etiquetas:
        o["labels"] = [{"properties": {"show": _lit("true")}}]
    return o

def _campo(entidad, prop, medida, alias):
    clave = "Measure" if medida else "Column"
    return {clave: {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}, "Name": f"{entidad}.{prop}"}


def _titulo(texto):
    return {"title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                                      "text": {"expr": {"Literal": {"Value": f"'{texto}'"}}}}}]}


def visual(tipo, x, y, w, h, roles, titulo=None, objetos=None, orden_desc=None):
    """roles: {"Values": [("Medidas", "Cartera Bruta", True)], "Category": [("Calendario", "Inicio de mes", False)]}"""
    alias, desde, select, proy = {}, [], [], {}
    for rol, campos in roles.items():
        proy[rol] = []
        for ent, prop, es_medida in campos:
            if ent not in alias:
                alias[ent] = f"t{len(alias)}"
                desde.append({"Name": alias[ent], "Entity": ent, "Type": 0})
            s = _campo(ent, prop, es_medida, alias[ent])
            if s["Name"] not in [q["Name"] for q in select]:
                select.append(s)
            proy[rol].append({"queryRef": s["Name"]} | ({"active": True} if rol == "Category" or (tipo == "slicer" and not es_medida) else {}))
    nombre = uuid.uuid4().hex[:20]
    consulta = {"Version": 2, "From": desde, "Select": select}
    if orden_desc:  # (entidad, medida): ordenar de mayor a menor por esa medida
        ent, prop = orden_desc
        consulta["OrderBy"] = [{"Direction": 2, "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": alias[ent]}},
                                                                           "Property": prop}}}]
    sv = {"visualType": tipo, "projections": proy,
          "prototypeQuery": consulta,
          "drillFilterOtherVisuals": True}
    if titulo:
        sv["vcObjects"] = _titulo(titulo)
    if objetos:
        sv["objects"] = objetos
    config = {"name": nombre, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
              "singleVisual": sv}
    return {"x": x, "y": y, "z": 0, "width": w, "height": h, "config": json.dumps(config, ensure_ascii=False),
            "filters": "[]"}


def texto(x, y, w, h, lineas):
    """lineas: lista de (texto, tamaño_pt, negrita, color)."""
    parrafos = [{"textRuns": [{"value": t, "textStyle": {"fontSize": f"{s}pt", **({"fontWeight": "bold"} if b else {}),
                                                          }}]} for t, s, b, c in lineas]
    nombre = uuid.uuid4().hex[:20]
    config = {"name": nombre, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
              "singleVisual": {"visualType": "textbox", "drillFilterOtherVisuals": True,
                               "objects": {"general": [{"properties": {"paragraphs": parrafos}}]}}}
    return {"x": x, "y": y, "z": 0, "width": w, "height": h, "config": json.dumps(config, ensure_ascii=False),
            "filters": "[]"}


def reporte(paginas):
    """paginas: lista de (nombre_visible, [visuales])."""
    secciones = []
    for i, (nombre, visuales) in enumerate(paginas):
        secciones.append({"id": i, "name": f"Seccion{i + 1:02d}", "displayName": nombre, "displayOption": 1,
                          "width": 1280, "height": 720, "filters": "[]", "config": "{}",
                          "visualContainers": visuales, "ordinal": i})
    config = {"version": "5.57", "themeCollection": {"baseTheme": {"name": TEMA_BASE, "version": "5.57", "type": 2},
                                                     "customTheme": {"name": TEMA, "version": "5.57", "type": 1}},
              "activeSectionIndex": 0, "defaultDrillFilterOtherVisuals": True,
              "settings": {"useNewFilterPaneExperience": True, "allowChangeFilterTypes": True,
                           "useStylableVisualContainerHeader": True, "exportDataMode": 1,
                           "useDefaultAggregateDisplayName": True, "useEnhancedTooltips": True}}
    paquetes = [{"resourcePackage": {"name": "SharedResources", "type": 2, "disabled": False,
                                     "items": [{"type": 202, "path": f"BaseThemes/{TEMA_BASE}.json", "name": TEMA_BASE}]}},
                {"resourcePackage": {"name": "RegisteredResources", "type": 1, "disabled": False,
                                     "items": [{"type": 202, "path": f"{TEMA}.json", "name": TEMA}]}}]
    return {"id": 0, "config": json.dumps(config), "layoutOptimization": 0, "resourcePackages": paquetes,
            "sections": secciones}


# ----------------------------------------------------------------------------- escritura

def escribir_pbip(carpeta, nombre, model_bim, report_json):
    carpeta = Path(carpeta)
    sm, rp = carpeta / f"{nombre}.SemanticModel", carpeta / f"{nombre}.Report"
    for d in (sm, rp):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    def w(p, obj):
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    w(carpeta / f"{nombre}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{nombre}.Report"}}],
        "settings": {"enableAutoRecovery": True}})
    w(sm / "definition.pbism", {"version": "1.0", "settings": {}})
    w(sm / "model.bim", model_bim)
    w(rp / "definition.pbir", {"version": "1.0", "datasetReference": {"byPath": {"path": f"../{nombre}.SemanticModel"}}})
    w(rp / "report.json", report_json)
    temas = rp / "StaticResources" / "SharedResources" / "BaseThemes"
    temas.mkdir(parents=True)
    shutil.copy(Path(__file__).with_name(f"{TEMA_BASE}.json"), temas / f"{TEMA_BASE}.json")
    registrados = rp / "StaticResources" / "RegisteredResources"
    registrados.mkdir(parents=True)
    shutil.copy(Path(__file__).with_name(f"{TEMA}.json"), registrados / f"{TEMA}.json")
    (carpeta / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")
    return carpeta / f"{nombre}.pbip"
