"""
Análisis de ventas de "Granorte Café" (empresa ficticia, datos sintéticos).

Calcula:
  1. KPIs mensuales y anuales: ventas, margen bruto, ticket promedio, clientes activos.
  2. Desempeño por canal (2024 vs. 2025).
  3. Puente de margen 2024 → 2025: efecto de los descuentos online y del precio
     congelado de la referencia estrella.
  4. Pareto / ABC de productos.
  5. Segmentación RFM de clientes y recompra.
  6. Recomendaciones cuantificadas.

Salida: ../datos/resultados/*.csv  (también sirven como tablas para Power BI)
Uso:    python analisis_ventas.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent / "datos"
RES = BASE / "resultados"
RES.mkdir(exist_ok=True)
ESTRELLA = "P001"
INICIO_DESC = pd.Timestamp("2025-07-01")
AJUSTE_PRECIO = pd.Timestamp("2025-04-01")
FECHA_REF = pd.Timestamp("2025-12-31")


def cargar():
    v = pd.read_csv(BASE / "ventas.csv", parse_dates=["fecha"])
    p = pd.read_csv(BASE / "productos.csv")
    c = pd.read_csv(BASE / "clientes.csv", parse_dates=["fecha_primera_compra"])
    k = pd.read_csv(BASE / "canales.csv")
    v = v.merge(k[["id_canal", "canal"]], on="id_canal").merge(p[["id_producto", "nombre_producto", "categoria"]], on="id_producto")
    v["venta_neta"] = v["venta_neta"].astype(float)
    v["venta_bruta"] = (v["cantidad"] * v["precio_unitario"]).astype(float)
    v["anio"] = v["fecha"].dt.year
    v["mes"] = v["fecha"].dt.to_period("M").dt.to_timestamp()
    return v, p, c, k


def resumen(g):
    ventas, costo = g["venta_neta"].sum(), g["costo_total"].sum()
    return pd.Series({
        "ventas": ventas, "costo": costo, "margen_bruto": ventas - costo,
        "margen_pct": (ventas - costo) / ventas,
        "facturas": g["id_factura"].nunique(),
        "ticket_promedio": ventas / g["id_factura"].nunique(),
        "clientes_activos": g["id_cliente"].nunique(),
        "unidades": g["cantidad"].sum(),
        "descuento_pct": 1 - ventas / g["venta_bruta"].sum(),
    })


def margen_pct(df):
    return 1 - df["costo_total"].sum() / df["venta_neta"].sum()


def puente_margen(v):
    """Descompone la caída del margen % de 2024 a 2025."""
    a24, a25 = v[v.anio == 2024], v[v.anio == 2025].copy()
    m24, m25 = margen_pct(a24), margen_pct(a25)

    # Escenario 1: la tienda online mantiene en el 2.º semestre su descuento del 1.er semestre
    online = a25["id_canal"].eq("C04")
    desc_h1 = 1 - a25.loc[online & (a25.fecha < INICIO_DESC), "venta_neta"].sum() / \
        a25.loc[online & (a25.fecha < INICIO_DESC), "venta_bruta"].sum()
    e1 = a25.copy()
    m = online & (e1.fecha >= INICIO_DESC)
    e1.loc[m, "venta_neta"] = e1.loc[m, "venta_bruta"] * (1 - desc_h1)
    m_e1 = margen_pct(e1)

    # Escenario 2: además, la estrella recibe el mismo ajuste de precio que el resto del café
    e2 = e1.copy()
    m = e2["id_producto"].eq(ESTRELLA) & (e2.fecha >= AJUSTE_PRECIO)
    e2.loc[m, "venta_neta"] *= 1.05 * 1.09
    m_e2 = margen_pct(e2)

    puente = pd.DataFrame([
        ("Margen 2024", m24, "total"),
        ("Alza de costos y mezcla", m_e2 - m24, "efecto"),
        ("Precio congelado de la estrella", m_e1 - m_e2, "efecto"),
        ("Descuentos online (2.º sem.)", m25 - m_e1, "efecto"),
        ("Margen 2025", m25, "total"),
    ], columns=["concepto", "valor", "tipo"])
    return puente, desc_h1


def pareto(v):
    s = v[v.anio == 2025].groupby(["id_producto", "nombre_producto", "categoria"])["venta_neta"].sum() \
        .sort_values(ascending=False).reset_index()
    s["rank"] = np.arange(1, len(s) + 1)
    s["pct_productos"] = s["rank"] / len(s)
    s["pct_ventas"] = s["venta_neta"] / s["venta_neta"].sum()
    s["pct_ventas_acum"] = s["pct_ventas"].cumsum()
    s["clase_abc"] = np.select([s["pct_ventas_acum"] <= 0.80, s["pct_ventas_acum"] <= 0.95], ["A", "B"], "C")
    return s


def rfm(v):
    g = v.groupby("id_cliente").agg(ultima=("fecha", "max"), primera=("fecha", "min"),
                                     frecuencia=("id_factura", "nunique"), monto=("venta_neta", "sum"))
    g["recencia_dias"] = (FECHA_REF - g["ultima"]).dt.days
    g["R"] = pd.qcut(g["recencia_dias"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    g["F"] = pd.qcut(g["frecuencia"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    g["M"] = pd.qcut(g["monto"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    nuevo = (FECHA_REF - g["primera"]).dt.days <= 90
    g["segmento"] = np.select(
        [nuevo, (g.R >= 4) & (g.F >= 4), (g.R >= 3) & (g.F >= 4), (g.R >= 4) & (g.F >= 2),
         (g.R <= 2) & (g.F >= 3), (g.R == 3)],
        ["Nuevos", "Campeones", "Leales", "Potenciales", "En riesgo", "Necesitan atención"],
        "Perdidos")
    return g.reset_index()


if __name__ == "__main__":
    v, p, c, k = cargar()

    km = v.groupby("mes").apply(resumen, include_groups=False).reset_index()
    ka = v.groupby("anio").apply(resumen, include_groups=False).reset_index()
    kc = v.groupby(["anio", "id_canal", "canal"]).apply(resumen, include_groups=False).reset_index()
    kcm = v.groupby(["mes", "canal"]).apply(resumen, include_groups=False).reset_index()
    km.to_csv(RES / "kpis_mensuales.csv", index=False)
    ka.to_csv(RES / "kpis_anuales.csv", index=False)
    kc.to_csv(RES / "kpis_canal_anual.csv", index=False)
    kcm.to_csv(RES / "kpis_canal_mensual.csv", index=False)

    puente, desc_h1 = puente_margen(v)
    puente.to_csv(RES / "puente_margen.csv", index=False)

    par = pareto(v)
    par.to_csv(RES / "pareto_productos.csv", index=False)

    r = rfm(v)
    r.to_csv(RES / "rfm_clientes.csv", index=False)
    v25 = v[v.anio == 2025].groupby("id_cliente")["venta_neta"].sum()
    r["ventas_2025"] = r["id_cliente"].map(v25).fillna(0)
    seg = r.groupby("segmento").agg(clientes=("id_cliente", "count"), ventas_2025=("ventas_2025", "sum"),
                                    monto_historico=("monto", "sum"), recencia_media=("recencia_dias", "mean"),
                                    frecuencia_media=("frecuencia", "mean")).reset_index()
    seg["pct_clientes"] = seg["clientes"] / seg["clientes"].sum()
    seg["pct_ventas_2025"] = seg["ventas_2025"] / seg["ventas_2025"].sum()
    seg.to_csv(RES / "rfm_segmentos.csv", index=False)

    compras = v.groupby("id_cliente")["id_factura"].nunique()
    recompra = (compras >= 2).mean()
    c24 = set(v.loc[v.anio == 2024, "id_cliente"])
    c25 = set(v.loc[v.anio == 2025, "id_cliente"])
    retencion = len(c24 & c25) / len(c24)

    # ------------------------------------------------ recomendaciones
    h2_online = v[(v.id_canal == "C04") & (v.fecha >= INICIO_DESC)].copy()
    cap = 0.10
    nueva = h2_online["venta_bruta"] * (1 - np.minimum(h2_online["descuento_pct"], cap))
    rec1 = (nueva - h2_online["venta_neta"]).sum()                       # mismo volumen
    afect = h2_online["descuento_pct"] > cap
    marg_nueva = (nueva - h2_online["costo_total"])
    # escenario prudente: las líneas con descuento > 10 % pierden 30 % de su volumen
    rec1_prudente = (marg_nueva[~afect].sum() + 0.7 * marg_nueva[afect].sum()) - \
        (h2_online["venta_neta"] - h2_online["costo_total"]).sum()

    est = v[(v.id_producto == ESTRELLA) & (v.fecha >= AJUSTE_PRECIO)]
    meses_est = 9
    rec2 = (est["venta_neta"].sum() * 0.10) * 12 / meses_est                # +10 % precio, mismo volumen, anualizado
    marg_est = est["venta_neta"].sum() - est["costo_total"].sum()
    rec2_prudente = ((est["venta_neta"].sum() * 1.10 - est["costo_total"].sum()) * 0.92 - marg_est) * 12 / meses_est

    riesgo = r[r.segmento == "En riesgo"]
    gasto_anual = (riesgo["monto"] / 2).mean()
    reactiva = 0.20
    margen_prom = margen_pct(v[v.anio == 2025])
    rec3_ventas = len(riesgo) * reactiva * gasto_anual
    rec3_margen = rec3_ventas * margen_prom

    recs = pd.DataFrame([
        {"id": 1, "recomendacion": "Limitar el descuento online al 10 %", "margen_anual_mismo_volumen": rec1 * 2,
         "margen_anual_prudente": rec1_prudente * 2,
         "supuesto": "Anualiza el 2.º semestre de 2025; escenario prudente: las líneas con descuento > 10 % pierden 30 % del volumen"},
        {"id": 2, "recomendacion": "Subir 10 % el precio de Café en grano Huila 500 g", "margen_anual_mismo_volumen": rec2,
         "margen_anual_prudente": rec2_prudente,
         "supuesto": "Anualiza abr-dic 2025; escenario prudente: el volumen de la referencia cae 8 %"},
        {"id": 3, "recomendacion": "Campaña de reactivación a clientes 'En riesgo'", "margen_anual_mismo_volumen": rec3_margen,
         "margen_anual_prudente": rec3_margen,
         "supuesto": f"Se reactiva el {reactiva:.0%} de {len(riesgo)} clientes con su gasto anual promedio y el margen de 2025"},
    ])
    recs.to_csv(RES / "recomendaciones.csv", index=False)

    indicadores = pd.DataFrame([
        ("recompra_pct", recompra), ("retencion_2024_2025", retencion),
        ("descuento_online_h1_2025", desc_h1),
        ("descuento_online_h2_2025", 1 - h2_online["venta_neta"].sum() / h2_online["venta_bruta"].sum()),
        ("clientes_en_riesgo", len(riesgo)), ("gasto_anual_cliente_en_riesgo", gasto_anual),
        ("rec3_ventas", rec3_ventas),
        ("productos_total", len(par)), ("productos_clase_a", (par.clase_abc == "A").sum()),
        ("pct_ventas_top20pct_productos", par.loc[par["pct_productos"] <= 0.2, "pct_ventas"].sum()),
        ("estrella_rank_2025", par.loc[par.id_producto == ESTRELLA, "rank"].iloc[0]),
        ("estrella_pct_ventas_2025", par.loc[par.id_producto == ESTRELLA, "pct_ventas"].iloc[0]),
        ("estrella_margen_2024", margen_pct(v[(v.id_producto == ESTRELLA) & (v.anio == 2024)])),
        ("estrella_margen_2025_desde_abr", margen_pct(est)),
    ], columns=["indicador", "valor"])
    indicadores.to_csv(RES / "indicadores.csv", index=False)

    pd.set_option("display.width", 200)
    print(ka.round(3).to_string())
    print(kc.pivot(index="canal", columns="anio", values=["ventas", "margen_pct", "ticket_promedio"]).round(3))
    print(puente.round(4))
    print(seg.round(3).to_string())
    print(recs[["recomendacion", "margen_anual_mismo_volumen", "margen_anual_prudente"]].round(0).to_string())
    print(indicadores.to_string())
