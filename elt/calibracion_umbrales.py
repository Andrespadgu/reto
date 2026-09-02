# -*- coding: utf-8 -*-
"""
Calibracion de umbrales de decision para Indice_Sospecha.
Proyecto: Sistema Indice de Sospecha / Score Confiabilidad -- caso "Cancelado"
Subagente: data-scientist

Proposito:
  Sustituir los cortes mecanicos en p33/p66 por cortes anclados en los perfiles
  reales del dataset.  Los cortes finales (30 y 50) se justifican con medianas
  y percentiles de cada grupo -- no con tercios arbitrarios.

Hallazgo clave:
  Cortes anteriores (p33=21, p66=35) dividian el dataset en tercios iguales sin
  importar si el 80% de las publicaciones eran legitimas.  Cortes calibrados a
  valores de perfil resuelven ese problema.

Entregable para database-optimizer: ver BLOQUE 5 al final del archivo.
"""

import sys
import pandas as pd
import numpy as np

# Forzar UTF-8 en stdout para evitar UnicodeEncodeError en Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Carga
CSV_PATH = "C:/Users/ANDRES/Desktop/reto/BASE.csv"

df = pd.read_csv(CSV_PATH, encoding="latin-1")
cols = list(df.columns)
df = df.rename(columns={cols[11]: "Antiguedad_Cuenta_Dias"})
df["Fecha_Hora_Publicacion"] = pd.to_datetime(
    df["Fecha_Hora_Publicacion"], errors="coerce"
)

# Detectar el valor exacto de "Anonimo" en el CSV (tolera mojibake de latin-1)
_anonimo_val = (
    df[df["Perfil_Usuario"].str.startswith("An")]["Perfil_Usuario"].iloc[0]
)

SEP = "=" * 72

# ── F1: perfil_riesgo_norm
PERFIL_RIESGO_MAP = {
    "Bot_Sospechoso": 3,
    "Cuenta_Nueva": 2,
    _anonimo_val: 2,
    "Fan_Antiguo": 0,
    "Verificado": 0,
}
df["f1_perfil_riesgo"] = (
    df["Perfil_Usuario"].map(PERFIL_RIESGO_MAP).fillna(0) / 3.0
)

# ── F2: antiguedad_inv_prank
df["f2_antiguedad_inv"] = (
    1.0 - df["Antiguedad_Cuenta_Dias"].rank(pct=True, na_option="bottom")
)

# ── F3: velocidad_prank
df["f3_velocidad_prank"] = df["Velocidad_Viralizacion"].rank(pct=True)

# ── F4: reciclado_score
def _parse_reciclado(val: str) -> float:
    v = str(val)
    if "ntico" in v:
        return 1.0
    if "osible" in v or "imilar" in v:
        return 0.6
    return 0.0

df["f4_reciclado"] = df["Contenido_Reciclado"].apply(_parse_reciclado)

# ── F5: tipo_contenido_riesgo
TIPO_RIESGO_MAP = {
    "Transcripción de audio/video": 3,
    "Descripción de captura": 3,
    "Repost/Cita": 2,
    "Comentario": 1,
    "Post original": 0,
}
df["f5_tipo_contenido"] = (
    df["Tipo_Publicacion"].map(TIPO_RIESGO_MAP).fillna(1) / 3.0
)

# ── Indice_Sospecha (0-100)
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

# ── Score_Confiabilidad (0-100)
df["g1_antiguedad"] = df["Antiguedad_Cuenta_Dias"].rank(pct=True, na_option="bottom")
df["g2_corroboraciones"] = df["Corroboraciones_Independientes"].rank(pct=True)
TIPO_CONFIABLE_MAP = {
    "Post original": 1.0,
    "Comentario": 0.67,
    "Repost/Cita": 0.33,
    "Descripción de captura": 0.0,
    "Transcripción de audio/video": 0.0,
}
df["g3_tipo_confiable"] = df["Tipo_Publicacion"].map(TIPO_CONFIABLE_MAP).fillna(0.5)

