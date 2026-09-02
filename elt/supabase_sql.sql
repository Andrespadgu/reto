-- =============================================================================
-- PROYECTO: Sistema Indice de Sospecha / Score Confiabilidad
-- CASO: "Cancelado" — Kai Duarte
-- SUBAGENTE: database-optimizer
-- ARCHIVO: elt/supabase_sql.sql
--
-- Proposito: traduccion 1:1 de las formulas validadas por data-scientist
-- en pandas a SQL ejecutable en Supabase (PostgreSQL).
--
-- COMO EJECUTAR: pegar TODO este archivo en el SQL Editor de Supabase
-- de arriba hacia abajo. Requiere que la tabla `publicaciones` ya exista
-- con datos cargados por data-engineer.
--
-- NOTA SOBRE contenido_reciclado:
--   El data-engineer sube la columna como BOOLEAN (true/false).
--   El CSV original tiene 3 valores (No / Posible-similar / Si-identico).
--   La formula del data-scientist asigna 0.0 / 0.6 / 1.0 segun el valor.
--   Con BOOLEAN solo tenemos dos estados; f4 usa: true=1.0, false=0.0
--   (peso 0.10 — impacto marginal en el score final).
--   Si data-engineer puede exponer una columna TEXT adicional con el valor
--   crudo del CSV, f4 puede refinarse a los tres niveles sin cambiar pesos.
-- =============================================================================


-- =============================================================================
-- SECCION 1: VISTA MATERIALIZADA mv_scores
-- =============================================================================
-- Calcula Indice_Sospecha, Score_Confiabilidad y decision para cada publicacion.
-- Se materializa porque el calculo con PERCENT_RANK() requiere un full-scan de
-- la tabla completa — no tiene sentido repetirlo en cada request del dashboard.
-- Refrescar con: REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_scores;
-- =============================================================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_scores;

CREATE MATERIALIZED VIEW public.mv_scores AS

WITH

-- ── CTE 1: features de Indice_Sospecha (escala 0-1 cada una) ─────────────────
features_sospecha AS (
    SELECT
        id_publicacion,
        id_publicacion_padre,
        id_usuario,
        usuario_handle,
        plataforma,
        tipo_publicacion,
        texto_publicacion,
        hashtags_usados,
        marca_mencionada,
        fecha_hora_publicacion,
        perfil_usuario,
        antiguedad_cuenta_dias,
        num_seguidores_cuenta,
        num_interacciones,
        velocidad_viralizacion,
        contenido_reciclado,
        corroboraciones_independientes,

        -- F1: perfil de riesgo estructural (0 / 0.667 / 1.0)
        -- Bot es la señal mas directa; Cuenta_Nueva y Anonimo tienen credibilidad baja.
        CASE perfil_usuario
            WHEN 'Bot_Sospechoso'  THEN 1.0
            WHEN 'Cuenta_Nueva'    THEN 0.667
            WHEN 'Anónimo'         THEN 0.667
            ELSE                        0.0
        END AS f1_perfil_riesgo,

        -- F2: antiguedad invertida — cuenta reciente = sospecha alta
        -- PERCENT_RANK ASC: la mas antigua tiene rank=1 (sospecha baja → invertida=0)
        -- la mas reciente tiene rank≈0 (sospecha baja antes de invertir → invertida≈1)
        1.0 - PERCENT_RANK() OVER (ORDER BY antiguedad_cuenta_dias ASC)
            AS f2_antiguedad_inv,

        -- F3: velocidad de viralizacion — rank alto = viralizacion anormal
        PERCENT_RANK() OVER (ORDER BY velocidad_viralizacion ASC)
            AS f3_velocidad_prank,

        -- F4: contenido reciclado (BOOLEAN en Supabase: true=1.0, false=0.0)
        CASE WHEN contenido_reciclado = TRUE THEN 1.0 ELSE 0.0 END
            AS f4_reciclado,

        -- F5: tipo de publicacion como proxy de verificabilidad
        -- Transcripcion/Captura son evidencia de segunda mano (no verificable directamente)
        CASE tipo_publicacion
            WHEN 'Transcripción de audio/video' THEN 1.0
            WHEN 'Descripción de captura'       THEN 1.0
            WHEN 'Repost/Cita'                  THEN 0.667
            WHEN 'Comentario'                   THEN 0.333
            ELSE                                     0.0   -- Post original
        END AS f5_tipo_contenido

    FROM public.publicaciones
),

