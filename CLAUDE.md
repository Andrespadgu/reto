# Proyecto: Sistema de Índice de Sospecha / Score de Confiabilidad (Reto Académico)

## Contexto
Reto académico DSAA — **caso "Cancelado"**. Tiempo real de ejecución de ~4 horas.
El objetivo es un **prototipo funcional**, no software de producción.

**El caso:** Kai Duarte, creador de contenido, es acusado de amañar un sorteo millonario.
Un clip viral de 14 s aparece a las 11:47 p.m.; para las 6:00 a.m. la plataforma y sus
marcas patrocinadoras (PulsoTech, UrbanKrew, NovaVolt) deben decidir entre tres acciones:
**cancelar/romper contrato**, **bajar el video**, o **mantener/dejar que siga su curso**.

El dataset contiene publicaciones, comentarios y menciones de X, TikTok, Instagram y foros
anónimos — mezclados: datos confiables, erróneos, falsos o reciclados de otro escándalo.

El flujo es **ELT** (no ETL): se carga el CSV crudo a Supabase tal cual, y las
transformaciones (índices, scores, porcentajes de decisión) se calculan con SQL dentro
de la base — nunca con Python en el cliente.

1. Cargar el **CSV crudo** (`BASE.csv`) a **Supabase (PostgreSQL)** con el schema correcto
   desde el primer intento (Extract + Load).
2. Calcular, con **SQL dentro de Supabase**, un `Indice_Sospecha`, un `Score_Confiabilidad`
   y 3 porcentajes de decisión (la "T" del ELT vive en la base, no en Python).
3. Exponer esos cálculos a un **dashboard HTML** que consulta Supabase en tiempo real.
4. Incluir un **chatbot de demo** que simula respuestas sin gastar tokens de un LLM real
   (matching de intención por keywords/similitud simple + respuestas JSON pregrabadas).

## Restricciones de tiempo y alcance
- Prototipo funcional rápido > arquitectura perfecta. Preferir la solución que corre en
  vivo hoy sobre la "correcta" que tomaría dos días.
- Presupuesto real ≈ 4 horas: cada subagente entrega **código listo para pegar y ejecutar**,
  no explicaciones teóricas largas.
- Todos los subagentes están familiarizados con **Supabase específicamente** (cliente
  `supabase-py`/`supabase-js`, Auth y RLS de Supabase, SQL Editor, `service_role` vs `anon`
  key, extensiones de Postgres habilitadas por Supabase), no solo con PostgreSQL genérico.

## Reglas fijas
- El CSV crudo es `BASE.csv` en la raíz del proyecto. Nunca se modifica directamente.
- El script de carga (Extract + Load) lo escribe **data-engineer** y vive en `elt/`
  (crear la carpeta si no existe).
- Las transformaciones ("T") se hacen con SQL dentro de Supabase (funciones, vistas,
  vistas materializadas) — las escribe **database-optimizer**, no Python.
- Las fórmulas de scoring (`Indice_Sospecha`, `Score_Confiabilidad`, 3 porcentajes de
  decisión) las diseña **data-scientist** en pandas para validarlas rápido; luego
  **database-optimizer** las traduce 1:1 a SQL ejecutable en Supabase.
- El chatbot de demo vive en `chatbot/` (crear la carpeta si no existe) y lo construye
  **ai-engineer-chatbot-ligero**; nunca depende de una API key de un LLM real.
- Ninguna credencial (`service_role key`, connection string) se hardcodea en código;
  siempre variables de entorno en `.env` (y `.env` en `.gitignore`).
- Antes de tocar código, cada subagente revisa si existe una skill relevante en
  `.claude/skills/` y la usa.

## Subagentes disponibles

| Subagente | Skill asociada | Cuándo usarlo |
|---|---|---|
| **data-engineer** | `supabase-schema-elt` | Diseñar el schema de Supabase (tipos, índices, RLS) y escribir el script de carga ELT (Python + `supabase-py` o `pandas` + `psycopg2`). |
| **data-scientist** | `scoring-indices-riesgo` | Diseñar la fórmula de `Indice_Sospecha`, `Score_Confiabilidad` y los 3 porcentajes de decisión: EDA, detección de anomalías, features derivadas, scores ponderados. |
| **database-optimizer** | `supabase-sql-optimizacion` | Traducir las fórmulas validadas a SQL avanzado en Supabase: funciones, vistas materializadas, y las queries optimizadas que usará el dashboard en tiempo real. |
| **ai-engineer-chatbot-ligero** | `chatbot-simulado-ligero` | Diseñar el chatbot de demo: matching de intención sin LLM real, JSON de respuestas pregrabadas, conexión a una interfaz de chat. |

