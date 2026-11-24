"""
Genera datos SINTÉTICOS de ventas de "Granorte Café", una tostadora de café de
especialidad INVENTADA (pyme colombiana, precios en COP). Ningún dato es real.

Historia incluida en los datos (lo que el análisis debe descubrir):
  - Las ventas crecen en 2025, pero el margen bruto cae porque:
    a) desde julio de 2025 la tienda online da descuentos agresivos (20-30 %);
    b) desde marzo de 2025 sube el costo del café verde (+22 %). En abril se
       ajustan los precios del café, excepto el de la referencia estrella
       (Café en grano Huila 500 g), que mantiene el precio de 2024.

Salida (carpeta ../datos), modelo estrella:
  ventas.csv     hechos: una fila por línea de factura
  productos.csv  dimensión de productos
  clientes.csv   dimensión de clientes
  canales.csv    dimensión de canales y sedes

Uso:  python generar_datos.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(2025)
SALIDA = Path(__file__).resolve().parent.parent / "datos"
SALIDA.mkdir(exist_ok=True)

DIAS = pd.date_range("2024-01-01", "2025-12-31", freq="D")
ESTRELLA = "P001"
INICIO_DESCUENTOS = pd.Timestamp("2025-07-01")
ALZA_COSTO = pd.Timestamp("2025-03-01")
AJUSTE_PRECIO = pd.Timestamp("2025-04-01")
CAFE = {"Café en grano", "Café molido", "Cápsulas"}


# ------------------------------------------------------------------ productos
def crear_productos() -> pd.DataFrame:
    filas = []
    origenes = {"Huila": 36_000, "Nariño": 38_000, "Sierra Nevada": 37_000, "Tolima": 33_000,
                "Cauca": 35_000, "Quindío": 34_000, "Santander": 32_000, "Blend Casa": 28_000}
    tam = {"250 g": 1.0, "500 g": 1.8, "1 kg": 3.3}
    for o, p in origenes.items():
        for t, f in tam.items():
            filas.append(("Café en grano", f"Café en grano {o} {t}", t, p * f, 0.45))
    for o in ["Huila", "Nariño", "Tolima", "Cauca", "Quindío", "Blend Casa"]:
        for t in ["250 g", "500 g"]:
            filas.append(("Café molido", f"Café molido {o} {t}", t, origenes[o] * tam[t] * 0.97, 0.45))
    for n, p in [("Huila", 32_000), ("Nariño", 33_000), ("Blend Casa", 28_000), ("Descafeinado", 34_000),
                 ("Intenso", 30_000), ("Vainilla", 31_000)]:
        filas.append(("Cápsulas", f"Cápsulas {n} x10", "Caja x10", p, 0.50))
    for n, p in [("Gotero V60", 65_000), ("Chemex 6 tazas", 240_000), ("Prensa francesa", 95_000),
                 ("Aeropress", 210_000), ("Cafetera moka", 120_000), ("Sifón japonés", 330_000),
                 ("Kalita Wave", 150_000)]:
        filas.append(("Métodos de preparación", n, "Unidad", p, 0.62))
    for n, p in [("Filtros V60 x100", 22_000), ("Filtros Chemex x100", 45_000), ("Molino manual", 180_000),
                 ("Báscula digital", 120_000), ("Termo 500 ml", 85_000), ("Taza de cerámica", 35_000),
                 ("Hervidor cuello de cisne", 260_000), ("Kit barista", 95_000)]:
        filas.append(("Accesorios", n, "Unidad", p, 0.55))
    for n, p in [("Espresso", 6_000), ("Americano", 7_000), ("Capuchino", 10_000), ("Latte", 11_000),
                 ("Filtrado V60", 12_000), ("Cold brew", 13_000), ("Mocaccino", 12_000), ("Affogato", 14_000)]:
        filas.append(("Bebidas en tienda", n, "Bebida", p, 0.30))

    df = pd.DataFrame(filas, columns=["categoria", "nombre_producto", "presentacion", "precio_2024", "costo_pct"])
    # La referencia estrella va primero (P001)
    i = df.index[df.nombre_producto == "Café en grano Huila 500 g"][0]
    df = pd.concat([df.loc[[i]], df.drop(i)], ignore_index=True)
    df["precio_2024"] = (df["precio_2024"] / 500).round() * 500
    df["costo_2024"] = (df["precio_2024"] * df["costo_pct"] * rng.uniform(0.93, 1.07, len(df))).round(-1)
    df.insert(0, "id_producto", [f"P{i:03d}" for i in range(1, len(df) + 1)])
    return df.drop(columns="costo_pct")


def precio_costo(prod: pd.DataFrame, fecha: pd.Timestamp):
    """Precio y costo vigentes en una fecha."""
    precio = prod["precio_2024"].to_numpy(dtype=float).copy()
    costo = prod["costo_2024"].to_numpy(dtype=float).copy()
    es_cafe = prod["categoria"].isin(CAFE).to_numpy()
    es_bebida = (prod["categoria"] == "Bebidas en tienda").to_numpy()
    estrella = (prod["id_producto"] == ESTRELLA).to_numpy()
    if fecha.year >= 2025:                       # inflación de enero
        precio = np.where(estrella, precio, precio * 1.05)
        costo = costo * 1.04
    if fecha >= ALZA_COSTO:                      # sube el café verde
        costo = np.where(es_cafe, costo * 1.22, np.where(es_bebida, costo * 1.12, costo))
    if fecha >= AJUSTE_PRECIO:                   # se traslada al precio... salvo a la estrella
        precio = np.where(es_cafe & ~estrella, precio * 1.09, precio)
        precio = np.where(es_bebida, precio * 1.05, precio)
    return (np.round(precio / 100) * 100), np.round(costo, -1)


# ------------------------------------------------------------------ canales
CANALES = pd.DataFrame({
    "id_canal": ["C01", "C02", "C03", "C04", "C05"],
    "canal": ["Tienda Chapinero", "Tienda Usaquén", "Tienda El Poblado", "Tienda online", "Mayoristas"],
    "tipo_canal": ["Tienda física", "Tienda física", "Tienda física", "Online", "Mayorista"],
    "ciudad": ["Bogotá", "Bogotá", "Medellín", "Nacional", "Nacional"],
})
FACTURAS_DIA = {"C01": 24, "C02": 19, "C03": 17, "C04": 11, "C05": 2.0}
CLIENTES_CANAL = {"C01": 1250, "C02": 980, "C03": 880, "C04": 950, "C05": 90}
MEZCLA = {  # participación de líneas por categoría
    "tienda": {"Bebidas en tienda": 0.55, "Café en grano": 0.20, "Café molido": 0.12, "Cápsulas": 0.05,
               "Métodos de preparación": 0.03, "Accesorios": 0.05},
    "C04": {"Café en grano": 0.40, "Café molido": 0.22, "Cápsulas": 0.18, "Métodos de preparación": 0.09,
            "Accesorios": 0.11},
    "C05": {"Café en grano": 0.85, "Café molido": 0.15},
}
ESTACIONALIDAD = [0.88, 0.90, 0.95, 0.95, 1.00, 0.98, 1.00, 1.00, 0.97, 1.02, 1.12, 1.45]


def crear_clientes() -> pd.DataFrame:
    filas = []
    n = 0
    ciudades_tienda = {"C01": "Bogotá", "C02": "Bogotá", "C03": "Medellín"}
    for canal, k in CLIENTES_CANAL.items():
        extra = 380 if canal == "C04" else 0      # clientes que llegan atraídos por los descuentos
        total = k + extra
        antiguos = rng.random(total) < 0.55
        inicio = np.where(
            antiguos,
            pd.Timestamp("2023-01-01").value + rng.random(total) * (pd.Timestamp("2023-12-31").value - pd.Timestamp("2023-01-01").value),
            pd.Timestamp("2024-01-01").value + rng.random(total) * (pd.Timestamp("2025-11-30").value - pd.Timestamp("2024-01-01").value),
        )
        if extra:
            ini_extra = INICIO_DESCUENTOS.value + rng.random(extra) * (pd.Timestamp("2025-12-15").value - INICIO_DESCUENTOS.value)
            inicio[-extra:] = ini_extra
        vida_meses = rng.exponential(20 if canal != "C05" else 40, total)
        fin = inicio + vida_meses * 30.4 * 86_400e9
        if canal == "C04":
            ciudad = rng.choice(["Bogotá", "Medellín", "Cali", "Barranquilla", "Bucaramanga", "Pereira", "Otras"],
                                total, p=[0.38, 0.18, 0.12, 0.08, 0.07, 0.05, 0.12])
        elif canal == "C05":
            ciudad = rng.choice(["Bogotá", "Medellín", "Cali"], total, p=[0.6, 0.3, 0.1])
        else:
            ciudad = np.full(total, ciudades_tienda[canal])
        peso = rng.lognormal(0, 0.9, total)
        if extra:
            peso[-extra:] *= 0.6
        for j in range(total):
            n += 1
            filas.append((f"CL{n:05d}", "Empresa" if canal == "C05" else "Persona", ciudad[j], canal,
                          inicio[j], fin[j], peso[j], extra and j >= k))
    df = pd.DataFrame(filas, columns=["id_cliente", "tipo_cliente", "ciudad", "id_canal_principal",
                                      "_inicio", "_fin", "_peso", "_por_descuento"])
    df["_inicio"] = pd.to_datetime(df["_inicio"].astype("int64"))
    df["_fin"] = pd.to_datetime(df["_fin"].astype("int64"))
    return df


def factor_dia(d: pd.Timestamp, canal: str) -> float:
    f = ESTACIONALIDAD[d.month - 1]
    if d.day in (1, 15, 16, 30, 31):          # quincenas
        f *= 1.35
    if canal in ("C01", "C02", "C03") and d.day_of_week == 5:
        f *= 1.25
    if canal in ("C01", "C02", "C03") and d.day_of_week == 6:
        f *= 0.8
    if canal == "C05" and d.day_of_week >= 5:
        f *= 0.2
    # crecimiento del negocio
    t = (d - pd.Timestamp("2024-01-01")).days / 365
    crec = {"C01": 0.05, "C02": 0.05, "C03": 0.07, "C04": 0.08, "C05": 0.03}[canal]
    f *= 1 + crec * t
    if canal == "C04" and d >= INICIO_DESCUENTOS:  # los descuentos traen volumen
        f *= 1.35
    return f


def main():
    prod = crear_productos()
    cli = crear_clientes()
    precios = {}
    lineas = []
    n_fact = 0
    pesos_prod = {}
    for clave, mezcla in MEZCLA.items():
        w = np.zeros(len(prod))
        for cat, share in mezcla.items():
            m = (prod["categoria"] == cat).to_numpy()
            idx = np.flatnonzero(m)
            zipf = 1 / np.arange(1, len(idx) + 1) ** 2.1
            orden = rng.permutation(len(idx))
            zipf = zipf[orden]
            if cat == "Café en grano":
                zipf[0] = zipf.max() * 2.2    # la estrella (P001) es la más vendida
            if clave == "C05" and cat == "Café en grano":
                es_kg = prod.loc[idx, "presentacion"].eq("1 kg").to_numpy()
                zipf = np.where(es_kg, zipf * 6, zipf)
                zipf[0] = zipf.max() * 2.0
            w[idx] = share * zipf / zipf.sum()
        pesos_prod[clave] = w / w.sum()

    for d in DIAS:
        clave_mes = (d.year, d.month >= 4 and d.year == 2025, d >= ALZA_COSTO)
        if clave_mes not in precios:
            precios[clave_mes] = precio_costo(prod, d)
        p_vig, c_vig = precios[clave_mes]
        for canal, base in FACTURAS_DIA.items():
            n = rng.poisson(base * factor_dia(d, canal))
            if n == 0:
                continue
            pool = cli[(cli.id_canal_principal == canal) & (cli._inicio <= d) & (cli._fin >= d)]
            if pool.empty:
                continue
            w = pool["_peso"].to_numpy()
            if canal == "C04" and d < INICIO_DESCUENTOS:
                w = np.where(pool["_por_descuento"], 0, w)
            if w.sum() == 0:
                continue
            clientes = rng.choice(pool["id_cliente"].to_numpy(), n, p=w / w.sum())
            clave = canal if canal in ("C04", "C05") else "tienda"
            for c in clientes:
                n_fact += 1
                if canal == "C05":
                    k = rng.integers(2, 6)
                elif canal == "C04":
                    k = rng.choice([1, 2, 3, 4], p=[0.35, 0.35, 0.2, 0.1])
                else:
                    k = rng.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
                items = rng.choice(len(prod), k, replace=False, p=pesos_prod[clave])
                for linea, it in enumerate(items, 1):
                    cat = prod.at[it, "categoria"]
                    if canal == "C05":
                        cant = int(rng.integers(2, 13))
                        desc = 0.12
                    elif canal == "C04":
                        cant = int(rng.choice([1, 2, 3], p=[0.7, 0.22, 0.08]))
                        if d >= INICIO_DESCUENTOS:
                            desc = float(rng.choice([0, 0.20, 0.25, 0.30], p=[0.25, 0.25, 0.30, 0.20]))
                        else:
                            desc = 0.10 if rng.random() < 0.30 else 0.0
                    else:
                        cant = int(rng.choice([1, 2], p=[0.8, 0.2])) if cat == "Bebidas en tienda" else 1
                        desc = 0.10 if rng.random() < 0.12 else 0.0
                    lineas.append((f"F{n_fact:06d}", linea, d, c, prod.at[it, "id_producto"], canal,
                                   cant, p_vig[it], desc, c_vig[it]))

    v = pd.DataFrame(lineas, columns=["id_factura", "linea", "fecha", "id_cliente", "id_producto", "id_canal",
                                      "cantidad", "precio_unitario", "descuento_pct", "costo_unitario"])
    v["precio_unitario"] = v["precio_unitario"].astype(np.int64)
    v["costo_unitario"] = v["costo_unitario"].astype(np.int64)
    v["venta_neta"] = (v["cantidad"] * v["precio_unitario"] * (1 - v["descuento_pct"])).round().astype(np.int64)
    v["costo_total"] = (v["cantidad"] * v["costo_unitario"]).astype(np.int64)
    v["fecha"] = v["fecha"].dt.strftime("%Y-%m-%d")

    p_fin, c_fin = precio_costo(prod, pd.Timestamp("2025-12-31"))
    productos = prod[["id_producto", "nombre_producto", "categoria", "presentacion"]].copy()
    productos["precio_lista_actual"] = p_fin.astype(np.int64)
    productos["costo_unitario_actual"] = c_fin.astype(np.int64)

    primera = v.groupby("id_cliente")["fecha"].min()
    clientes = cli[cli.id_cliente.isin(primera.index)][["id_cliente", "tipo_cliente", "ciudad", "id_canal_principal"]].copy()
    clientes["fecha_primera_compra"] = clientes["id_cliente"].map(primera)

    v.to_csv(SALIDA / "ventas.csv", index=False, encoding="utf-8")
    productos.to_csv(SALIDA / "productos.csv", index=False, encoding="utf-8")
    clientes.to_csv(SALIDA / "clientes.csv", index=False, encoding="utf-8")
    CANALES.to_csv(SALIDA / "canales.csv", index=False, encoding="utf-8")
    print(f"ventas.csv: {len(v):,} líneas, {v.id_factura.nunique():,} facturas")
    print(f"productos.csv: {len(productos)} | clientes.csv: {len(clientes):,} | canales.csv: {len(CANALES)}")


if __name__ == "__main__":
    main()
