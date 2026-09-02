# -*- coding: utf-8 -*-
"""
Features derivadas, scores ponderados y umbrales de decision.
Proyecto: Sistema Indice de Sospecha / Score Confiabilidad — caso "Cancelado"
Subagente: data-scientist

Proposito:
  Calcular 5 features de sospecha y 3 de confiabilidad sobre BASE.csv,
  combinarlas en Indice_Sospecha (0-100) y Score_Confiabilidad (0-100),
  y derivar 3 porcentajes de decision via cortes de percentil.

Salida esperada: resumen de distribucion por Perfil_Usuario + umbrales p33/p66.
Este codigo es la referencia que database-optimizer traduce 1:1 a SQL.
"""

import pandas as pd
import numpy as np

# ── Carga ─────────────────────────────────────────────────────────────────────
CSV_PATH = "C:/Users/ANDRES/Desktop/reto/BASE.csv"

df = pd.read_csv(CSV_PATH, encoding="latin-1")
cols = list(df.columns)
df = df.rename(columns={cols[11]: "Antiguedad_Cuenta_Dias"})  # tilde en col 11
df["Fecha_Hora_Publicacion"] = pd.to_datetime(
    df["Fecha_Hora_Publicacion"], errors="coerce"
)

SEPARADOR = "=" * 70

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 1: FEATURES DE INDICE_SOSPECHA (5 features, escala 0-1)
# ─────────────────────────────────────────────────────────────────────────────
print(SEPARADOR)
print("BLOQUE 1: FEATURES DE INDICE_SOSPECHA")
print(SEPARADOR)

# ── F1: perfil_riesgo_norm ───────────────────────────────────────────────────
# Criterio de negocio: un Bot o una Cuenta_Nueva tiene probabilidad estructuralmente
# mas alta de ser fuente de desinformacion; el perfil no se puede falsear a corto plazo.
# Escala ordinal dividida por el maximo (3) -> ya en 0-1, sin outliers posibles.
# SQL: CASE WHEN Perfil_Usuario = 'Bot_Sospechoso' THEN 1.0
#           WHEN Perfil_Usuario IN ('Cuenta_Nueva','Anónimo') THEN 0.667
#           ELSE 0.0 END
PERFIL_RIESGO_MAP = {
    "Bot_Sospechoso": 3,
    "Cuenta_Nueva": 2,
    "Anónimo": 2,
    "Fan_Antiguo": 0,
    "Verificado": 0,
}
df["f1_perfil_riesgo"] = df["Perfil_Usuario"].map(PERFIL_RIESGO_MAP).fillna(0) / 3.0

# ── F2: antiguedad_inv_prank ─────────────────────────────────────────────────
# Criterio de negocio: una cuenta de 1 dia tiene mucho menos contexto de credibilidad
# que una de 3 años. Invertimos el percentil rank (1 - prank) para que cuentas recientes
# tengan score ALTO de sospecha.
# Normalizacion: percentil rank (robusto a outliers — max=4000 dias no afecta a la mediana).
# SQL: 1.0 - PERCENT_RANK() OVER (ORDER BY "Antiguedad_Cuenta_Dias" ASC)
#      (o: PERCENT_RANK() OVER (ORDER BY "Antiguedad_Cuenta_Dias" DESC))
df["f2_antiguedad_inv"] = (
    1.0 - df["Antiguedad_Cuenta_Dias"].rank(pct=True, na_option="bottom")
)

# ── F3: velocidad_prank ──────────────────────────────────────────────────────
# Criterio de negocio: una viralizacion anormalmente rapida es una señal clasica de
# amplificacion coordinada (bots o camara de eco). El max=300 es un outlier extremo
# (p99=24.4), por eso se usa percentil rank y NO min-max.
# SQL: PERCENT_RANK() OVER (ORDER BY "Velocidad_Viralizacion" ASC)
df["f3_velocidad_prank"] = df["Velocidad_Viralizacion"].rank(pct=True)

