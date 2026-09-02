# -*- coding: utf-8 -*-
"""
EDA Exploracion - BASE.csv
Proyecto: Sistema de Indice de Sospecha / Score de Confiabilidad
Subagente: data-scientist
Proposito: exploracion pura, sin proponer formulas todavia.
"""

import pandas as pd
import numpy as np

# ── Carga ────────────────────────────────────────────────────────────────────
df = pd.read_csv("C:/Users/ANDRES/Desktop/reto/BASE.csv", encoding="latin-1")

# Renombrar por posicion (columna 11) para evitar problemas de encoding con tilde
cols = list(df.columns)
antiguedad_col = cols[11]  # "Antigüedad_Cuenta_Dias"
df = df.rename(columns={antiguedad_col: "Antiguedad_Cuenta_Dias"})

print("=" * 70)
print("1. SHAPE, DTYPES Y % DE NULOS POR COLUMNA")
print("=" * 70)
print(f"Shape: {df.shape[0]} filas x {df.shape[1]} columnas\n")
print("Dtypes:")
print(df.dtypes)
print()

nulos = df.isna().sum()
pct_nulos = (df.isna().mean() * 100).round(2)
nulos_df = pd.DataFrame({"n_nulos": nulos, "pct_nulos": pct_nulos})
nulos_df = nulos_df[nulos_df["n_nulos"] > 0].sort_values("pct_nulos", ascending=False)
if len(nulos_df) == 0:
    print("Sin nulos en ninguna columna.")
else:
    print("Columnas con nulos:")
    print(nulos_df.to_string())

print()

