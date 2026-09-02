-- =============================================================================
-- grants.sql — PASO 3B: ejecutar DESPUÉS de supabase_sql.sql
-- Otorga permisos de lectura/ejecución al rol anon del dashboard HTML.
-- =============================================================================

-- Vista materializada (SELECT = el dashboard puede leer los scores)
GRANT SELECT ON public.mv_scores TO anon;
GRANT SELECT ON public.mv_scores TO authenticated;

-- Funciones RPC (EXECUTE = el dashboard puede llamar .rpc('nombre'))
GRANT EXECUTE ON FUNCTION public.decision_distribucion()              TO anon;
GRANT EXECUTE ON FUNCTION public.top_sospechosas(INT)                 TO anon;
GRANT EXECUTE ON FUNCTION public.distribucion_plataforma()             TO anon;
GRANT EXECUTE ON FUNCTION public.semaforo_confiabilidad()             TO anon;
GRANT EXECUTE ON FUNCTION public.publicaciones_por_hora()             TO anon;
GRANT EXECUTE ON FUNCTION public.cuentas_sospechosas(INT)             TO anon;

-- refresh_mv_scores NO se expone al anon (requiere service_role)
-- Solo el admin debe ejecutarla desde el SQL Editor de Supabase.

-- Verificación rápida: ejecutar esto y confirmar que devuelve datos
SELECT decision, n_publicaciones, porcentaje
FROM public.decision_distribucion();