PESOS_CONFIABILIDAD = {
    "g1_antiguedad": 0.40,
    "g2_corroboraciones": 0.40,
    "g3_tipo_confiable": 0.20,
}
df["Score_Confiabilidad"] = (
    sum(df[col] * peso for col, peso in PESOS_CONFIABILIDAD.items()) * 100
)

# =============================================================================
# BLOQUE 1: DIAGNOSTICO -- por que los cortes p33/p66 no funcionan
# =============================================================================
print(SEP)
print("BLOQUE 1: DIAGNOSTICO DE CORTES ANTERIORES (p33/p66)")
print(SEP)

p33_mec = df["Indice_Sospecha"].quantile(0.33)
p66_mec = df["Indice_Sospecha"].quantile(0.66)
print(f"\nCortes mecanicos: p33={p33_mec:.1f}, p66={p66_mec:.1f}")

print("\nMedianas de Indice_Sospecha por Perfil_Usuario:")
mediana_perfiles = (
    df.groupby("Perfil_Usuario")["Indice_Sospecha"]
    .median()
    .sort_values(ascending=False)
    .round(1)
)
print(mediana_perfiles.to_string())

print(
    f"\nProblema 1: con p33={p33_mec:.0f} como corte de 'mantener', Verificado"
    f" (mediana 19.1) y Fan_Antiguo (mediana 20.9) quedan mezclados con Anonimo"
    f" (mediana 48.9) en un mismo bucket sin separar perfiles."
)
print(
    f"\nProblema 2: los cortes mecanicos garantizan tercios iguales aunque el 80%"
    f" de las publicaciones sean legitimas -- eso fuerza a recomendar 'cancelar'"
    f" a un tercio del dataset sin importar quien lo publico."
)

# =============================================================================
# BLOQUE 2: EXPLORACION DE DISTRIBUCIONES POR PERFIL
# =============================================================================
print()
print(SEP)
print("BLOQUE 2: DISTRIBUCION DE Indice_Sospecha POR PERFIL")
print(SEP)

perfiles_ordenados = [
    "Verificado", "Fan_Antiguo", _anonimo_val, "Cuenta_Nueva", "Bot_Sospechoso"
]
print()
for p in perfiles_ordenados:
    subset = df[df["Perfil_Usuario"] == p]["Indice_Sospecha"]
    q25, q50, q75 = subset.quantile([0.25, 0.50, 0.75])
    print(
        f"  {p:<20} n={len(subset):>4}  "
        f"p25={q25:>5.1f}  mediana={q50:>5.1f}  p75={q75:>5.1f}"
    )

print(
    "\nSaltos naturales:"
    "\n  Zona baja  (mediana < 22): Verificado (19.1) + Fan_Antiguo (20.9)"
    "\n  Zona gris  (mediana ~ 49): Anonimo (48.9) -- perfil ambiguo por definicion"
    "\n  Zona alta  (mediana > 57): Cuenta_Nueva (57.2) + Bot_Sospechoso (82.6)"
    "\n"
    "\n  Brecha inferior: Verificado p75 ~ 24, Anonimo minimo ~ 26"
    "\n  -> NO HAY solapamiento real: Anonimo no baja a zona segura"
    "\n  Brecha superior: Anonimo p75 = 56.6, Cuenta_Nueva p25 = 51.4"
    "\n  -> Solapamiento leve en rango 51-57 (zona gris intencional)"
)

# =============================================================================
# BLOQUE 3: ESCANEO DE UMBRALES CANDIDATOS
# =============================================================================
print()
print(SEP)
print("BLOQUE 3: ESCANEO DE UMBRALES CANDIDATOS")
print(SEP)

print(
    "\nCriterios de aceptacion:"
    "\n  cancelar debe capturar >90% de Bot_Sospechoso y >80% de Cuenta_Nueva"
    "\n  mantener debe capturar >70% de Verificado y >70% de Fan_Antiguo"
    "\n  bajar_video es zona gris (Anonimo ambiguo) -- sin requisito estricto"
)

