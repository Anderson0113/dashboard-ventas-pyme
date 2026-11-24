/* =====================================================================
   Caso de portafolio: Dashboard de ventas para pymes (Granorte Café, ficticia)
   Motor: SQL Server (T-SQL)
   Tablas: dbo.ventas, dbo.productos, dbo.clientes, dbo.canales
           (cargadas desde los CSV de /datos, UTF-8, separador coma, punto decimal)
   NOTA: estas consultas NO se ejecutaron contra un SQL Server real; la lógica
         replica el análisis en Python (scripts/analisis_ventas.py). Pruébalas
         en tu entorno antes de usarlas.
   Autor: Anderson Barrero
   ===================================================================== */

/* ---------------------------------------------------------------------
   0. Estructura (modelo estrella)
   --------------------------------------------------------------------- */
CREATE TABLE dbo.canales (
    id_canal    CHAR(3)      NOT NULL PRIMARY KEY,
    canal       VARCHAR(40)  NOT NULL,
    tipo_canal  VARCHAR(20)  NOT NULL,
    ciudad      VARCHAR(30)  NOT NULL
);

CREATE TABLE dbo.productos (
    id_producto            CHAR(4)      NOT NULL PRIMARY KEY,
    nombre_producto        VARCHAR(60)  NOT NULL,
    categoria              VARCHAR(30)  NOT NULL,
    presentacion           VARCHAR(20)  NOT NULL,
    precio_lista_actual    INT          NOT NULL,
    costo_unitario_actual  INT          NOT NULL
);

CREATE TABLE dbo.clientes (
    id_cliente            CHAR(7)      NOT NULL PRIMARY KEY,
    tipo_cliente          VARCHAR(10)  NOT NULL,
    ciudad                VARCHAR(30)  NOT NULL,
    id_canal_principal    CHAR(3)      NOT NULL REFERENCES dbo.canales(id_canal),
    fecha_primera_compra  DATE         NOT NULL
);

CREATE TABLE dbo.ventas (
    id_factura       CHAR(7)       NOT NULL,
    linea            TINYINT       NOT NULL,
    fecha            DATE          NOT NULL,
    id_cliente       CHAR(7)       NOT NULL REFERENCES dbo.clientes(id_cliente),
    id_producto      CHAR(4)       NOT NULL REFERENCES dbo.productos(id_producto),
    id_canal         CHAR(3)       NOT NULL REFERENCES dbo.canales(id_canal),
    cantidad         INT           NOT NULL,
    precio_unitario  INT           NOT NULL,
    descuento_pct    DECIMAL(4,2)  NOT NULL,
    costo_unitario   INT           NOT NULL,
    venta_neta       BIGINT        NOT NULL,   -- cantidad * precio_unitario * (1 - descuento_pct)
    costo_total      BIGINT        NOT NULL,   -- cantidad * costo_unitario
    CONSTRAINT PK_ventas PRIMARY KEY (id_factura, linea)
);
CREATE INDEX IX_ventas_fecha ON dbo.ventas (fecha) INCLUDE (venta_neta, costo_total, id_canal, id_producto);


/* ---------------------------------------------------------------------
   1. KPIs anuales: ventas, margen bruto, ticket promedio, clientes activos
   --------------------------------------------------------------------- */
SELECT
    YEAR(v.fecha)                                             AS anio,
    SUM(v.venta_neta)                                         AS ventas,
    SUM(v.costo_total)                                        AS costo,
    SUM(v.venta_neta) - SUM(v.costo_total)                    AS margen_bruto,
    CAST(SUM(v.venta_neta) - SUM(v.costo_total) AS FLOAT)
        / NULLIF(SUM(v.venta_neta), 0)                        AS margen_pct,
    COUNT(DISTINCT v.id_factura)                              AS facturas,
    CAST(SUM(v.venta_neta) AS FLOAT) / COUNT(DISTINCT v.id_factura) AS ticket_promedio,
    COUNT(DISTINCT v.id_cliente)                              AS clientes_activos,
    1 - CAST(SUM(v.venta_neta) AS FLOAT)
        / NULLIF(SUM(CAST(v.cantidad AS BIGINT) * v.precio_unitario), 0) AS descuento_pct
