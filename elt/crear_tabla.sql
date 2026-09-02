-- =============================================================================
-- crear_tabla.sql
-- PASO 1 DE 3 — Ejecutar en el SQL Editor de Supabase ANTES de cargar_csv.py
-- y ANTES de supabase_sql.sql
--
-- Crea la tabla base `publicaciones` con el schema de las 17 columnas del CSV.
-- Otorga permisos de lectura al rol anon (requerido por el dashboard HTML).
-- =============================================================================

-- ── Tabla principal ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.publicaciones (
    id_publicacion                BIGINT PRIMARY KEY,
    id_publicacion_padre          BIGINT     NULL,
    id_usuario                    BIGINT     NOT NULL,
    usuario_handle                TEXT       NOT NULL,
    plataforma                    TEXT       NOT NULL,
    tipo_publicacion              TEXT       NOT NULL,
    texto_publicacion             TEXT,
    hashtags_usados               TEXT       NULL,
    marca_mencionada              TEXT       NULL,
    fecha_hora_publicacion        TIMESTAMPTZ,
    perfil_usuario                TEXT       NOT NULL,
    antiguedad_cuenta_dias        NUMERIC    NOT NULL,
    num_seguidores_cuenta         NUMERIC    NOT NULL,
    num_interacciones             NUMERIC    NULL,
    velocidad_viralizacion        NUMERIC    NULL,
    contenido_reciclado           BOOLEAN    NOT NULL DEFAULT FALSE,
    corroboraciones_independientes INTEGER   NOT NULL DEFAULT 0
);

COMMENT ON TABLE public.publicaciones IS
    'Publicaciones del caso Kai Duarte — 3.210 registros de X, TikTok, Instagram y Foros.';

-- ── Índices de la tabla base ─────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_pub_plataforma
    ON public.publicaciones (plataforma);

CREATE INDEX IF NOT EXISTS idx_pub_perfil
    ON public.publicaciones (perfil_usuario);

CREATE INDEX IF NOT EXISTS idx_pub_fecha
    ON public.publicaciones (fecha_hora_publicacion);

CREATE INDEX IF NOT EXISTS idx_pub_usuario
    ON public.publicaciones (id_usuario);

-- ── Permisos (anon = clave pública del dashboard) ────────────────────────────

GRANT SELECT ON public.publicaciones TO anon;
GRANT SELECT ON public.publicaciones TO authenticated;

-- ── Verificación ──────────────────────────────────────────────────────────────
-- Ejecutar estas líneas al final para confirmar que todo quedó bien:

SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name   = 'publicaciones'
ORDER BY ordinal_position;

-- =============================================================================
-- PASO 2: ejecutar cargar_csv.py  (carga los 3.210 registros de BASE.csv)
-- PASO 3: ejecutar supabase_sql.sql (crea mv_scores y las funciones RPC)
-- =============================================================================