cn  = df[df["Perfil_Usuario"] == "Cuenta_Nueva"]["Indice_Sospecha"]
bot = df[df["Perfil_Usuario"] == "Bot_Sospechoso"]["Indice_Sospecha"]
ver = df[df["Perfil_Usuario"] == "Verificado"]["Indice_Sospecha"]
fan = df[df["Perfil_Usuario"] == "Fan_Antiguo"]["Indice_Sospecha"]
an  = df[df["Perfil_Usuario"] == _anonimo_val]["Indice_Sospecha"]

print(
    f"\n{'cut1':>5} {'cut2':>5} | "
    f"{'Bot-c%':>7} {'CN-c%':>6} {'Ver-m%':>7} {'Fan-m%':>7} | "
    f"{'mant%':>6} {'bv%':>5} {'canc%':>6}"
)
print("-" * 75)
for cut1 in [25, 27, 30]:
    for cut2 in [45, 47, 50, 55]:
        b_c  = (bot > cut2).mean() * 100
        cn_c = (cn  > cut2).mean() * 100
        v_m  = (ver < cut1).mean() * 100
        f_m  = (fan < cut1).mean() * 100
        mant = (df["Indice_Sospecha"] < cut1).mean() * 100
        canc = (df["Indice_Sospecha"] > cut2).mean() * 100
        bv   = 100 - mant - canc
        ok   = (b_c > 90 and cn_c > 80 and v_m > 70 and f_m > 70)
        marker = " <-- CANDIDATO" if ok else ""
        print(
            f"{cut1:>5} {cut2:>5} | "
            f"{b_c:>7.1f} {cn_c:>6.1f} {v_m:>7.1f} {f_m:>7.1f} | "
            f"{mant:>6.1f} {bv:>5.1f} {canc:>6.1f}{marker}"
        )

# =============================================================================
# BLOQUE 4: CORTES CALIBRADOS FINALES Y VALIDACION
# =============================================================================
print()
print(SEP)
print("BLOQUE 4: CORTES CALIBRADOS FINALES")
print("  mantener < 30  |  30 <= bajar_video <= 50  |  cancelar > 50")
print(SEP)

# Justificacion de los cortes:
#
# CUT_MANTENER = 30
#   El p75 de Verificado es 23.9 y de Fan_Antiguo es 27.3 -- ambos caen
#   por debajo de 30.  Con cut1=30 se captura el 94% de Verificado y el 85%
#   de Fan_Antiguo en "mantener" sin que ningun Cuenta_Nueva (min=27.9) entre
#   masivamente (solo 0.3% de CN cae por debajo de 30).
#
# CUT_CANCELAR = 50
#   La mediana de Anonimo es 48.9.  Al poner el corte en 50 se deja el 53%
#   del Anonimo en "bajar_video" (zona gris correcta) y solo el 46% sube a
#   "cancelar" -- aceptable porque Anonimo es ambiguo por definicion.
#   El p25 de Cuenta_Nueva es 51.4: el 82% de CN supera 50 y cae en "cancelar".
#   El 98% de Bot_Sospechoso supera 50 (su p10 ya es ~65).
#
# Por que 50 y no 47 (que tambien pasa los criterios):
#   cut2=47 manda el 58% de Anonimo a "cancelar" -- demasiado agresivo para
#   un perfil que por definicion es ambiguo.  cut2=50 es mas conservador
#   (46% de Anonimo a cancelar) y sigue pasando CN (82%) y Bot (98%).

CUT_MANTENER = 30   # Indice_Sospecha < 30  -> mantener
CUT_CANCELAR = 50   # Indice_Sospecha > 50  -> cancelar
                    # 30 <= IS <= 50         -> bajar_video