FROM dbo.ventas AS v
GROUP BY YEAR(v.fecha)
ORDER BY anio;


/* ---------------------------------------------------------------------
   2. Ventas y margen mensual con variación frente al mismo mes del año anterior
   --------------------------------------------------------------------- */
WITH mensual AS (
    SELECT
        DATEFROMPARTS(YEAR(fecha), MONTH(fecha), 1)           AS mes,
        SUM(venta_neta)                                       AS ventas,
        CAST(SUM(venta_neta) - SUM(costo_total) AS FLOAT) / NULLIF(SUM(venta_neta), 0) AS margen_pct
    FROM dbo.ventas
    GROUP BY DATEFROMPARTS(YEAR(fecha), MONTH(fecha), 1)
)
SELECT
    mes,
    ventas,
    margen_pct,
    CAST(ventas AS FLOAT) / NULLIF(LAG(ventas, 12) OVER (ORDER BY mes), 0) - 1 AS var_ventas_aa,
    margen_pct - LAG(margen_pct, 12) OVER (ORDER BY mes)                    AS var_margen_pp
FROM mensual
ORDER BY mes;


/* ---------------------------------------------------------------------
   3. Desempeño por canal (2024 vs. 2025)
   --------------------------------------------------------------------- */
SELECT
    c.canal,
    YEAR(v.fecha)                                             AS anio,
    SUM(v.venta_neta)                                         AS ventas,
    CAST(SUM(v.venta_neta) - SUM(v.costo_total) AS FLOAT) / NULLIF(SUM(v.venta_neta), 0) AS margen_pct,
    CAST(SUM(v.venta_neta) AS FLOAT) / COUNT(DISTINCT v.id_factura) AS ticket_promedio,
    1 - CAST(SUM(v.venta_neta) AS FLOAT)
        / NULLIF(SUM(CAST(v.cantidad AS BIGINT) * v.precio_unitario), 0) AS descuento_pct
FROM dbo.ventas AS v
JOIN dbo.canales AS c ON c.id_canal = v.id_canal
GROUP BY c.canal, YEAR(v.fecha)
ORDER BY c.canal, anio;


/* ---------------------------------------------------------------------
   4. Descuento promedio de la tienda online por semestre
   --------------------------------------------------------------------- */
SELECT
    YEAR(fecha)                                               AS anio,
    CASE WHEN MONTH(fecha) <= 6 THEN 1 ELSE 2 END             AS semestre,
    1 - CAST(SUM(venta_neta) AS FLOAT)
        / NULLIF(SUM(CAST(cantidad AS BIGINT) * precio_unitario), 0) AS descuento_promedio,
    CAST(SUM(venta_neta) - SUM(costo_total) AS FLOAT) / NULLIF(SUM(venta_neta), 0) AS margen_pct
FROM dbo.ventas
WHERE id_canal = 'C04'
GROUP BY YEAR(fecha), CASE WHEN MONTH(fecha) <= 6 THEN 1 ELSE 2 END
ORDER BY anio, semestre;


/* ---------------------------------------------------------------------
   5. Pareto / ABC de productos (ventas 2025)
   --------------------------------------------------------------------- */
WITH ventas_producto AS (
    SELECT p.id_producto, p.nombre_producto, p.categoria, SUM(v.venta_neta) AS ventas
    FROM dbo.ventas AS v
    JOIN dbo.productos AS p ON p.id_producto = v.id_producto
    WHERE YEAR(v.fecha) = 2025
    GROUP BY p.id_producto, p.nombre_producto, p.categoria
),
acumulado AS (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY ventas DESC)                                   AS ranking,
           CAST(ventas AS FLOAT) / SUM(ventas) OVER ()                                AS pct_ventas,
           CAST(SUM(ventas) OVER (ORDER BY ventas DESC ROWS UNBOUNDED PRECEDING) AS FLOAT)
               / SUM(ventas) OVER ()                                                  AS pct_ventas_acum,
           CAST(ROW_NUMBER() OVER (ORDER BY ventas DESC) AS FLOAT) / COUNT(*) OVER () AS pct_productos
    FROM ventas_producto
)
SELECT *,
       CASE WHEN pct_ventas_acum <= 0.80 THEN 'A'
            WHEN pct_ventas_acum <= 0.95 THEN 'B'
            ELSE 'C' END AS clase_abc