# ── F4: reciclado_score ──────────────────────────────────────────────────────
# Criterio de negocio: contenido identico a otra publicacion de 2023 es la señal mas
# directa de manipulacion deliberada; contenido "posible similar" es un riesgo moderado.
# Escala ordinal: identico=1.0, posible=0.6, no=0.0 (ya 0-1, sin normalizacion adicional).
# Nota de encoding: el CSV tiene encoding mixto para 'Si tilde'. Se detecta por subcadena
# 'ntico' (parte de 'identico'/'idéntico') para ser robusto a cualquier codificacion.
# SQL: CASE WHEN "Contenido_Reciclado" ILIKE '%ntico%' THEN 1.0
#           WHEN "Contenido_Reciclado" ILIKE '%osible%' OR "Contenido_Reciclado" ILIKE '%imilar%' THEN 0.6
#           ELSE 0.0 END


def _parse_reciclado(val: str) -> float:
    v = str(val)
    if "ntico" in v:      # 'idéntico' / 'identico' (robusto a mojibake)
        return 1.0
    if "osible" in v or "imilar" in v:  # 'Posible (similar...)'
        return 0.6
    return 0.0


df["f4_reciclado"] = df["Contenido_Reciclado"].apply(_parse_reciclado)

# ── F5: tipo_contenido_riesgo ────────────────────────────────────────────────
# Criterio de negocio: una transcripcion de audio o descripcion de captura es evidencia
# de segunda mano que no se puede verificar directamente; un repost es intermediado;
# un comentario es opinion; un post original es el mas verificable.
# Escala ordinal dividida por 3 -> 0-1. Sin outliers posibles (variable categorica finita).
# SQL: CASE WHEN "Tipo_Publicacion" IN ('Transcripción de audio/video','Descripción de captura') THEN 1.0
#           WHEN "Tipo_Publicacion" = 'Repost/Cita' THEN 0.667
#           WHEN "Tipo_Publicacion" = 'Comentario' THEN 0.333
#           ELSE 0.0 END
TIPO_RIESGO_MAP = {
    "Transcripción de audio/video": 3,
    "Descripción de captura": 3,
    "Repost/Cita": 2,
    "Comentario": 1,
    "Post original": 0,
}
df["f5_tipo_contenido"] = df["Tipo_Publicacion"].map(TIPO_RIESGO_MAP).fillna(1) / 3.0

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2: INDICE_SOSPECHA PONDERADO (escala 0-100)
# ─────────────────────────────────────────────────────────────────────────────
print()
print(SEPARADOR)
print("BLOQUE 2: INDICE_SOSPECHA PONDERADO")
print(SEPARADOR)
print()
print("Formula:")
print("  Indice_Sospecha = 100 * (")
print("      0.35 * f1_perfil_riesgo")
print("    + 0.25 * f2_antiguedad_inv")
print("    + 0.20 * f3_velocidad_prank")
print("    + 0.10 * f4_reciclado")
print("    + 0.10 * f5_tipo_contenido")
print("  )")
print()
print("Justificacion de pesos:")
print("  0.35 -> Perfil es la señal estructural mas directa (Bot/Cuenta_Nueva vs Verificado)")
print("  0.25 -> Antiguedad invierte la credibilidad acumulada de la cuenta")
print("  0.20 -> Velocidad anormal es señal de amplificacion coordinada")
print("  0.10 -> Contenido reciclado confirma manipulacion deliberada (pero solo 5.9% del set)")
print("  0.10 -> Tipo de contenido captura el riesgo de evidencia no verificable")

PESOS_SOSPECHA = {
    "f1_perfil_riesgo": 0.35,
    "f2_antiguedad_inv": 0.25,
    "f3_velocidad_prank": 0.20,
    "f4_reciclado": 0.10,
    "f5_tipo_contenido": 0.10,
}
df["Indice_Sospecha"] = (
    sum(df[col] * peso for col, peso in PESOS_SOSPECHA.items()) * 100
)

print()
print("=== Indice_Sospecha: distribucion global ===")
print(
    df["Indice_Sospecha"]
    .describe(percentiles=[0.10, 0.25, 0.33, 0.50, 0.66, 0.75, 0.90, 0.95])
    .round(1)
    .to_string()
)