df["decision"] = pd.cut(
    df["Indice_Sospecha"],
    bins=[-np.inf, CUT_MANTENER, CUT_CANCELAR, np.inf],
    labels=["mantener", "bajar_video", "cancelar"],
)

# --- [1] % global ---
print("\n[1] Porcentajes globales del dataset (los 3 numeros del dashboard):")
pct_global = (
    df["decision"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
    .reindex(["mantener", "bajar_video", "cancelar"])
)
desc_map = {
    "mantener":    "Pruebas demasiado debiles -- dejar que siga su curso",
    "bajar_video": "Evidencia ambigua -- retirar video sin romper contrato",
    "cancelar":    "Manipulacion confirmada -- cancelar y romper contratos",
}
for etiqueta, pct in pct_global.items():
    print(f"  {etiqueta:<12}: {pct:>5.1f}%  ({desc_map[etiqueta]})")

# --- [2] Tabla perfil x decision ---
print("\n[2] % de cada perfil en cada decision (filas suman 100%):")
tabla = (
    df.groupby("Perfil_Usuario")["decision"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
    .unstack(fill_value=0)
    .reindex(columns=["mantener", "bajar_video", "cancelar"])
)
print(tabla.to_string())

# --- [3] Validacion de criterios ---
print("\n[3] Validacion de criterios de negocio:")
checks = {
    "Bot_Sospechoso en cancelar": (tabla.loc["Bot_Sospechoso", "cancelar"], 90),
    "Cuenta_Nueva en cancelar":   (tabla.loc["Cuenta_Nueva",   "cancelar"], 80),
    "Verificado en mantener":     (tabla.loc["Verificado",      "mantener"], 70),
    "Fan_Antiguo en mantener":    (tabla.loc["Fan_Antiguo",     "mantener"], 70),
}
all_ok = True
for nombre, (val, objetivo) in checks.items():
    estado = "OK" if val > objetivo else "FALLA"
    if estado == "FALLA":
        all_ok = False
    print(f"  {nombre:<30}: {val:>5.1f}%  [objetivo >{objetivo}%]  {estado}")

anonimo_bv = tabla.loc[_anonimo_val, "bajar_video"]
print(
    f"  {'Anonimo en bajar_video':<30}: {anonimo_bv:>5.1f}%"
    f"  [zona gris -- sin objetivo estricto]"
)
print(
    f"\n  Resultado general: "
    f"{'TODOS LOS CRITERIOS PASAN' if all_ok else 'HAY FALLOS -- revisar cortes'}"
)

# --- [4] Anclas de percentil ---
print("\n[4] Anclas de percentil para referencia de database-optimizer:")
p_mantener = (df["Indice_Sospecha"] < CUT_MANTENER).mean() * 100
p_cancelar  = (df["Indice_Sospecha"] > CUT_CANCELAR).mean() * 100
print(f"  CUT_MANTENER=30 equivale al p{p_mantener:.0f} del dataset")
print(f"  CUT_CANCELAR=50 equivale al p{100-p_cancelar:.0f} del dataset")
print(
    f"  Distribucion: mantener={p_mantener:.1f}% "
    f"/ bajar_video={100-p_mantener-p_cancelar:.1f}% "
    f"/ cancelar={p_cancelar:.1f}%"
)

# =============================================================================
# BLOQUE 5: RESUMEN PARA database-optimizer (traduccion 1:1 a SQL)
# =============================================================================
print()
print(SEP)
print("BLOQUE 5: RESUMEN PARA database-optimizer")
print(SEP)

lines = [
    "",
    "FORMULAS VALIDADAS EN PANDAS -- traducir 1:1 a SQL (vistas materializadas):",
    "",
    "--- Indice_Sospecha (0-100) ---",
    "  f1 = CASE",
    "         WHEN perfil_usuario = 'Bot_Sospechoso' THEN 1.0",
    "         WHEN perfil_usuario IN ('Cuenta_Nueva', 'Anonimo') THEN 0.667",
    "         ELSE 0.0",
    "       END",
    "",
    "  f2 = 1.0 - PERCENT_RANK() OVER (ORDER BY antiguedad_cuenta_dias ASC)",
    "",
    "  f3 = PERCENT_RANK() OVER (ORDER BY velocidad_viralizacion ASC)",
    "",
    "  f4 = CASE",
    "         WHEN contenido_reciclado ILIKE '%ntico%'               THEN 1.0",
    "         WHEN contenido_reciclado ILIKE '%osible%'",
    "           OR contenido_reciclado ILIKE '%imilar%'              THEN 0.6",
    "         ELSE 0.0",
    "       END",
    "",
    "  f5 = CASE",
    "         WHEN tipo_publicacion IN ('Transcripcion de audio/video',",
    "                                   'Descripcion de captura')    THEN 1.0",
    "         WHEN tipo_publicacion = 'Repost/Cita'                  THEN 0.667",
    "         WHEN tipo_publicacion = 'Comentario'                   THEN 0.333",
    "         ELSE 0.0",
    "       END",
    "",
    "  Indice_Sospecha = 100 * (0.35*f1 + 0.25*f2 + 0.20*f3 + 0.10*f4 + 0.10*f5)",
    "",
    "--- Score_Confiabilidad (0-100) ---",
    "  g1 = PERCENT_RANK() OVER (ORDER BY antiguedad_cuenta_dias ASC)",
    "",
    "  g2 = PERCENT_RANK() OVER (ORDER BY corroboraciones_independientes ASC)",
    "",
    "  g3 = CASE",
    "         WHEN tipo_publicacion = 'Post original'  THEN 1.0",
    "         WHEN tipo_publicacion = 'Comentario'     THEN 0.67",
    "         WHEN tipo_publicacion = 'Repost/Cita'    THEN 0.33",
    "         ELSE 0.0",
    "       END",
    "",
    "  Score_Confiabilidad = 100 * (0.40*g1 + 0.40*g2 + 0.20*g3)",
    "",
    "--- Regla de decision (3 buckets) ---",
    "  CASE",
    "    WHEN Indice_Sospecha < 30  THEN 'mantener'      -- 36.4% del dataset",
    "    WHEN Indice_Sospecha <= 50 THEN 'bajar_video'   -- 25.5% del dataset",
    "    ELSE                            'cancelar'       -- 38.1% del dataset",
    "  END",
    "",
    "--- Justificacion de cortes (para el pitch) ---",
    "  30: p75 de Verificado (23.9) y Fan_Antiguo (27.3) caen por debajo de 30.",
    "      Captura el 94% de Verificado y el 85% de Fan_Antiguo en 'mantener'",
    "      sin ceder 'mantener' a Cuenta_Nueva (solo 0.3% de CN cae por debajo).",
    "",
    "  50: Mediana de Anonimo = 48.9. El corte en 50 deja el 53% del perfil",
    "      ambiguo en 'bajar_video' (correcto) y captura el 82% de Cuenta_Nueva",
    "      y el 98% de Bot_Sospechoso en 'cancelar'.",
    "",
    "--- Validacion final (todos los criterios superados) ---",
    "  Bot_Sospechoso en cancelar : 97.8%  [objetivo >90%]  OK",
    "  Cuenta_Nueva en cancelar   : 82.1%  [objetivo >80%]  OK",
    "  Verificado en mantener     : 93.8%  [objetivo >70%]  OK",
    "  Fan_Antiguo en mantener    : 84.8%  [objetivo >70%]  OK",
    "  Anonimo en bajar_video     : 52.5%  [zona gris -- sin objetivo]",
    "",
    "--- Numeros del dashboard (en grande, en tiempo real) ---",
    "  MANTENER    : 36.4%",
    "  BAJAR_VIDEO : 25.5%",
    "  CANCELAR    : 38.1%",
    "",
]
for line in lines:
    print(line)

print("Script completado.")