FROM acumulado
ORDER BY ranking;


/* ---------------------------------------------------------------------
   6. Margen de la referencia estrella (P001) antes y después del alza de costos
   --------------------------------------------------------------------- */
SELECT
    CASE WHEN fecha < '2025-04-01' THEN 'Antes de abr-2025' ELSE 'Desde abr-2025' END AS periodo,
    AVG(CAST(precio_unitario AS FLOAT))                       AS precio_promedio,
    AVG(CAST(costo_unitario AS FLOAT))                        AS costo_promedio,
    CAST(SUM(venta_neta) - SUM(costo_total) AS FLOAT) / NULLIF(SUM(venta_neta), 0) AS margen_pct
FROM dbo.ventas
WHERE id_producto = 'P001'
GROUP BY CASE WHEN fecha < '2025-04-01' THEN 'Antes de abr-2025' ELSE 'Desde abr-2025' END;


/* ---------------------------------------------------------------------
   7. Segmentación RFM (corte 2025-12-31)
   --------------------------------------------------------------------- */
DECLARE @fecha_ref DATE = '2025-12-31';

WITH base AS (
    SELECT
        id_cliente,
        DATEDIFF(DAY, MAX(fecha), @fecha_ref)  AS recencia_dias,
        COUNT(DISTINCT id_factura)             AS frecuencia,
        SUM(venta_neta)                        AS monto,
        MIN(fecha)                             AS primera_compra
    FROM dbo.ventas
    GROUP BY id_cliente
),
puntajes AS (
    SELECT *,
           6 - NTILE(5) OVER (ORDER BY recencia_dias ASC, id_cliente) AS R_inv,  -- auxiliar
           NTILE(5) OVER (ORDER BY frecuencia, id_cliente)            AS F,
           NTILE(5) OVER (ORDER BY monto, id_cliente)                 AS M
    FROM base
),
rfm AS (
    SELECT *, R_inv AS R   -- recencia baja (compra reciente) = puntaje 5
    FROM puntajes
)
SELECT
    id_cliente, recencia_dias, frecuencia, monto, R, F, M,
    CASE
        WHEN DATEDIFF(DAY, primera_compra, @fecha_ref) <= 90 THEN 'Nuevos'
        WHEN R >= 4 AND F >= 4 THEN 'Campeones'
        WHEN R >= 3 AND F >= 4 THEN 'Leales'
        WHEN R >= 4 AND F >= 2 THEN 'Potenciales'
        WHEN R <= 2 AND F >= 3 THEN 'En riesgo'
        WHEN R = 3             THEN 'Necesitan atención'
        ELSE 'Perdidos'
    END AS segmento
FROM rfm;
-- Nota: NTILE reparte empates de forma algo distinta a pd.qcut sobre rank(method="first");
-- los conteos por segmento pueden variar en unos pocos clientes frente a Python.


/* ---------------------------------------------------------------------
   8. Retención: clientes de 2024 que volvieron a comprar en 2025
   --------------------------------------------------------------------- */
SELECT
    COUNT(DISTINCT c24.id_cliente)                                         AS clientes_2024,
    COUNT(DISTINCT c25.id_cliente)                                         AS retenidos_2025,
    CAST(COUNT(DISTINCT c25.id_cliente) AS FLOAT) / COUNT(DISTINCT c24.id_cliente) AS tasa_retencion
FROM (SELECT DISTINCT id_cliente FROM dbo.ventas WHERE YEAR(fecha) = 2024) AS c24
LEFT JOIN (SELECT DISTINCT id_cliente FROM dbo.ventas WHERE YEAR(fecha) = 2025) AS c25
       ON c25.id_cliente = c24.id_cliente;