# ── 2. describe() de numericas candidatas ────────────────────────────────────
print("=" * 70)
print("2. DESCRIBE() DE COLUMNAS NUMERICAS CANDIDATAS")
print("=" * 70)
numericas = [
    "Antiguedad_Cuenta_Dias",
    "Num_Seguidores_Cuenta",
    "Num_Interacciones",
    "Velocidad_Viralizacion",
    "Corroboraciones_Independientes",
]
desc = df[numericas].describe(percentiles=[0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
print(desc.round(2).to_string())
print()

# ── 3. value_counts() de categoricas ─────────────────────────────────────────
print("=" * 70)
print("3. VALUE_COUNTS() DE COLUMNAS CATEGORICAS")
print("=" * 70)
categoricas = [
    "Plataforma",
    "Tipo_Publicacion",
    "Perfil_Usuario",
    "Contenido_Reciclado",
    "Marca_Mencionada",
]
for col in categoricas:
    vc = df[col].value_counts(dropna=False)
    pct = (vc / len(df) * 100).round(1)
    resultado = pd.DataFrame({"conteo": vc, "pct": pct})
    print(f"\n--- {col} ---")
    print(resultado.to_string())

print()

# ── 4. Distribucion temporal ──────────────────────────────────────────────────
print("=" * 70)
print("4. DISTRIBUCION DE FECHA_HORA_PUBLICACION")
print("=" * 70)
df["Fecha_Hora_Publicacion"] = pd.to_datetime(
    df["Fecha_Hora_Publicacion"], errors="coerce"
)
fechas_validas = df["Fecha_Hora_Publicacion"].dropna()
print(f"Registros con fecha valida: {len(fechas_validas)} de {len(df)}")
print(f"Fecha minima: {fechas_validas.min()}")
print(f"Fecha maxima: {fechas_validas.max()}")
print(f"Rango total:  {fechas_validas.max() - fechas_validas.min()}")
print()

df["hora"] = df["Fecha_Hora_Publicacion"].dt.hour
pub_por_hora = df["hora"].value_counts().sort_index()
print("Publicaciones por hora del dia:")
for hora, cnt in pub_por_hora.items():
    barra = "#" * (cnt // 5)
    print(f"  {int(hora):02d}:00 -> {cnt:4d}  {barra}")
print()

# ── 5. Correlaciones entre numericas ─────────────────────────────────────────
print("=" * 70)
print("5. CORRELACIONES DE SPEARMAN ENTRE COLUMNAS NUMERICAS")
print("=" * 70)
corr_matrix = df[numericas].corr(method="spearman")
print("Matriz de correlacion de Spearman:")
print(corr_matrix.round(3).to_string())
print()

print("Pares con |Spearman| > 0.4:")
pares_fuertes = []
for i in range(len(numericas)):
    for j in range(i + 1, len(numericas)):
        r = corr_matrix.iloc[i, j]
        if abs(r) > 0.4:
            pares_fuertes.append((numericas[i], numericas[j], round(r, 3)))
if pares_fuertes:
    for a, b, r in pares_fuertes:
        print(f"  {a} <-> {b}: r={r}")
else:
    print("  Ninguno por encima del umbral 0.4")
print()

# ── 6. Deteccion de outliers ──────────────────────────────────────────────────
print("=" * 70)
print("6. DETECCION DE OUTLIERS (percentiles 95 y 99)")
print("=" * 70)
columnas_outliers = ["Velocidad_Viralizacion", "Num_Interacciones"]
for col in columnas_outliers:
    serie = df[col].dropna()
    p50 = serie.quantile(0.50)
    p90 = serie.quantile(0.90)
    p95 = serie.quantile(0.95)
    p99 = serie.quantile(0.99)
    max_val = serie.max()
    n_above_p95 = int((serie > p95).sum())
    n_above_p99 = int((serie > p99).sum())
    pct_above_p95 = n_above_p95 / len(serie) * 100
    pct_above_p99 = n_above_p99 / len(serie) * 100
    ratio = p99 / p50 if p50 != 0 else float("inf")
    print(f"\n--- {col} ---")
    print(f"  Mediana (p50): {p50:.2f}")
    print(f"  p90:           {p90:.2f}")
    print(f"  p95:           {p95:.2f}")
    print(f"  p99:           {p99:.2f}")
    print(f"  Max:           {max_val:.2f}")
    print(f"  Registros > p95: {n_above_p95} ({pct_above_p95:.1f}%)")
    print(f"  Registros > p99: {n_above_p99} ({pct_above_p99:.1f}%)")
    print(f"  Razon p99/mediana: {ratio:.1f}x")

print()

# ── 7. Observaciones adicionales para scoring ─────────────────────────────────
print("=" * 70)
print("7. OBSERVACIONES ADICIONALES RELEVANTES PARA SCORING")
print("=" * 70)

# Contenido_Reciclado como bool
df["es_reciclado"] = df["Contenido_Reciclado"].str.strip().str.lower().isin(
    ["si", "sí", "yes", "true", "1"]
)
n_reciclado = int(df["es_reciclado"].sum())
print(f"Registros con Contenido_Reciclado=Si: {n_reciclado} ({n_reciclado/len(df)*100:.1f}%)")

# Perfil Bot_Sospechoso
bots = int((df["Perfil_Usuario"] == "Bot_Sospechoso").sum())
print(f"Registros con Perfil_Usuario=Bot_Sospechoso: {bots} ({bots/len(df)*100:.1f}%)")

# Cuentas nuevas (<= 30 dias)
cuentas_nuevas = int((df["Antiguedad_Cuenta_Dias"] <= 30).sum())
print(f"Cuentas con Antiguedad <= 30 dias: {cuentas_nuevas} ({cuentas_nuevas/len(df)*100:.1f}%)")

# Publicaciones originales (sin padre)
originales = int(df["ID_Publicacion_Padre"].isna().sum())
print(f"Publicaciones originales (sin padre): {originales} ({originales/len(df)*100:.1f}%)")

# Foro anonimo
foro = int(df["Plataforma"].str.lower().str.contains("foro|anonimo|anónimo", na=False).sum())
print(f"Publicaciones en Foro anonimo: {foro} ({foro/len(df)*100:.1f}%)")

# Corroboraciones == 0
cero_corr = int((df["Corroboraciones_Independientes"] == 0).sum())
print(f"Registros con Corroboraciones_Independientes=0: {cero_corr} ({cero_corr/len(df)*100:.1f}%)")

# Velocidad_Viralizacion nulos
nulos_vel = int(df["Velocidad_Viralizacion"].isna().sum())
print(f"Nulos en Velocidad_Viralizacion: {nulos_vel} ({nulos_vel/len(df)*100:.1f}%)")

print()
print("Mediana de seguidores por Perfil_Usuario:")
print(df.groupby("Perfil_Usuario")["Num_Seguidores_Cuenta"].median().sort_values(ascending=False).to_string())

print()
print("Mediana de Velocidad_Viralizacion por Plataforma:")
print(df.groupby("Plataforma")["Velocidad_Viralizacion"].median().sort_values(ascending=False).to_string())

print()
print("Mediana de Num_Interacciones por Tipo_Publicacion:")
print(df.groupby("Tipo_Publicacion")["Num_Interacciones"].median().sort_values(ascending=False).to_string())

print()
print("% de contenido reciclado por Perfil_Usuario:")
print((df.groupby("Perfil_Usuario")["es_reciclado"].mean() * 100).round(1).sort_values(ascending=False).to_string())

print()
print("Corroboraciones_Independientes mediana por Plataforma:")
print(df.groupby("Plataforma")["Corroboraciones_Independientes"].median().sort_values(ascending=False).to_string())

print()
print("Contenido_Reciclado valor crudo unico (para validar parse):")
print(df["Contenido_Reciclado"].value_counts(dropna=False).to_string())

print()
print("EDA completado.")