-- ── CTE 2: features de Score_Confiabilidad (escala 0-1 cada una) ─────────────
features_confiabilidad AS (
    SELECT
        id_publicacion,

        -- G1: antiguedad directa — cuenta antigua = mayor credibilidad acumulada
        PERCENT_RANK() OVER (ORDER BY antiguedad_cuenta_dias ASC)
            AS g1_antiguedad,

        -- G2: corroboraciones independientes — multiples testigos sin conexion
        --     reducen la probabilidad de fabricacion coordinada
        PERCENT_RANK() OVER (ORDER BY corroboraciones_independientes ASC)
            AS g2_corroboraciones,

        -- G3: tipo de publicacion como proxy de confiabilidad (inverso de F5)
        CASE tipo_publicacion
            WHEN 'Post original' THEN 1.0
            WHEN 'Comentario'    THEN 0.67
            WHEN 'Repost/Cita'   THEN 0.33
            ELSE                      0.0   -- Transcripcion/Captura
        END AS g3_tipo_confiable

    FROM public.publicaciones
),

-- ── CTE 3: scores ponderados (escala 0-100) ───────────────────────────────────
scores AS (
    SELECT
        fs.id_publicacion,
        fs.id_publicacion_padre,
        fs.id_usuario,
        fs.usuario_handle,
        fs.plataforma,
        fs.tipo_publicacion,
        fs.texto_publicacion,
        fs.hashtags_usados,
        fs.marca_mencionada,
        fs.fecha_hora_publicacion,
        fs.perfil_usuario,
        fs.antiguedad_cuenta_dias,
        fs.num_seguidores_cuenta,
        fs.num_interacciones,
        fs.velocidad_viralizacion,
        fs.contenido_reciclado,
        fs.corroboraciones_independientes,

        -- Features intermedias (utiles para debug y drill-down en el dashboard)
        fs.f1_perfil_riesgo,
        fs.f2_antiguedad_inv,
        fs.f3_velocidad_prank,
        fs.f4_reciclado,
        fs.f5_tipo_contenido,
        fc.g1_antiguedad,
        fc.g2_corroboraciones,
        fc.g3_tipo_confiable,

        -- Indice_Sospecha: 0-100, mayor = mas sospechoso
        ROUND(CAST(
            100.0 * (
                0.35 * fs.f1_perfil_riesgo
              + 0.25 * fs.f2_antiguedad_inv
              + 0.20 * fs.f3_velocidad_prank
              + 0.10 * fs.f4_reciclado
              + 0.10 * fs.f5_tipo_contenido
            )
        AS NUMERIC), 2) AS indice_sospecha,

        -- Score_Confiabilidad: 0-100, mayor = mas confiable
        -- NOTA: NO es 100 - Indice_Sospecha. Son dimensiones ortogonales.
        -- Una cuenta antigua amplificada por bots puede tener confiabilidad alta Y sospecha alta.
        ROUND(CAST(
            100.0 * (
                0.40 * fc.g1_antiguedad
              + 0.40 * fc.g2_corroboraciones
              + 0.20 * fc.g3_tipo_confiable
            )
        AS NUMERIC), 2) AS score_confiabilidad

    FROM features_sospecha fs
    JOIN features_confiabilidad fc ON fs.id_publicacion = fc.id_publicacion
),

-- ── CTE 4: cortes de decision (p33 y p66 sobre Indice_Sospecha) ──────────────
-- Valores calibrados con pandas sobre BASE.csv (3.210 filas):
--   p33 = 21.02  p66 = 34.95
-- Se recalculan aqui sobre el total real de la tabla para que sean dinamicos
-- si data-engineer agrega filas. Si se quiere fijar los umbrales de pandas,
-- reemplazar esta CTE por: SELECT 21.02 AS p33, 34.95 AS p66
cortes AS (
    SELECT
        PERCENTILE_CONT(0.33) WITHIN GROUP (ORDER BY indice_sospecha) AS p33,
        PERCENTILE_CONT(0.66) WITHIN GROUP (ORDER BY indice_sospecha) AS p66
    FROM scores
)