## Flujo de trabajo recomendado
1. **data-scientist** valida en pandas, sobre una muestra del CSV, la fórmula de
   `Indice_Sospecha` / `Score_Confiabilidad` / 3 porcentajes.
2. **data-engineer** diseña el schema de Supabase y sube el CSV limpio (en paralelo al
   paso 1, no depende de él).
3. **database-optimizer** traduce la fórmula validada por data-scientist a una función SQL
   o vista materializada en Supabase, y optimiza las queries del dashboard.
4. **ai-engineer-chatbot-ligero** construye el chatbot de demo en paralelo — solo necesita
   conocer los *nombres* de las métricas que va a "explicar", no depende de que los pasos
   1-3 estén terminados.

El agente principal (tú, orquestando) **no hace directamente** diseño de schema, fórmulas
de scoring, SQL avanzado ni el chatbot: siempre delega en el subagente correspondiente vía
el Task tool.

## Schema del CSV (BASE.csv — 3.210 registros, 17 columnas)

La entidad principal es la **publicación** (`ID_Publicacion`). El `Indice_Sospecha` y el
`Score_Confiabilidad` se calculan **por publicación**, no por usuario ni por sesión.

| Columna | Tipo esperado | Notas |
|---|---|---|
| `ID_Publicacion` | `BIGINT PK` | Identificador único de la publicación |
| `ID_Publicacion_Padre` | `BIGINT NULL` | A qué publicación responde/cita (NULL si es original) |
| `ID_Usuario` | `BIGINT` | Identificador del usuario |
| `Usuario_Handle` | `TEXT` | Alias (@handle) del usuario |
| `Plataforma` | `TEXT` | X, TikTok, Instagram, Foro anónimo |
| `Tipo_Publicacion` | `TEXT` | Post original / Comentario / Repost-Cita / Descripción de captura / Transcripción de audio-video |
| `Texto_Publicacion` | `TEXT` | Texto real o transcripción de la evidencia |
| `Hashtags_Usados` | `TEXT NULL` | Hashtags incluidos |
| `Marca_Mencionada` | `TEXT NULL` | PulsoTech, UrbanKrew, NovaVolt (o NULL) |
| `Fecha_Hora_Publicacion` | `TIMESTAMPTZ` | Timestamp de la publicación |
| `Perfil_Usuario` | `TEXT` | Verificado / Cuenta_Nueva / Bot_Sospechoso / Fan_Antiguo / Anónimo |
| `Antigüedad_Cuenta_Dias` | `NUMERIC` | Días desde la creación de la cuenta |
| `Num_Seguidores_Cuenta` | `NUMERIC` | Número de seguidores |
| `Num_Interacciones` | `NUMERIC NULL` | Likes + comentarios + compartidos |
| `Velocidad_Viralizacion` | `NUMERIC NULL` | Interacciones por minuto en la primera hora |
| `Contenido_Reciclado` | `BOOLEAN` | Si coincide con contenido de otro contexto/fecha (Sí/No en el CSV) |
| `Corroboraciones_Independientes` | `INTEGER` | Cuántos usuarios sin conexión aparente describen el mismo hecho |

## Las 3 decisiones de salida del sistema

| Decisión | Etiqueta en código | Descripción |
|---|---|---|
| Cancelar / Romper contrato | `cancelar` | Pruebas confiables suficientes para actuar |
| Bajar el video | `bajar_video` | Evidencia justifica retirar contenido, no romper contratos |
| Mantener / Dejar que siga | `mantener` | Pruebas demasiado débiles o fabricadas para actuar |

## Pendiente
- [ ] Crear el proyecto en Supabase (nuevo, separado de Treego) y poner `SUPABASE_URL` /
      `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_ANON_KEY` en `.env`.