print()
print("=== Indice_Sospecha: mediana por Perfil_Usuario ===")
mediana_sospecha = (
    df.groupby("Perfil_Usuario")["Indice_Sospecha"]
    .median()
    .sort_values(ascending=False)
    .round(1)
)
print(mediana_sospecha.to_string())
print()
print("Discriminacion esperada: Bot_Sospechoso >> Cuenta_Nueva > Anonimo > Fan_Antiguo ~ Verificado")

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3: FEATURES DE SCORE_CONFIABILIDAD (3 features, escala 0-1)
# ─────────────────────────────────────────────────────────────────────────────
print()
print(SEPARADOR)
print("BLOQUE 3: FEATURES DE SCORE_CONFIABILIDAD")
print(SEPARADOR)

# ── G1: antiguedad_prank ─────────────────────────────────────────────────────
# Criterio de negocio: una cuenta con anos de historia tiene un track record verificable.
# Nota: es la misma variable que F2 pero en direccion positiva (no invertida).
# SQL: PERCENT_RANK() OVER (ORDER BY "Antiguedad_Cuenta_Dias" ASC)
df["g1_antiguedad"] = df["Antiguedad_Cuenta_Dias"].rank(pct=True, na_option="bottom")

# ── G2: corroboraciones_prank ─────────────────────────────────────────────────
# Criterio de negocio: si multiples fuentes independientes describen el mismo hecho,
# la probabilidad de fabricacion coordinada cae drasticamente.
# Nota: 58.8% tienen 0 corroboraciones -> su prank promedio es 0.294 (correcto por empates).
# SQL: PERCENT_RANK() OVER (ORDER BY "Corroboraciones_Independientes" ASC)
df["g2_corroboraciones"] = df["Corroboraciones_Independientes"].rank(pct=True)

# ── G3: tipo_contenido_confiable ──────────────────────────────────────────────
# Criterio de negocio: inverso de F5. Un post original en primera persona es mas
# verificable que una transcripcion de un audio que no se puede autenticar.
# SQL: CASE WHEN "Tipo_Publicacion" = 'Post original' THEN 1.0
#           WHEN "Tipo_Publicacion" = 'Comentario' THEN 0.67
#           WHEN "Tipo_Publicacion" = 'Repost/Cita' THEN 0.33
#           ELSE 0.0 END
TIPO_CONFIABLE_MAP = {
    "Post original": 1.0,
    "Comentario": 0.67,
    "Repost/Cita": 0.33,
    "Descripción de captura": 0.0,
    "Transcripción de audio/video": 0.0,
}
df["g3_tipo_confiable"] = df["Tipo_Publicacion"].map(TIPO_CONFIABLE_MAP).fillna(0.5)

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 4: SCORE_CONFIABILIDAD PONDERADO (escala 0-100)
# ─────────────────────────────────────────────────────────────────────────────
print()
print(SEPARADOR)
print("BLOQUE 4: SCORE_CONFIABILIDAD PONDERADO")
print(SEPARADOR)
print()
print("Formula:")
print("  Score_Confiabilidad = 100 * (")
print("      0.40 * g1_antiguedad")
print("    + 0.40 * g2_corroboraciones")
print("    + 0.20 * g3_tipo_confiable")
print("  )")
print()
print("Justificacion de pesos:")
print("  0.40 -> Antiguedad: la credibilidad acumulada a lo largo del tiempo es el mejor predictor")
print("  0.40 -> Corroboraciones: multiples testigos independientes es la prueba mas fuerte")
print("  0.20 -> Tipo de fuente: matiza, pero pesa menos que la historia de la cuenta")
print()
print("Nota: Score_Confiabilidad NO es 100 - Indice_Sospecha.")
print("  Una publicacion puede tener cuenta antigua (confiabilidad alta) Y velocidad anormal (sospecha alta)")
print("  — eso es exactamente el caso de influencers con muchos bots amplificando.")

PESOS_CONFIABILIDAD = {
    "g1_antiguedad": 0.40,
    "g2_corroboraciones": 0.40,
    "g3_tipo_confiable": 0.20,
}
df["Score_Confiabilidad"] = (
    sum(df[col] * peso for col, peso in PESOS_CONFIABILIDAD.items()) * 100
)