-- ── SELECT final: cada publicacion con su decision ────────────────────────────
SELECT
    s.id_publicacion,
    s.id_publicacion_padre,
    s.id_usuario,
    s.usuario_handle,
    s.plataforma,
    s.tipo_publicacion,
    s.texto_publicacion,
    s.hashtags_usados,
    s.marca_mencionada,
    s.fecha_hora_publicacion,
    s.perfil_usuario,
    s.antiguedad_cuenta_dias,
    s.num_seguidores_cuenta,
    s.num_interacciones,
    s.velocidad_viralizacion,
    s.contenido_reciclado,
    s.corroboraciones_independientes,

    -- Features intermedias
    ROUND(s.f1_perfil_riesgo::NUMERIC,   4) AS f1_perfil_riesgo,
    ROUND(s.f2_antiguedad_inv::NUMERIC,  4) AS f2_antiguedad_inv,
    ROUND(s.f3_velocidad_prank::NUMERIC, 4) AS f3_velocidad_prank,
    ROUND(s.f4_reciclado::NUMERIC,       4) AS f4_reciclado,
    ROUND(s.f5_tipo_contenido::NUMERIC,  4) AS f5_tipo_contenido,
    ROUND(s.g1_antiguedad::NUMERIC,      4) AS g1_antiguedad,
    ROUND(s.g2_corroboraciones::NUMERIC, 4) AS g2_corroboraciones,
    ROUND(s.g3_tipo_confiable::NUMERIC,  4) AS g3_tipo_confiable,

    -- Scores finales
    s.indice_sospecha,
    s.score_confiabilidad,

    -- Decision de moderacion
    CASE
        WHEN s.indice_sospecha < c.p33  THEN 'mantener'
        WHEN s.indice_sospecha <= c.p66 THEN 'bajar_video'
        ELSE                                 'cancelar'
    END AS decision,

    -- Umbrales usados (para referencia en el dashboard)
    ROUND(c.p33::NUMERIC, 2) AS umbral_p33,
    ROUND(c.p66::NUMERIC, 2) AS umbral_p66

FROM scores s, cortes c;


-- =============================================================================
-- SECCION 2: INDICES SOBRE mv_scores
-- =============================================================================
-- Estos indices eliminan full-scans en todas las queries del dashboard.
-- Se crean DESPUES de la vista materializada porque los indices viven
-- sobre la vista, no sobre la tabla base.
-- =============================================================================

-- Indice unico requerido por REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_scores_pk
    ON public.mv_scores (id_publicacion);

-- Top 10 por sospecha (ORDER BY indice_sospecha DESC)
CREATE INDEX IF NOT EXISTS idx_mv_scores_sospecha_desc
    ON public.mv_scores (indice_sospecha DESC);

-- Distribución de decision (GROUP BY decision)
CREATE INDEX IF NOT EXISTS idx_mv_scores_decision
    ON public.mv_scores (decision);

-- Distribución por plataforma (GROUP BY plataforma)
CREATE INDEX IF NOT EXISTS idx_mv_scores_plataforma
    ON public.mv_scores (plataforma);

-- Publicaciones por hora (DATE_TRUNC hour sobre fecha)
CREATE INDEX IF NOT EXISTS idx_mv_scores_fecha
    ON public.mv_scores (fecha_hora_publicacion);

-- Cuentas mas sospechosas agrupadas por usuario (GROUP BY id_usuario)
CREATE INDEX IF NOT EXISTS idx_mv_scores_usuario
    ON public.mv_scores (id_usuario, indice_sospecha DESC);

-- Score de confiabilidad para el semaforo (ORDER BY score_confiabilidad)
CREATE INDEX IF NOT EXISTS idx_mv_scores_confiabilidad
    ON public.mv_scores (score_confiabilidad);


-- =============================================================================
-- SECCION 3: FUNCION RPC PARA REFRESCAR mv_scores DESDE EL DASHBOARD
-- =============================================================================
-- Llama: supabase.rpc('refresh_mv_scores')
-- Requiere que el rol que la ejecuta tenga privilegio sobre la vista.
-- En Supabase, ejecutar como service_role o con SECURITY DEFINER.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.refresh_mv_scores()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_scores;
END;
$$;


-- =============================================================================
-- SECCION 4: QUERIES DEL DASHBOARD
-- =============================================================================
-- Listas para pegar en supabase-js .from().select() o en el SQL Editor.
-- Cada query va acompañada del snippet JS equivalente en comentarios.
-- =============================================================================


