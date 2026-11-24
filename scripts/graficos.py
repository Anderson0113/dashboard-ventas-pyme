"""
Genera las imágenes del caso de portafolio de ventas (1920x1200 px) a partir de ../datos/resultados.
Uso: python graficos.py   (ejecutar antes analisis_ventas.py)
Mismo sistema visual que el caso de cartera.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "datos" / "resultados"
IMG = RAIZ / "imagenes"
IMG.mkdir(exist_ok=True)

# Paleta y tinta (paleta categórica validada, modo claro)
SUP, PLANO = "#fcfcfb", "#f9f9f7"
TXT1, TXT2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, EJE = "#e1e0d9", "#c3c2b7"
AZUL, NARANJA = "#2a78d6", "#eb6834"
AZUL_CLARO = "#9ec5f4"
GRIS_SERIE = "#c3c2b7"
OK, CRITICO = "#0ca30c", "#d03b3b"
COLOR_ANIO = {2024: GRIS_SERIE, 2025: AZUL}

plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 13, "text.color": TXT1,
    "axes.edgecolor": EJE, "axes.labelcolor": TXT2, "axes.facecolor": SUP,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 12, "ytick.labelsize": 12,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SUP,
})
AUTOR = "Anderson Barrero · Analista de Datos y Power BI"
NOTA = "Datos sintéticos de una empresa ficticia (Granorte Café), generados con Python para fines demostrativos."
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ------------------------------------------------------------------ formato colombiano
def miles(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return miles(x * 100, d) + " %"


def millones(x, d=0):
    return f"$ {miles(x / 1e6, d)} M"


def mes_txt(f):
    return f"{MESES[f.month - 1]}-{f.year}"


def lienzo(titulo, subtitulo, seccion):
    fig = plt.figure(figsize=(12, 7.5), dpi=160)
    fig.text(0.05, 0.945, seccion.upper(), fontsize=11, color=MUTED, weight="semibold")
    fig.text(0.05, 0.895, titulo, fontsize=24, weight="semibold", color=TXT1)
    fig.text(0.05, 0.855, subtitulo, fontsize=13.5, color=TXT2)
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.065, 0.065], color=GRID, lw=1))
    fig.text(0.05, 0.035, AUTOR, fontsize=10.5, color=TXT2, weight="semibold")
    fig.text(0.95, 0.035, NOTA, fontsize=9.5, color=MUTED, ha="right")
    return fig


def ejes_limpios(ax, grid_y=True):
    ax.grid(axis="y" if grid_y else "x", color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ("left",) if grid_y else ("bottom",):
        ax.spines[s].set_visible(False)


def tarjeta(fig, x, y, w, h, etiqueta, valor, nota=None, color_nota=TXT2, tam_valor=28):
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                  transform=fig.transFigure, fc=PLANO, ec=GRID, lw=1))
    fig.text(x + 0.018, y + h - 0.045, etiqueta, fontsize=12, color=TXT2)
    fig.text(x + 0.018, y + h - 0.115, valor, fontsize=tam_valor, weight="semibold", color=TXT1)
    if nota:
        fig.text(x + 0.018, y + 0.025, nota, fontsize=11, color=color_nota)


def cargar():
    d = {n: pd.read_csv(RES / f"{n}.csv") for n in
         ["kpis_mensuales", "kpis_anuales", "kpis_canal_anual", "kpis_canal_mensual", "puente_margen",
          "pareto_productos", "rfm_segmentos", "recomendaciones", "indicadores"]}
    d["kpis_mensuales"]["mes"] = pd.to_datetime(d["kpis_mensuales"]["mes"])
    d["kpis_canal_mensual"]["mes"] = pd.to_datetime(d["kpis_canal_mensual"]["mes"])
    d["ind"] = d["indicadores"].set_index("indicador")["valor"]
    return d


# ------------------------------------------------------------------ 0. Portada
def portada(d):
    ka = d["kpis_anuales"].set_index("anio")
    rec = d["recomendaciones"]
    crec = ka.loc[2025, "ventas"] / ka.loc[2024, "ventas"] - 1
    fig = plt.figure(figsize=(12, 7.5), dpi=160)
    fig.add_artist(plt.Rectangle((0, 0), 0.012, 1, transform=fig.transFigure, color=AZUL))
    fig.text(0.07, 0.86, "CASO DE ESTUDIO · VENTAS Y RENTABILIDAD PARA PYMES", fontsize=12, color=MUTED, weight="semibold")
    fig.text(0.07, 0.72, f"Vendimos {pct(crec, 0)} más…\ny ganamos lo mismo", fontsize=40, weight="semibold",
             va="center", linespacing=1.15)
    fig.text(0.07, 0.565, "Dashboard de ventas de una tostadora de café: margen, canales, productos\n"
                          "y clientes (RFM), con recomendaciones cuantificadas para recuperar rentabilidad.",
             fontsize=15, color=TXT2, va="center", linespacing=1.5)
    datos = [(f"+{pct(crec)}", "ventas 2025 vs. 2024"),
             (f"{pct(ka.loc[2024, 'margen_pct'])} → {pct(ka.loc[2025, 'margen_pct'])}", "margen bruto"),
             (millones(rec["margen_anual_prudente"].sum()), "de margen anual recuperable\n(escenario prudente)")]
    for i, (v, t) in enumerate(datos):
        x = 0.07 + i * 0.29
        fig.text(x, 0.40, v, fontsize=30, weight="semibold", color=TXT1)
        fig.text(x, 0.355, t, fontsize=13, color=TXT2, va="top", linespacing=1.35)
    x = 0.07
    for h in ["Python", "SQL Server", "Power BI · DAX", "Análisis comercial"]:
        w = 0.012 * len(h) * 0.72 + 0.03
        fig.add_artist(FancyBboxPatch((x, 0.15), w, 0.055, boxstyle="round,pad=0,rounding_size=0.02",
                                      transform=fig.transFigure, fc=PLANO, ec=GRID, lw=1))
        fig.text(x + w / 2, 0.1775, h, fontsize=12.5, ha="center", va="center", color=TXT1)
        x += w + 0.015
    fig.text(0.07, 0.07, AUTOR, fontsize=12, color=TXT1, weight="semibold")
    fig.text(0.95, 0.07, "Datos sintéticos · empresa ficticia", fontsize=10.5, color=MUTED, ha="right")
    fig.savefig(IMG / "00_portada.png")
    plt.close(fig)


# ------------------------------------------------------------------ 1. Resumen
def resumen(d):
    ka = d["kpis_anuales"].set_index("anio")
    km = d["kpis_mensuales"]
    a, b = ka.loc[2024], ka.loc[2025]
    fig = lienzo("Las ventas crecen, pero el margen se queda atrás",
                 "Indicadores comerciales de Granorte Café · año 2025 frente a 2024",
                 "Caso de estudio · Dashboard de ventas")
    tarjetas = [
        ("Ventas netas 2025", millones(b.ventas), f"▲ {pct(b.ventas / a.ventas - 1)} vs. 2024", TXT2),
        ("Margen bruto", pct(b.margen_pct), f"▼ {miles((b.margen_pct - a.margen_pct) * 100, 1)} pp vs. 2024", CRITICO),
        ("Ticket promedio", f"$ {miles(b.ticket_promedio)}", f"▲ {pct(b.ticket_promedio / a.ticket_promedio - 1)} vs. 2024", TXT2),
        ("Clientes activos", miles(b.clientes_activos), f"▲ {pct(b.clientes_activos / a.clientes_activos - 1)} vs. 2024", TXT2),
    ]
    for i, t in enumerate(tarjetas):
        tarjeta(fig, 0.05 + i * 0.2275, 0.635, 0.2125, 0.17, *t)

    ax = fig.add_axes([0.085, 0.13, 0.61, 0.42])
    for anio in (2024, 2025):
        s = km[km.mes.dt.year == anio]
        x = s.mes.dt.month
        ax.plot(x, s.ventas, color=COLOR_ANIO[anio], lw=2, solid_capstyle="round", zorder=3 if anio == 2025 else 2)
        ax.scatter(x.iloc[-1], s.ventas.iloc[-1], s=60, color=COLOR_ANIO[anio], edgecolor=SUP, linewidth=2, zorder=4)
        ax.annotate(f"{anio}  {millones(s.ventas.iloc[-1])}", (x.iloc[-1], s.ventas.iloc[-1]),
                    xytext=(10, 0), textcoords="offset points", va="center", fontsize=11.5, color=TXT1)
    ax.set_xticks(range(1, 13), MESES)
    ax.set_xlim(0.7, 12.3)
    ax.set_ylim(0, km.ventas.max() * 1.15)
    ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"$ {miles(v / 1e6)} M"))
    ejes_limpios(ax)
    ax.set_title("Ventas netas mensuales", loc="left", fontsize=13.5, color=TXT1, pad=12)
    leg = [plt.Line2D([], [], color=COLOR_ANIO[k], lw=2.5, label=str(k)) for k in COLOR_ANIO]
    ax.legend(handles=leg, loc="lower right", frameon=False, ncol=2, fontsize=11.5)

    x0 = 0.785
    fig.text(x0, 0.545, "Hallazgos clave", fontsize=14, weight="semibold")
    mb_a, mb_b = a.margen_bruto, b.margen_bruto
    puntos = [f"Ventas +{pct(b.ventas / a.ventas - 1, 0)}, pero el margen\nbruto en pesos crece solo\n{pct(mb_b / mb_a - 1)}.",
              "Diciembre y las quincenas\nconcentran los picos.",
              "La caída del margen viene de\ncostos, descuentos online y\nuna referencia sin ajuste."]
    y = 0.48
    for i, p in enumerate(puntos, 1):
        fig.text(x0, y, f"{i}", fontsize=13, weight="semibold", color=AZUL, va="top")
        fig.text(x0 + 0.022, y, p, fontsize=12, color=TXT2, va="top", linespacing=1.4)
        y -= 0.06 + 0.035 * p.count("\n")
    fig.savefig(IMG / "01_resumen_ventas.png")
    plt.close(fig)


# ------------------------------------------------------------------ 2. Margen
def margen(d):
    km = d["kpis_mensuales"]
    pu = d["puente_margen"]
    caida = (pu.valor.iloc[-1] - pu.valor.iloc[0]) * 100
    controlable = -(pu.valor.iloc[2] + pu.valor.iloc[3]) * 100
    fig = lienzo(f"El margen cayó {miles(-caida, 1)} puntos; {miles(controlable, 1)} dependen de decisiones comerciales",
                 "Margen bruto % mensual y descomposición de la caída entre 2024 y 2025",
                 "Rentabilidad")
    ax = fig.add_axes([0.085, 0.14, 0.43, 0.6])
    ax.plot(km.mes, km.margen_pct, color=AZUL, lw=2, solid_capstyle="round", zorder=3)
    ax.scatter(km.mes.iloc[-1], km.margen_pct.iloc[-1], s=60, color=AZUL, edgecolor=SUP, linewidth=2, zorder=4)
    ax.annotate(pct(km.margen_pct.iloc[-1]), (km.mes.iloc[-1], km.margen_pct.iloc[-1]), xytext=(8, 0),
                textcoords="offset points", va="center", fontsize=11.5)
    for f, txt, yt in [("2025-03-01", "Sube el costo\ndel café verde", 0.535), ("2025-07-01", "Descuentos\nonline 20-30 %", 0.395)]:
        ax.axvline(pd.Timestamp(f), color=EJE, lw=1, zorder=1)
        ax.text(pd.Timestamp(f) + pd.Timedelta(days=8), yt, txt, fontsize=10.5, color=TXT2, va="top")
    ax.yaxis.set_major_locator(mt.MultipleLocator(0.05))
    ax.tick_params(axis="x", pad=8)
    ax.set_ylim(0.35, 0.55)
    ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v * 100:.0f} %"))
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: mes_txt(matplotlib.dates.num2date(v))))
    ax.set_xlim(km.mes.iloc[0] - pd.Timedelta(days=10), km.mes.iloc[-1] + pd.Timedelta(days=75))
    ejes_limpios(ax)
    ax.set_title("Margen bruto % por mes", loc="left", fontsize=13.5, pad=12)

    # Puente (cascada) en puntos porcentuales
    ax2 = fig.add_axes([0.6, 0.14, 0.36, 0.6])
    efectos = pu[pu.tipo == "efecto"].reset_index(drop=True)
    etiquetas = ["Alza de costos\ny mezcla", "Precio congelado\nde la estrella", "Descuentos\nonline"]
    for i, r in efectos.iterrows():
        col = NARANJA if i >= 1 else AZUL_CLARO
        ax2.bar(i, r.valor * 100, width=0.5, color=col, zorder=3)
        ax2.text(i, r.valor * 100 - 0.12, f"{miles(r.valor * 100, 1)} pp", ha="center", va="top", fontsize=12,
                 weight="semibold")
    ax2.axhline(0, color=EJE, lw=1, zorder=4)
    ax2.set_xticks(range(3), etiquetas, fontsize=11.5)
    ax2.xaxis.tick_top()
    ax2.set_ylim(-5, 0)
    ax2.set_xlim(-0.6, 2.6)
    ax2.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{miles(v, 0)} pp"))
    ejes_limpios(ax2)
    ax2.spines["bottom"].set_visible(False)
    ax2.set_title(f"¿Qué explica la caída de {pct(pu.valor.iloc[0])} a {pct(pu.valor.iloc[-1])}?", loc="left",
                  fontsize=13.5, pad=40)
    leg = [plt.Rectangle((0, 0), 1, 1, color=AZUL_CLARO, label="Externo (mercado)"),
           plt.Rectangle((0, 0), 1, 1, color=NARANJA, label="Decisión comercial")]
    ax2.legend(handles=leg, loc="lower right", frameon=False, fontsize=11)
    fig.savefig(IMG / "02_margen.png")
    plt.close(fig)


# ------------------------------------------------------------------ 3. Canales
def canales(d):
    kc = d["kpis_canal_anual"]
    orden = ["Mayoristas", "Tienda online", "Tienda Chapinero", "Tienda Usaquén", "Tienda El Poblado"]
    p = kc.pivot(index="canal", columns="anio").reindex(orden)
    on = p.loc["Tienda online"]
    caida_on = (on[("margen_pct", 2024)] - on[("margen_pct", 2025)]) * 100
    fig = lienzo(f"La tienda online crece {pct(on[('ventas', 2025)] / on[('ventas', 2024)] - 1, 0)}, pero su margen cae {miles(caida_on, 0)} puntos",
                 "Ventas, margen bruto y ticket promedio por canal · 2025 frente a 2024",
                 "Desempeño por canal")
    y = np.arange(len(orden))
    # Panel 1: ventas 2025
    ax = fig.add_axes([0.2, 0.17, 0.3, 0.57])
    colores = [NARANJA if c == "Tienda online" else AZUL for c in orden]
    ax.barh(y, p[("ventas", 2025)], height=0.5, color=colores, zorder=3)
    for i, c in enumerate(orden):
        v = p.loc[c, ("ventas", 2025)]
        g = v / p.loc[c, ("ventas", 2024)] - 1
        ax.text(v + 2e7, i, f"{millones(v)}  ·  +{pct(g, 0)}", va="center", fontsize=11.5)
    ax.set_yticks(y, orden, fontsize=12.5, color=TXT1)
    ax.invert_yaxis()
    ax.set_xlim(0, p[("ventas", 2025)].max() * 1.65)
    ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{miles(v / 1e6)}"))
    ejes_limpios(ax, grid_y=False)
    ax.set_title("Ventas 2025 (millones COP) y crecimiento", loc="left", fontsize=13, pad=12)

    # Panel 2: margen 2024 → 2025 (pesas)
    ax2 = fig.add_axes([0.56, 0.17, 0.24, 0.57])
    for i, c in enumerate(orden):
        m24, m25 = p.loc[c, ("margen_pct", 2024)], p.loc[c, ("margen_pct", 2025)]
        col = NARANJA if c == "Tienda online" else AZUL
        ax2.plot([m24, m25], [i, i], color=EJE, lw=2, zorder=2)
        ax2.scatter(m24, i, s=70, color=GRIS_SERIE, edgecolor=SUP, linewidth=2, zorder=3)
        ax2.scatter(m25, i, s=70, color=col, edgecolor=SUP, linewidth=2, zorder=4)
        ax2.text(m25 - 0.012, i, pct(m25), ha="right", va="center", fontsize=11, color=TXT1)
    ax2.set_yticks(y, [""] * len(y))
    ax2.set_ylim(len(orden) - 0.5, -0.5)
    ax2.set_xlim(0.28, 0.56)
    ax2.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v * 100:.0f} %"))
    ejes_limpios(ax2, grid_y=False)
    ax2.spines["left"].set_visible(False)
    ax2.set_title("Margen bruto %", loc="left", fontsize=13, pad=12)
    leg = [plt.Line2D([], [], marker="o", ls="", color=GRIS_SERIE, markersize=9, label="2024"),
           plt.Line2D([], [], marker="o", ls="", color=AZUL, markersize=9, label="2025")]
    ax2.legend(handles=leg, loc="lower right", bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=11, ncol=2, handletextpad=0.2, columnspacing=0.8)

    # Panel 3: ticket promedio
    fig.text(0.835, 0.76, "Ticket promedio 2025", fontsize=13, color=TXT1)
    ax3 = fig.add_axes([0.835, 0.17, 0.12, 0.57])
    ax3.set_ylim(len(orden) - 0.5, -0.5)
    ax3.axis("off")
    for i, c in enumerate(orden):
        ax3.text(0, i, f"$ {miles(p.loc[c, ('ticket_promedio', 2025)])}", va="center", fontsize=12.5,
                 font={"family": "Segoe UI"})
    fig.text(0.05, 0.085, f"La tienda online pasó de un descuento promedio de {pct(d['ind']['descuento_online_h1_2025'])} "
                          f"(1.er semestre 2025) a {pct(d['ind']['descuento_online_h2_2025'])} (2.º semestre).",
             fontsize=11.5, color=TXT2)
    fig.savefig(IMG / "03_canales.png")
    plt.close(fig)


# ------------------------------------------------------------------ 4. Pareto
def pareto_img(d):
    par = d["pareto_productos"]
    ind = d["ind"]
    top20 = ind["pct_ventas_top20pct_productos"]
    fig = lienzo(f"El 20 % de los productos genera el {pct(top20, 0)} de las ventas",
                 f"Curva de Pareto y 10 productos más vendidos en 2025 ({int(ind['productos_total'])} referencias)",
                 "Análisis de productos (ABC)")
    ax = fig.add_axes([0.085, 0.14, 0.36, 0.6])
    x = np.concatenate([[0], par.pct_productos])
    yv = np.concatenate([[0], par.pct_ventas_acum])
    ax.fill_between(x, yv, color=AZUL, alpha=0.10, lw=0)
    ax.plot(x, yv, color=AZUL, lw=2, zorder=3)
    ax.plot([0.2, 0.2], [0, top20], color=TXT2, lw=1, zorder=2)
    ax.plot([0, 0.2], [top20, top20], color=TXT2, lw=1, zorder=2)
    ax.scatter(0.2, top20, s=60, color=AZUL, edgecolor=SUP, linewidth=2, zorder=4)
    ax.annotate(f"20 % de productos → {pct(top20, 0)} de ventas", (0.2, top20), xytext=(12, -14),
                textcoords="offset points", fontsize=11.5, color=TXT1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v * 100:.0f} %"))
    ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v * 100:.0f} %"))
    ax.set_xlabel("% de productos (de mayor a menor venta)", fontsize=11.5, labelpad=8)
    ax.tick_params(axis="x", pad=8)
    ejes_limpios(ax)
    ax.set_title("% acumulado de ventas", loc="left", fontsize=13.5, pad=12)

    top = par.head(10)
    ax2 = fig.add_axes([0.66, 0.14, 0.2, 0.6])
    yy = np.arange(len(top))
    ax2.barh(yy, top.venta_neta, height=0.55, color=[AZUL if i == 0 else AZUL_CLARO for i in range(len(top))], zorder=3)
    for i, r in top.reset_index().iterrows():
        ax2.text(r.venta_neta + 1e7, i, f"{millones(r.venta_neta)}", va="center", fontsize=11,
                 weight="semibold" if i == 0 else "normal")
    ax2.set_yticks(yy, top.nombre_producto.str.replace("Café en grano", "Grano").str.replace("Café molido", "Molido"),
                   fontsize=11.5, color=TXT1)
    ax2.invert_yaxis()
    ax2.set_xlim(0, top.venta_neta.max() * 1.45)
    ax2.set_xticks([])
    ejes_limpios(ax2, grid_y=False)
    ax2.spines["bottom"].set_visible(False)
    ax2.set_title("Top 10 productos · ventas 2025", loc="left", fontsize=13.5, pad=12)
    fig.text(0.56, 0.085, f"La referencia estrella (Grano Huila 500 g) aporta el {pct(ind['estrella_pct_ventas_2025'], 0)} "
                          f"de las ventas,\npero su margen bajó de {pct(ind['estrella_margen_2024'], 0)} a "
                          f"{pct(ind['estrella_margen_2025_desde_abr'], 0)} (precio sin ajustar).",
             fontsize=11, color=TXT2, ha="left", linespacing=1.35)
    fig.savefig(IMG / "04_pareto_productos.png")
    plt.close(fig)


# ------------------------------------------------------------------ 5. Clientes RFM
def rfm_img(d):
    s = d["rfm_segmentos"].set_index("segmento")
    ind = d["ind"]
    orden = ["Campeones", "Leales", "Potenciales", "Nuevos", "Necesitan atención", "En riesgo", "Perdidos"]
    s = s.reindex(orden)
    camp = s.loc["Campeones"]
    fig = lienzo(f"El {pct(camp.pct_clientes, 0)} de los clientes genera el {pct(camp.pct_ventas_2025, 0)} de las ventas",
                 "Segmentación RFM (recencia, frecuencia y monto) de los clientes · corte dic-2025",
                 "Análisis de clientes (RFM)")
    ax = fig.add_axes([0.2, 0.14, 0.48, 0.6])
    y = np.arange(len(orden))
    h = 0.34
    ax.barh(y - h / 2 - 0.02, s.pct_clientes, height=h, color=GRIS_SERIE, zorder=3)
    ax.barh(y + h / 2 + 0.02, s.pct_ventas_2025, height=h, color=AZUL, zorder=3)
    for i, c in enumerate(orden):
        ax.text(s.loc[c, "pct_clientes"] + 0.008, i - h / 2 - 0.02, f"{pct(s.loc[c, 'pct_clientes'], 0)} · {miles(s.loc[c, 'clientes'])} clientes",
                va="center", fontsize=10.5, color=TXT2)
        ax.text(s.loc[c, "pct_ventas_2025"] + 0.008, i + h / 2 + 0.02, pct(s.loc[c, "pct_ventas_2025"], 0),
                va="center", fontsize=10.5, color=TXT1)
    ax.set_yticks(y, orden, fontsize=12.5, color=TXT1)
    ax.invert_yaxis()
    ax.set_xlim(0, 0.8)
    ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v * 100:.0f} %"))
    ejes_limpios(ax, grid_y=False)
    leg = [plt.Rectangle((0, 0), 1, 1, color=GRIS_SERIE, label="% de clientes"),
           plt.Rectangle((0, 0), 1, 1, color=AZUL, label="% de ventas 2025")]
    ax.legend(handles=leg, loc="lower right", frameon=False, fontsize=11.5)

    x0, w = 0.75, 0.2
    tarjeta(fig, x0, 0.575, w, 0.175, "Clientes que recompran", pct(ind["recompra_pct"], 0), "2 o más compras en 2 años")
    tarjeta(fig, x0, 0.385, w, 0.175, "Retención 2024 → 2025", pct(ind["retencion_2024_2025"], 0), "compraron en ambos años")
    tarjeta(fig, x0, 0.195, w, 0.175, "Clientes en riesgo", miles(ind["clientes_en_riesgo"]),
            f"gastaban $ {miles(ind['gasto_anual_cliente_en_riesgo'] / 1e3)} mil al año", CRITICO)
    fig.text(x0, 0.17, "Eran frecuentes y llevan más de\nun año sin comprar: el público ideal\npara una campaña de reactivación.",
             fontsize=11, color=TXT2, va="top", linespacing=1.4)
    fig.savefig(IMG / "05_clientes_rfm.png")
    plt.close(fig)


# ------------------------------------------------------------------ 6. Recomendaciones
def recomendaciones(d):
    r = d["recomendaciones"]
    ka = d["kpis_anuales"].set_index("anio")
    total = r.margen_anual_prudente.sum()
    fig = lienzo("Tres acciones para recuperar margen",
                 "Impacto estimado en margen bruto anual (COP) · escenario prudente y escenario con el mismo volumen",
                 "Recomendaciones")
    textos = [
        ("Limitar el descuento\nonline al 10 %", "Los descuentos de 20-30 % traen volumen,\npero ese volumen deja poco margen.",
         "Supuesto prudente: las ventas con\ndescuento > 10 % caen 30 %."),
        ("Subir 10 % el precio del\nGrano Huila 500 g", "Es la referencia n.º 1 y es la única que\nno trasladó el alza del café verde.",
         "Supuesto prudente: su volumen\ncae 8 %."),
        ("Reactivar clientes\n'En riesgo'", f"{miles(d['ind']['clientes_en_riesgo'])} clientes frecuentes llevan más\nde un año sin comprar.",
         "Supuesto: se reactiva el 20 % con\nsu gasto anual promedio."),
    ]
    for i, (tit, por, sup) in enumerate(textos):
        x, y0, w, h = 0.05 + i * 0.305, 0.2, 0.285, 0.58
        fig.add_artist(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                      transform=fig.transFigure, fc=PLANO, ec=GRID, lw=1))
        fig.text(x + 0.02, y0 + h - 0.05, f"{i + 1}", fontsize=15, weight="semibold", color=AZUL, va="top")
        fig.text(x + 0.05, y0 + h - 0.05, tit, fontsize=15, weight="semibold", va="top", linespacing=1.25)
        fig.text(x + 0.02, y0 + h - 0.17, por, fontsize=11.5, color=TXT2, va="top", linespacing=1.4)
        pru, mismo = r.margen_anual_prudente.iloc[i], r.margen_anual_mismo_volumen.iloc[i]
        fig.text(x + 0.02, y0 + 0.235, "Margen anual recuperable", fontsize=11.5, color=TXT2)
        rango = millones(pru) if abs(pru - mismo) < 1e6 else f"{millones(pru)} – {miles(mismo / 1e6)} M"
        fig.text(x + 0.02, y0 + 0.165, rango, fontsize=26, weight="semibold")
        fig.text(x + 0.02, y0 + 0.03, sup, fontsize=10.5, color=MUTED, linespacing=1.35)
    fig.text(0.05, 0.11, f"En conjunto: al menos {millones(total)} de margen bruto al año, "
                         f"{pct(total / ka.loc[2025, 'margen_bruto'], 0)} del margen de 2025.",
             fontsize=14, weight="semibold")
    fig.savefig(IMG / "06_recomendaciones.png")
    plt.close(fig)


if __name__ == "__main__":
    datos = cargar()
    for f in (portada, resumen, margen, canales, pareto_img, rfm_img, recomendaciones):
        f(datos)
        print("ok", f.__name__)