print()
print("=== Score_Confiabilidad: distribucion global ===")
print(
    df["Score_Confiabilidad"]
    .describe(percentiles=[0.10, 0.25, 0.50, 0.75, 0.90])
    .round(1)
    .to_string()
)

print()
print("=== Score_Confiabilidad: mediana por Perfil_Usuario ===")
mediana_conf = (
    df.groupby("Perfil_Usuario")["Score_Confiabilidad"]
    .median()
    .sort_values(ascending=False)
    .round(1)
)
print(mediana_conf.to_string())
print()
print("Discriminacion esperada: Verificado ~ Fan_Antiguo >> Anonimo > Cuenta_Nueva >> Bot_Sospechoso")

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 5: UMBRALES DE DECISION (p33 y p66 sobre Indice_Sospecha)
# ─────────────────────────────────────────────────────────────────────────────
print()
print(SEPARADOR)
print("BLOQUE 5: UMBRALES DE DECISION")
print(SEPARADOR)

p33 = df["Indice_Sospecha"].quantile(0.33)
p66 = df["Indice_Sospecha"].quantile(0.66)

print()
print(f"Corte inferior (p33): {p33:.2f}  -> por debajo: MANTENER")
print(f"Corte superior (p66): {p66:.2f}  -> por encima: CANCELAR")
print(f"Zona media [p33, p66]: BAJAR_VIDEO")
print()
print("Justificacion: los cortes en p33 y p66 garantizan aprox. un tercio de registros")
print("por bucket, evitando que un umbral arbitrario concentre el 90% en una sola categoria.")
print("Con los datos actuales:")
print(f"  Indice_Sospecha < {p33:.1f}  -> mantener (no hay pruebas suficientes)")
print(f"  Indice_Sospecha en [{p33:.1f}, {p66:.1f}]  -> bajar_video (evidencia ambigua)")
print(f"  Indice_Sospecha > {p66:.1f}  -> cancelar (pruebas confiables de manipulacion)")

df["decision"] = pd.cut(
    df["Indice_Sospecha"],
    bins=[-np.inf, p33, p66, np.inf],
    labels=["mantener", "bajar_video", "cancelar"],
)

print()
print("=== Distribucion de decisiones (%) ===")
pct_dec = df["decision"].value_counts(normalize=True).mul(100).round(1)
print(pct_dec.to_string())

print()
print("=== Decision por Perfil_Usuario (%) ===")
dec_por_perfil = (
    df.groupby("Perfil_Usuario")["decision"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
    .unstack(fill_value=0)
)
print(dec_por_perfil.to_string())

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 6: DISTRIBUCION DE CADA FEATURE (para validacion)
# ─────────────────────────────────────────────────────────────────────────────
print()
print(SEPARADOR)
print("BLOQUE 6: DISTRIBUCION DE FEATURES (min, mediana, p75, p95, max)")
print(SEPARADOR)

features_sospecha = [
    "f1_perfil_riesgo",
    "f2_antiguedad_inv",
    "f3_velocidad_prank",
    "f4_reciclado",
    "f5_tipo_contenido",
]
features_conf = [
    "g1_antiguedad",
    "g2_corroboraciones",
    "g3_tipo_confiable",
]
todas = features_sospecha + features_conf + ["Indice_Sospecha", "Score_Confiabilidad"]

print()
print(
    df[todas]
    .describe(percentiles=[0.25, 0.50, 0.75, 0.95])
    .loc[["min", "25%", "50%", "75%", "95%", "max"]]
    .round(3)
    .to_string()
)

print()
print("=== Sospecha mediana por Tipo_Publicacion ===")
print(
    df.groupby("Tipo_Publicacion")["Indice_Sospecha"]
    .median()
    .sort_values(ascending=False)
    .round(1)
    .to_string()
)

print()
print("=== Confiabilidad mediana por Tipo_Publicacion ===")
print(
    df.groupby("Tipo_Publicacion")["Score_Confiabilidad"]
    .median()
    .sort_values(ascending=False)
    .round(1)
    .to_string()
)

print()
print("Script completado.")