-- ── QUERY 1: Distribucion de las 3 decisiones con porcentajes ────────────────
-- Panel de decision: cuantas publicaciones caen en cada bucket (%).
--
-- supabase-js:
--   const { data } = await supabase
--     .from('mv_scores')
--     .select('decision')
--   // luego agrupar en cliente, o usar la query SQL directa via rpc()
--
-- Mejor via RPC o .rpc('decision_distribucion') — ver funcion mas abajo.
-- Query directa:

SELECT
    decision,
    COUNT(*)                                                        AS n_publicaciones,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)             AS porcentaje
FROM public.mv_scores
GROUP BY decision
ORDER BY
    CASE decision
        WHEN 'cancelar'    THEN 1
        WHEN 'bajar_video' THEN 2
        WHEN 'mantener'    THEN 3
    END;


-- ── QUERY 2: Top 10 publicaciones por Indice_Sospecha mas alto ───────────────
-- Para el panel de alertas: las publicaciones mas peligrosas primero.
--
-- supabase-js:
--   const { data } = await supabase
--     .from('mv_scores')
--     .select('id_publicacion, usuario_handle, plataforma, tipo_publicacion, '
--           + 'texto_publicacion, perfil_usuario, indice_sospecha, score_confiabilidad, decision')
--     .order('indice_sospecha', { ascending: false })
--     .limit(10);

SELECT
    id_publicacion,
    usuario_handle,
    plataforma,
    tipo_publicacion,
    LEFT(texto_publicacion, 120)   AS texto_truncado,
    perfil_usuario,
    indice_sospecha,
    score_confiabilidad,
    decision
FROM public.mv_scores
ORDER BY indice_sospecha DESC
LIMIT 10;


-- ── QUERY 3: Distribucion de publicaciones por plataforma ────────────────────
-- Grafico de barras: X / TikTok / Instagram / Foro anonimo.
--
-- supabase-js:
--   const { data } = await supabase
--     .from('mv_scores')
--     .select('plataforma, indice_sospecha, decision')
--   // agrupar en cliente, o:
--
-- Query directa con conteos y sospecha media por plataforma:

SELECT
    plataforma,
    COUNT(*)                                    AS n_publicaciones,
    ROUND(AVG(indice_sospecha)::NUMERIC, 1)     AS sospecha_media,
    ROUND(AVG(score_confiabilidad)::NUMERIC, 1) AS confiabilidad_media,
    COUNT(*) FILTER (WHERE decision = 'cancelar')    AS n_cancelar,
    COUNT(*) FILTER (WHERE decision = 'bajar_video') AS n_bajar_video,
    COUNT(*) FILTER (WHERE decision = 'mantener')    AS n_mantener
FROM public.mv_scores
GROUP BY plataforma
ORDER BY sospecha_media DESC;


-- ── QUERY 4: Distribucion de Score_Confiabilidad en 5 rangos (semaforo) ──────
-- Para el semaforo del dashboard: muy bajo / bajo / medio / alto / muy alto.
--
-- supabase-js:
--   const { data } = await supabase
--     .from('mv_scores')
--     .select('score_confiabilidad')
--   // clasificar en cliente con los mismos cortes, o:

SELECT
    CASE
        WHEN score_confiabilidad <  20 THEN '0-20 (Muy baja)'
        WHEN score_confiabilidad <  40 THEN '20-40 (Baja)'
        WHEN score_confiabilidad <  60 THEN '40-60 (Media)'
        WHEN score_confiabilidad <  80 THEN '60-80 (Alta)'
        ELSE                                '80-100 (Muy alta)'
    END AS rango_confiabilidad,
    COUNT(*)                                                         AS n_publicaciones,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)              AS porcentaje
FROM public.mv_scores
GROUP BY rango_confiabilidad
ORDER BY MIN(score_confiabilidad);


-- ── QUERY 5: Publicaciones por hora (linea de tiempo) ────────────────────────
-- Grafico de linea: actividad temporal del escandalo hora a hora.
--
-- supabase-js:
--   const { data } = await supabase
--     .from('mv_scores')
--     .select('fecha_hora_publicacion, decision')
--   // agrupar por hora en cliente, o:

SELECT
    DATE_TRUNC('hour', fecha_hora_publicacion)              AS hora_utc,
    TO_CHAR(DATE_TRUNC('hour', fecha_hora_publicacion),
            'YYYY-MM-DD HH24:00')                          AS hora_label,
    COUNT(*)                                                AS n_publicaciones,
    COUNT(*) FILTER (WHERE decision = 'cancelar')           AS n_cancelar,
    COUNT(*) FILTER (WHERE decision = 'bajar_video')        AS n_bajar_video,
    COUNT(*) FILTER (WHERE decision = 'mantener')           AS n_mantener,
    ROUND(AVG(indice_sospecha)::NUMERIC, 1)                 AS sospecha_media_hora
FROM public.mv_scores
WHERE fecha_hora_publicacion IS NOT NULL
GROUP BY DATE_TRUNC('hour', fecha_hora_publicacion)
ORDER BY hora_utc;


-- ── QUERY 6: Cuentas mas sospechosas (agrupado por usuario) ──────────────────
-- Tabla de lideres de desinformacion: que usuarios acumulan mas publicaciones
-- de alta sospecha.
--
-- supabase-js:
--   const { data } = await supabase
--     .from('mv_scores')
--     .select('id_usuario, usuario_handle, perfil_usuario, indice_sospecha, decision')
--   // agrupar en cliente, o:

SELECT
    id_usuario,
    usuario_handle,
    perfil_usuario,
    COUNT(*)                                                         AS n_publicaciones,
    ROUND(AVG(indice_sospecha)::NUMERIC, 1)                         AS sospecha_promedio,
    ROUND(MAX(indice_sospecha)::NUMERIC, 1)                         AS sospecha_maxima,
    COUNT(*) FILTER (WHERE decision = 'cancelar')                   AS n_cancelar,
    COUNT(*) FILTER (WHERE decision = 'bajar_video')                AS n_bajar_video,
    ROUND(AVG(score_confiabilidad)::NUMERIC, 1)                     AS confiabilidad_promedio
FROM public.mv_scores
GROUP BY id_usuario, usuario_handle, perfil_usuario
ORDER BY sospecha_promedio DESC, n_cancelar DESC
LIMIT 20;


-- =============================================================================
-- SECCION 5: FUNCIONES RPC PARA EL DASHBOARD (supabase-js .rpc())
-- =============================================================================
-- Encapsulan las queries de arriba como funciones llamables desde el cliente
-- con supabase.rpc('nombre_funcion'). Mas seguro que exponer SQL crudo
-- y permite que Supabase gestione permisos a nivel de funcion.
-- =============================================================================


-- ── RPC: distribucion de decisiones ──────────────────────────────────────────
-- JS: const { data } = await supabase.rpc('decision_distribucion');

CREATE OR REPLACE FUNCTION public.decision_distribucion()
RETURNS TABLE (
    decision        TEXT,
    n_publicaciones BIGINT,
    porcentaje      NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        decision,
        COUNT(*)                                                   AS n_publicaciones,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)        AS porcentaje
    FROM public.mv_scores
    GROUP BY decision
    ORDER BY
        CASE decision
            WHEN 'cancelar'    THEN 1
            WHEN 'bajar_video' THEN 2
            WHEN 'mantener'    THEN 3
        END;
$$;


-- ── RPC: top publicaciones por sospecha ──────────────────────────────────────
-- JS: const { data } = await supabase.rpc('top_sospechosas', { limite: 10 });

