# Modelo y medidas DAX · Dashboard de ventas Granorte Café

## Modelo (esquema estrella)

| Tabla | Tipo | Origen | Relación |
|---|---|---|---|
| `ventas` | Hechos (1 fila por línea de factura) | `datos/ventas.csv` | — |
| `productos` | Dimensión | `datos/productos.csv` | `productos[id_producto]` 1 → * `ventas[id_producto]` |
| `clientes` | Dimensión | `datos/clientes.csv` | `clientes[id_cliente]` 1 → * `ventas[id_cliente]` |
| `canales` | Dimensión | `datos/canales.csv` | `canales[id_canal]` 1 → * `ventas[id_canal]` |
| `Calendario` | Dimensión (DAX) | tabla calculada | `Calendario[Date]` 1 → * `ventas[fecha]` |
| `rfm_clientes`, `pareto_productos`, `puente_margen`, `recomendaciones` | Apoyo | `datos/resultados/*.csv` | `rfm_clientes[id_cliente]` 1 → 1 `clientes[id_cliente]` (opcional) |

Al importar los CSV en Power Query: origen de archivo **65001 (UTF-8)**, delimitador **coma**, configuración regional **Inglés (Estados Unidos)** para que `0.25` se lea como número. Marca `Calendario` como tabla de fechas.

```DAX
Calendario =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2025, 12, 31 ) ),
    "Año", YEAR ( [Date] ),
    "Mes", FORMAT ( [Date], "mmm" ),
    "MesNum", MONTH ( [Date] ),
    "AñoMes", FORMAT ( [Date], "yyyy-mm" ),
    "Trimestre", "T" & QUARTER ( [Date] ),
    "Semestre", IF ( MONTH ( [Date] ) <= 6, "S1", "S2" ),
    "Quincena", IF ( DAY ( [Date] ) IN { 1, 15, 16, 30, 31 }, "Día de quincena", "Otro día" ),
    "DíaSemana", FORMAT ( [Date], "dddd" )
)
```

## Medidas base

```DAX
Ventas = SUM ( ventas[venta_neta] )

Ventas Brutas = SUMX ( ventas, ventas[cantidad] * ventas[precio_unitario] )

Costo = SUM ( ventas[costo_total] )

Margen Bruto = [Ventas] - [Costo]

Margen % = DIVIDE ( [Margen Bruto], [Ventas] )

Unidades = SUM ( ventas[cantidad] )

Facturas = DISTINCTCOUNT ( ventas[id_factura] )

Ticket Promedio = DIVIDE ( [Ventas], [Facturas] )

Clientes Activos = DISTINCTCOUNT ( ventas[id_cliente] )

Descuento % = 1 - DIVIDE ( [Ventas], [Ventas Brutas] )

Valor Descuento = [Ventas Brutas] - [Ventas]

Precio Promedio = DIVIDE ( [Ventas], [Unidades] )
```

## Comparación con el año anterior

```DAX
Ventas AA = CALCULATE ( [Ventas], SAMEPERIODLASTYEAR ( Calendario[Date] ) )

Var % Ventas AA = DIVIDE ( [Ventas] - [Ventas AA], [Ventas AA] )

Margen Bruto AA = CALCULATE ( [Margen Bruto], SAMEPERIODLASTYEAR ( Calendario[Date] ) )

Var % Margen Bruto AA = DIVIDE ( [Margen Bruto] - [Margen Bruto AA], [Margen Bruto AA] )

Margen % AA = CALCULATE ( [Margen %], SAMEPERIODLASTYEAR ( Calendario[Date] ) )

Var Margen pp = ( [Margen %] - [Margen % AA] ) * 100

Ticket Promedio AA = CALCULATE ( [Ticket Promedio], SAMEPERIODLASTYEAR ( Calendario[Date] ) )

Clientes Activos AA = CALCULATE ( [Clientes Activos], SAMEPERIODLASTYEAR ( Calendario[Date] ) )

Ventas Acumuladas Año = TOTALYTD ( [Ventas], Calendario[Date] )
```

## Productos (Pareto / ABC)

```DAX
% Participación Ventas =
DIVIDE ( [Ventas], CALCULATE ( [Ventas], ALL ( productos ) ) )

Ranking Producto =
RANKX ( ALL ( productos ), [Ventas], , DESC, DENSE )

% Ventas Acumulado =
VAR VentasProducto = [Ventas]
VAR Acumulado =
    SUMX (
        FILTER (
            ALL ( productos ),
            CALCULATE ( [Ventas] ) >= VentasProducto
        ),
        CALCULATE ( [Ventas] )
    )
RETURN
    DIVIDE ( Acumulado, CALCULATE ( [Ventas], ALL ( productos ) ) )

Clase ABC =
SWITCH (
    TRUE (),
    [% Ventas Acumulado] <= 0.80, "A",
    [% Ventas Acumulado] <= 0.95, "B",
    "C"
)
```

## Clientes

```DAX
Clientes Recompra =
COUNTROWS (
    FILTER (
        VALUES ( ventas[id_cliente] ),
        CALCULATE ( DISTINCTCOUNT ( ventas[id_factura] ) ) >= 2
    )
)

% Recompra = DIVIDE ( [Clientes Recompra], [Clientes Activos] )

Clientes Retenidos =
VAR ClientesAA =
    CALCULATETABLE ( VALUES ( ventas[id_cliente] ), SAMEPERIODLASTYEAR ( Calendario[Date] ) )
VAR ClientesActual = VALUES ( ventas[id_cliente] )
RETURN
    COUNTROWS ( INTERSECT ( ClientesActual, ClientesAA ) )

% Retención = DIVIDE ( [Clientes Retenidos], [Clientes Activos AA] )

Ventas por Cliente = DIVIDE ( [Ventas], [Clientes Activos] )
```

## Formato condicional

```DAX
Color Margen =
SWITCH (
    TRUE (),
    [Margen %] >= 0.48, "#0ca30c",
    [Margen %] >= 0.42, "#fab219",
    "#d03b3b"
)

Color Var AA = IF ( [Var % Ventas AA] >= 0, "#006300", "#d03b3b" )
```

## Páginas sugeridas del tablero

1. **Resumen:** tarjetas (Ventas, Margen %, Ticket Promedio, Clientes Activos con su variación AA), líneas de ventas mensuales 2024 vs. 2025, segmentadores de canal, categoría y año.
2. **Rentabilidad:** línea de Margen % mensual + gráfico de cascada con la tabla `puente_margen`.
3. **Canales:** barras de Ventas y Var % AA por canal, Margen % por canal y año, Ticket Promedio y Descuento % por canal.
4. **Productos:** curva de % Ventas Acumulado y, en un visual aparte, barras del top 10 por Ventas (evita el gráfico combinado con dos ejes), más una tabla con Clase ABC y Margen % por producto.
5. **Clientes:** barras de clientes y ventas por segmento RFM (`rfm_clientes`), tarjetas de % Recompra y % Retención.
6. **Recomendaciones:** tabla `recomendaciones` + parámetro *What-if* "Tope de descuento online" para simular el margen recuperado.
