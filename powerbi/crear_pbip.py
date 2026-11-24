"""
Genera el proyecto de Power BI (PBIP) del caso de ventas de Granorte Café.
Uso: python crear_pbip.py   ->  powerbi/VentasGranorte/VentasGranorte.pbip
Al abrirlo en Power BI Desktop: "Actualizar ahora" para cargar los CSV.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "herramientas"))
from pbip_builder import (SIN_TOTALES_TABLA, color_unico, colores_serie, decimales_tarjeta, escribir_pbip, modelo,  # noqa: E402
                          relacion, reporte, tabla_calendario, tabla_csv, tabla_medidas, texto, visual)

DATOS = str(AQUI.parent / "datos")
PCT, ENT, COP = "0.0 %;-0.0 %;0.0 %", "#,0", "\\$ #,0"
TXT1, TXT2 = "#0b0b0b", "#52514e"
CANALES = {"Tienda Chapinero": "#2a78d6", "Tienda Usaquén": "#1baf7a", "Tienda El Poblado": "#6250d6",
           "Tienda online": "#eb6834", "Mayoristas": "#eda100"}
ANIOS = {2024: "#c3c2b7", 2025: "#2a78d6"}

# ------------------------------------------------------------------ tablas
ventas = tabla_csv("ventas", "ventas.csv", [
    ("id_factura", "string"), ("linea", "int64"), ("fecha", "dateTime", {"formatString": "dd/mm/yyyy"}),
    ("id_cliente", "string"), ("id_producto", "string"), ("id_canal", "string"),
    ("cantidad", "int64", {"summarizeBy": "sum"}), ("precio_unitario", "int64", {"formatString": COP}),
    ("descuento_pct", "double", {"formatString": PCT}), ("costo_unitario", "int64", {"formatString": COP}),
    ("venta_neta", "int64", {"formatString": COP, "summarizeBy": "sum"}),
    ("costo_total", "int64", {"formatString": COP, "summarizeBy": "sum"}),
])
productos = tabla_csv("productos", "productos.csv", [
    ("id_producto", "string"), ("nombre_producto", "string", {"como": "Producto"}),
    ("categoria", "string", {"como": "Categoría"}), ("presentacion", "string", {"como": "Presentación"}),
    ("precio_lista_actual", "int64", {"formatString": COP}), ("costo_unitario_actual", "int64", {"formatString": COP}),
])
clientes = tabla_csv("clientes", "clientes.csv", [
    ("id_cliente", "string"), ("tipo_cliente", "string", {"como": "Tipo de cliente"}),
    ("ciudad", "string", {"como": "Ciudad", "dataCategory": "City"}), ("id_canal_principal", "string"),
    ("fecha_primera_compra", "dateTime", {"formatString": "dd/mm/yyyy"}),
])
canales = tabla_csv("canales", "canales.csv", [
    ("id_canal", "string"), ("canal", "string", {"como": "Canal"}),
    ("tipo_canal", "string", {"como": "Tipo de canal"}), ("ciudad", "string", {"como": "Ciudad"}),
])
pareto = tabla_csv("pareto", "resultados\\pareto_productos.csv", [
    ("id_producto", "string"), ("nombre_producto", "string", {"como": "Producto"}),
    ("categoria", "string", {"como": "Categoría"}), ("venta_neta", "double", {"formatString": COP}),
    ("rank", "int64", {"como": "Puesto"}), ("pct_productos", "double", {"formatString": PCT}),
    ("pct_ventas", "double", {"formatString": PCT}), ("pct_ventas_acum", "double", {"formatString": PCT, "como": "% ventas acumulado"}),
    ("clase_abc", "string", {"como": "Clase ABC"}),
])
segmentos = tabla_csv("rfm_segmentos", "resultados\\rfm_segmentos.csv", [
    ("segmento", "string", {"como": "Segmento"}), ("clientes", "int64", {"formatString": ENT}),
    ("ventas_2025", "double", {"formatString": COP}), ("monto_historico", "double", {"formatString": COP}),
    ("recencia_media", "double", {"formatString": "0", "como": "Días desde la última compra"}), ("frecuencia_media", "double", {"formatString": "0.0", "como": "Compras promedio"}),
    ("pct_clientes", "double", {"formatString": PCT}), ("pct_ventas_2025", "double", {"formatString": PCT}),
])
recomendaciones = tabla_csv("recomendaciones", "resultados\\recomendaciones.csv", [
    ("id", "int64"), ("recomendacion", "string", {"como": "Recomendación"}),
    ("margen_anual_mismo_volumen", "double", {"formatString": COP, "como": "Margen anual (mismo volumen)"}),
    ("margen_anual_prudente", "double", {"formatString": COP, "como": "Margen anual (prudente)"}),
    ("supuesto", "string", {"como": "Supuesto"}),
])

ANIO_ACTUAL = "VAR a = YEAR ( CALCULATE ( MAX ( ventas[fecha] ), ALL ( ventas ), ALL ( Calendario ) ) ) RETURN "
medidas = tabla_medidas("Medidas", [
    ("Ventas", "SUM ( ventas[venta_neta] )", COP, "Base"),
    ("Costo", "SUM ( ventas[costo_total] )", COP, "Base"),
    ("Margen Bruto", "[Ventas] - [Costo]", COP, "Base"),
    ("Margen %", "DIVIDE ( [Margen Bruto], [Ventas] )", PCT, "Base"),
    ("Unidades", "SUM ( ventas[cantidad] )", ENT, "Base"),
    ("Facturas", "DISTINCTCOUNT ( ventas[id_factura] )", ENT, "Base"),
    ("Ticket Promedio", "DIVIDE ( [Ventas], [Facturas] )", COP, "Base"),
    ("Clientes Activos", "DISTINCTCOUNT ( ventas[id_cliente] )", ENT, "Base"),
    ("Venta Bruta", "SUMX ( ventas, ventas[cantidad] * ventas[precio_unitario] )", COP, "Base"),
    ("Descuento %", "DIVIDE ( [Venta Bruta] - [Ventas], [Venta Bruta] )", PCT, "Base"),
    ("Ventas AA", "CALCULATE ( [Ventas], SAMEPERIODLASTYEAR ( Calendario[Fecha] ) )", COP, "Comparación"),
    ("Var % Ventas AA", "DIVIDE ( [Ventas] - [Ventas AA], [Ventas AA] )", "+0.0 %;-0.0 %;0.0 %", "Comparación"),
    ("Margen % AA", "CALCULATE ( [Margen %], SAMEPERIODLASTYEAR ( Calendario[Fecha] ) )", PCT, "Comparación"),
    ("Var Margen (pp)", "( [Margen %] - [Margen % AA] ) * 100", "+0.0 \"pp\";-0.0 \"pp\"", "Comparación"),
    ("Ventas (año actual)", ANIO_ACTUAL + "CALCULATE ( [Ventas], Calendario[Año] = a )", COP, "Año actual"),
    ("Var % Ventas (año actual)", ANIO_ACTUAL + "CALCULATE ( [Var % Ventas AA], Calendario[Año] = a )", "+0.0 %;-0.0 %;0.0 %", "Año actual"),
    ("Margen % (año actual)", ANIO_ACTUAL + "CALCULATE ( [Margen %], Calendario[Año] = a )", PCT, "Año actual"),
    ("Var Margen pp (año actual)", ANIO_ACTUAL + "CALCULATE ( [Var Margen (pp)], Calendario[Año] = a )", "+0.0 \"pp\";-0.0 \"pp\"", "Año actual"),
    ("Ticket Promedio (año actual)", ANIO_ACTUAL + "CALCULATE ( [Ticket Promedio], Calendario[Año] = a )", COP, "Año actual"),
    ("Clientes Activos (año actual)", ANIO_ACTUAL + "CALCULATE ( [Clientes Activos], Calendario[Año] = a )", ENT, "Año actual"),
    ("Descuento % (año actual)", ANIO_ACTUAL + "CALCULATE ( [Descuento %], Calendario[Año] = a )", PCT, "Año actual"),
    ("Ventas Pareto", "SUM ( pareto[venta_neta] )", COP, "Análisis"),
    ("Participación acumulada", "MAX ( pareto[pct_ventas_acum] )", PCT, "Análisis"),
    ("Clientes por segmento", "SUM ( rfm_segmentos[clientes] )", ENT, "Análisis"),
    ("% de ventas 2025 (segmento)", "SUM ( rfm_segmentos[pct_ventas_2025] )", PCT, "Análisis"),
    ("% de clientes (segmento)", "SUM ( rfm_segmentos[pct_clientes] )", PCT, "Análisis"),
])

tablas = [ventas, productos, clientes, canales, tabla_calendario("2024-01-01", "2025-12-31"),
          pareto, segmentos, recomendaciones, medidas]
relaciones = [
    relacion("ventas.id_producto", "productos.id_producto"),
    relacion("ventas.id_cliente", "clientes.id_cliente"),
    relacion("ventas.id_canal", "canales.id_canal"),
    relacion("ventas.fecha", "Calendario.Fecha"),
]


# ------------------------------------------------------------------ páginas
def encabezado(titulo, sub):
    return texto(20, 8, 1240, 64, [(titulo, 20, True, TXT1), (sub, 11, False, TXT2)])


M = "Medidas"
p1 = [
    encabezado("Granorte Café · Resumen de ventas", "Tostadora pyme (empresa ficticia, datos sintéticos) · tarjetas: último año completo frente al anterior"),
    visual("card", 20, 80, 300, 110, {"Values": [(M, "Ventas (año actual)", True)]}, "Ventas del año", decimales_tarjeta(1)),
    visual("card", 335, 80, 300, 110, {"Values": [(M, "Var % Ventas (año actual)", True)]}, "Crecimiento vs. año anterior"),
    visual("card", 650, 80, 300, 110, {"Values": [(M, "Margen % (año actual)", True)]}, "Margen bruto %"),
    visual("card", 965, 80, 295, 110, {"Values": [(M, "Var Margen pp (año actual)", True)]}, "Variación del margen"),
    visual("clusteredColumnChart", 20, 205, 600, 495, {"Category": [("Calendario", "Inicio de mes", False)],
                                                       "Y": [(M, "Ventas", True)]}, "Ventas por mes", color_unico("#2a78d6", False)),
    visual("lineChart", 635, 205, 625, 340, {"Category": [("Calendario", "Inicio de mes", False)],
                                             "Y": [(M, "Margen %", True)]}, "Margen bruto % por mes", color_unico("#eb6834", False)),
    visual("slicer", 635, 560, 305, 140, {"Values": [("canales", "Canal", False)]}, "Canal"),
    visual("slicer", 955, 560, 305, 140, {"Values": [("productos", "Categoría", False)]}, "Categoría"),
]
p2 = [
    encabezado("Canales", "La tienda online crece, pero los descuentos le quitan margen"),
    visual("lineChart", 20, 80, 760, 380, {"Category": [("Calendario", "Inicio de mes", False)], "Y": [(M, "Margen %", True)],
                                           "Series": [("canales", "Canal", False)]}, "Margen bruto % por canal",
           colores_serie("canales", "Canal", CANALES)),
    visual("lineChart", 795, 80, 465, 380, {"Category": [("Calendario", "Inicio de mes", False)], "Y": [(M, "Descuento %", True)],
                                            "Series": [("canales", "Canal", False)]}, "Descuento promedio por canal",
           colores_serie("canales", "Canal", CANALES)),
    visual("tableEx", 20, 475, 1240, 225, {"Values": [("canales", "Canal", False), (M, "Ventas (año actual)", True), (M, "Var % Ventas (año actual)", True),
                                                      (M, "Margen % (año actual)", True), (M, "Var Margen pp (año actual)", True),
                                                      (M, "Descuento % (año actual)", True), (M, "Ticket Promedio (año actual)", True),
                                                      (M, "Clientes Activos (año actual)", True)]},
           "Detalle por canal · 2025 frente a 2024", SIN_TOTALES_TABLA),
]
p3 = [
    encabezado("Productos: Pareto y clasificación ABC", "Pocas referencias concentran la mayor parte de las ventas"),
    visual("clusteredBarChart", 20, 80, 620, 620, {"Category": [("pareto", "Producto", False)], "Y": [(M, "Ventas Pareto", True)]},
           "Ventas por producto (2024-2025)", color_unico("#2a78d6", False), orden_desc=(M, "Ventas Pareto")),
    visual("tableEx", 655, 80, 605, 380, {"Values": [("pareto", "Puesto", False), ("pareto", "Producto", False),
                                                     ("pareto", "Clase ABC", False), (M, "Ventas Pareto", True),
                                                     (M, "Participación acumulada", True)]}, "Ranking y clase ABC", SIN_TOTALES_TABLA),
    visual("clusteredColumnChart", 655, 475, 605, 225, {"Category": [("productos", "Categoría", False)],
                                                        "Y": [(M, "Margen %", True)]}, "Margen bruto % por categoría",
           color_unico("#2a78d6")),
]
p4 = [
    encabezado("Clientes: segmentación RFM", "Recencia, frecuencia y monto · los Campeones son 1 de cada 5 clientes"),
    visual("clusteredBarChart", 20, 80, 615, 620, {"Category": [("rfm_segmentos", "Segmento", False)],
                                                   "Y": [(M, "% de ventas 2025 (segmento)", True)]}, "% de las ventas 2025",
           color_unico("#2a78d6"), orden_desc=(M, "% de ventas 2025 (segmento)")),
    visual("clusteredBarChart", 645, 80, 615, 380, {"Category": [("rfm_segmentos", "Segmento", False)],
                                                    "Y": [(M, "% de clientes (segmento)", True)]}, "% de los clientes",
           color_unico("#9ec5f4"), orden_desc=(M, "% de clientes (segmento)")),
    visual("tableEx", 645, 475, 615, 225, {"Values": [("rfm_segmentos", "Segmento", False), (M, "Clientes por segmento", True),
                                                      ("rfm_segmentos", "Días desde la última compra", False), ("rfm_segmentos", "Compras promedio", False)]},
           "Detalle por segmento", SIN_TOTALES_TABLA),
]
p5 = [
    encabezado("Recomendaciones", "Impacto estimado en margen bruto anual · escenarios con supuestos explícitos"),
    visual("tableEx", 20, 80, 1240, 300, {"Values": [("recomendaciones", "Recomendación", False),
                                                     ("recomendaciones", "Margen anual (prudente)", False),
                                                     ("recomendaciones", "Margen anual (mismo volumen)", False),
                                                     ("recomendaciones", "Supuesto", False)]}, "Acciones propuestas"),
    texto(20, 400, 1240, 200, [("Cómo leer", 13, True, TXT1),
                               ("Escenario prudente: incluye la pérdida de volumen esperada por cada acción. "
                                "Mismo volumen: supone que los clientes compran lo mismo. La decisión real debe validarse con una prueba piloto.",
                                11, False, TXT2)]),
]

if __name__ == "__main__":
    salida = AQUI / "VentasGranorte"
    salida.mkdir(exist_ok=True)
    ruta = escribir_pbip(salida, "VentasGranorte", modelo(tablas, relaciones, DATOS),
                         reporte([("Resumen", p1), ("Canales", p2), ("Productos", p3), ("Clientes RFM", p4),
                                  ("Recomendaciones", p5)]))
    print(ruta)