CREATE OR REPLACE FUNCTION public.top_sospechosas(limite INT DEFAULT 10)
RETURNS TABLE (
    id_publicacion      BIGINT,
    usuario_handle      TEXT,
    plataforma          TEXT,
    tipo_publicacion    TEXT,
    texto_truncado      TEXT,
    perfil_usuario      TEXT,
    indice_sospecha     NUMERIC,
    score_confiabilidad NUMERIC,
    decision            TEXT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        id_publicacion,
        usuario_handle,
        plataforma,
        tipo_publicacion,
        LEFT(texto_publicacion, 120) AS texto_truncado,
        perfil_usuario,
        indice_sospecha,
        score_confiabilidad,
        decision
    FROM public.mv_scores
    ORDER BY indice_sospecha DESC
    LIMIT limite;
$$;


-- ── RPC: distribucion por plataforma ─────────────────────────────────────────
-- JS: const { data } = await supabase.rpc('distribucion_plataforma');

CREATE OR REPLACE FUNCTION public.distribucion_plataforma()
RETURNS TABLE (
    plataforma          TEXT,
    n_publicaciones     BIGINT,
    sospecha_media      NUMERIC,
    confiabilidad_media NUMERIC,
    n_cancelar          BIGINT,
    n_bajar_video       BIGINT,
    n_mantener          BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        plataforma,
        COUNT(*)                                        AS n_publicaciones,
        ROUND(AVG(indice_sospecha)::NUMERIC, 1)         AS sospecha_media,
        ROUND(AVG(score_confiabilidad)::NUMERIC, 1)     AS confiabilidad_media,
        COUNT(*) FILTER (WHERE decision = 'cancelar')   AS n_cancelar,
        COUNT(*) FILTER (WHERE decision = 'bajar_video') AS n_bajar_video,
        COUNT(*) FILTER (WHERE decision = 'mantener')   AS n_mantener
    FROM public.mv_scores
    GROUP BY plataforma
    ORDER BY sospecha_media DESC;
$$;


-- ── RPC: distribucion de confiabilidad en rangos (semaforo) ──────────────────
-- JS: const { data } = await supabase.rpc('semaforo_confiabilidad');

CREATE OR REPLACE FUNCTION public.semaforo_confiabilidad()
RETURNS TABLE (
    rango_confiabilidad TEXT,
    n_publicaciones     BIGINT,
    porcentaje          NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        CASE
            WHEN score_confiabilidad <  20 THEN '0-20 (Muy baja)'
            WHEN score_confiabilidad <  40 THEN '20-40 (Baja)'
            WHEN score_confiabilidad <  60 THEN '40-60 (Media)'
            WHEN score_confiabilidad <  80 THEN '60-80 (Alta)'
            ELSE                                '80-100 (Muy alta)'
        END AS rango_confiabilidad,
        COUNT(*)                                                      AS n_publicaciones,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)           AS porcentaje
    FROM public.mv_scores
    GROUP BY rango_confiabilidad
    ORDER BY MIN(score_confiabilidad);
$$;


-- ── RPC: publicaciones por hora ───────────────────────────────────────────────
-- JS: const { data } = await supabase.rpc('publicaciones_por_hora');

CREATE OR REPLACE FUNCTION public.publicaciones_por_hora()
RETURNS TABLE (
    hora_utc         TIMESTAMPTZ,
    hora_label       TEXT,
    n_publicaciones  BIGINT,
    n_cancelar       BIGINT,
    n_bajar_video    BIGINT,
    n_mantener       BIGINT,
    sospecha_media   NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        DATE_TRUNC('hour', fecha_hora_publicacion)                   AS hora_utc,
        TO_CHAR(DATE_TRUNC('hour', fecha_hora_publicacion),
                'YYYY-MM-DD HH24:00')                               AS hora_label,
        COUNT(*)                                                     AS n_publicaciones,
        COUNT(*) FILTER (WHERE decision = 'cancelar')                AS n_cancelar,
        COUNT(*) FILTER (WHERE decision = 'bajar_video')             AS n_bajar_video,
        COUNT(*) FILTER (WHERE decision = 'mantener')                AS n_mantener,
        ROUND(AVG(indice_sospecha)::NUMERIC, 1)                      AS sospecha_media
    FROM public.mv_scores
    WHERE fecha_hora_publicacion IS NOT NULL
    GROUP BY DATE_TRUNC('hour', fecha_hora_publicacion)
    ORDER BY hora_utc;
$$;


-- ── RPC: cuentas mas sospechosas ──────────────────────────────────────────────
-- JS: const { data } = await supabase.rpc('cuentas_sospechosas', { limite: 20 });

CREATE OR REPLACE FUNCTION public.cuentas_sospechosas(limite INT DEFAULT 20)
RETURNS TABLE (
    id_usuario              BIGINT,
    usuario_handle          TEXT,
    perfil_usuario          TEXT,
    n_publicaciones         BIGINT,
    sospecha_promedio       NUMERIC,
    sospecha_maxima         NUMERIC,
    n_cancelar              BIGINT,
    n_bajar_video           BIGINT,
    confiabilidad_promedio  NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        id_usuario,
        usuario_handle,
        perfil_usuario,
        COUNT(*)                                                      AS n_publicaciones,
        ROUND(AVG(indice_sospecha)::NUMERIC, 1)                      AS sospecha_promedio,
        ROUND(MAX(indice_sospecha)::NUMERIC, 1)                      AS sospecha_maxima,
        COUNT(*) FILTER (WHERE decision = 'cancelar')                AS n_cancelar,
        COUNT(*) FILTER (WHERE decision = 'bajar_video')             AS n_bajar_video,
        ROUND(AVG(score_confiabilidad)::NUMERIC, 1)                  AS confiabilidad_promedio
    FROM public.mv_scores
    GROUP BY id_usuario, usuario_handle, perfil_usuario
    ORDER BY sospecha_promedio DESC, n_cancelar DESC
    LIMIT limite;
$$;


-- =============================================================================
-- SECCION 6: VERIFICACION RAPIDA (ejecutar para confirmar que todo funciono)
-- =============================================================================

-- Contar filas en la vista materializada (debe ser igual a publicaciones)
SELECT COUNT(*) AS total_mv_scores FROM public.mv_scores;

-- Umbrales usados (deben ser ~21.02 y ~34.95 con BASE.csv)
SELECT DISTINCT umbral_p33, umbral_p66 FROM public.mv_scores;

-- Muestra de las primeras 5 filas con scores
SELECT
    id_publicacion, usuario_handle, perfil_usuario,
    indice_sospecha, score_confiabilidad, decision
FROM public.mv_scores
ORDER BY indice_sospecha DESC
LIMIT 5;

-- Distribucion de decisiones (debe ser ~33% cada una)
SELECT decision, COUNT(*), ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(),1) AS pct
FROM public.mv_scores
GROUP BY decision;


-- =============================================================================
-- SNIPPETS supabase-js PARA EL DASHBOARD
-- =============================================================================
-- Copiar directamente en el archivo JS del dashboard.
-- Requiere: import { createClient } from '@supabase/supabase-js'
-- const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
-- =============================================================================

/*

// ── 1. Distribucion de decisiones (panel principal) ──────────────────────────
const { data: decisiones, error } = await supabase
  .rpc('decision_distribucion');
// decisiones: [{ decision, n_publicaciones, porcentaje }, ...]


// ── 2. Top 10 mas sospechosas (tabla de alertas) ─────────────────────────────
const { data: topSospechosas } = await supabase
  .rpc('top_sospechosas', { limite: 10 });
// topSospechosas: [{ id_publicacion, usuario_handle, plataforma, ... }, ...]

// Alternativa directa con .from() (si RLS lo permite):
const { data: topSospechosas } = await supabase
  .from('mv_scores')
  .select('id_publicacion, usuario_handle, plataforma, tipo_publicacion, perfil_usuario, indice_sospecha, score_confiabilidad, decision')
  .order('indice_sospecha', { ascending: false })
  .limit(10);


// ── 3. Distribucion por plataforma (grafico de barras) ───────────────────────
const { data: porPlataforma } = await supabase
  .rpc('distribucion_plataforma');
// porPlataforma: [{ plataforma, n_publicaciones, sospecha_media, n_cancelar, ... }, ...]


// ── 4. Semaforo de confiabilidad (5 rangos) ───────────────────────────────────
const { data: semaforo } = await supabase
  .rpc('semaforo_confiabilidad');
// semaforo: [{ rango_confiabilidad, n_publicaciones, porcentaje }, ...]


// ── 5. Linea de tiempo por hora ───────────────────────────────────────────────
const { data: porHora } = await supabase
  .rpc('publicaciones_por_hora');
// porHora: [{ hora_utc, hora_label, n_publicaciones, n_cancelar, sospecha_media }, ...]


// ── 6. Cuentas mas sospechosas (top 20) ───────────────────────────────────────
const { data: cuentas } = await supabase
  .rpc('cuentas_sospechosas', { limite: 20 });
// cuentas: [{ id_usuario, usuario_handle, perfil_usuario, sospecha_promedio, n_cancelar, ... }, ...]


// ── Refrescar mv_scores despues de una nueva carga de datos ──────────────────
// Llamar con service_role key (no anon), o exponer el boton solo a admins.
const { error } = await supabaseAdmin.rpc('refresh_mv_scores');

*/
