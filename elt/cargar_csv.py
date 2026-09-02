"""
cargar_csv.py — PASO 2 DE 3: carga BASE.csv a Supabase
=======================================================
Requisitos:
    pip install pandas supabase python-dotenv

Archivo .env requerido (en la raíz del proyecto, nunca en git):
    SUPABASE_URL=https://vuczxmesylxlltlsabpo.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=<service_role_key>   <-- NO la anon key

Ejecutar desde la raíz del proyecto:
    python elt/cargar_csv.py
"""

import os
import sys
import math
import pandas as pd
from dotenv import load_dotenv

# ── Carga de variables de entorno ────────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Se usa la service_role key para insertar (la anon key no tiene permiso de escritura)
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("ERROR: Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el archivo .env")
    sys.exit(1)

from supabase import create_client
sb = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# ── Ruta del CSV ─────────────────────────────────────────────────────────────
RUTA_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "BASE.csv")
if not os.path.exists(RUTA_CSV):
    print(f"ERROR: No se encontró BASE.csv en {RUTA_CSV}")
    sys.exit(1)

# ── Lectura del CSV (latin-1 porque el archivo no es UTF-8) ──────────────────
print(f"Leyendo {RUTA_CSV}…")
df = pd.read_csv(RUTA_CSV, encoding="latin-1", sep=",")
print(f"  {len(df)} filas × {len(df.columns)} columnas")
print(f"  Columnas: {list(df.columns)}")

# ── Renombrar columnas CSV → schema Supabase ─────────────────────────────────
# El CSV usa PascalCase con tildes; la tabla usa snake_case sin tildes.
columnas_map = {
    "ID_Publicacion":                  "id_publicacion",
    "ID_Publicacion_Padre":            "id_publicacion_padre",
    "ID_Usuario":                      "id_usuario",
    "Usuario_Handle":                  "usuario_handle",
    "Plataforma":                      "plataforma",
    "Tipo_Publicacion":                "tipo_publicacion",
    "Texto_Publicacion":               "texto_publicacion",
    "Hashtags_Usados":                 "hashtags_usados",
    "Marca_Mencionada":                "marca_mencionada",
    "Fecha_Hora_Publicacion":          "fecha_hora_publicacion",
    "Perfil_Usuario":                  "perfil_usuario",
    "Antigüedad_Cuenta_Dias":          "antiguedad_cuenta_dias",
    "Num_Seguidores_Cuenta":           "num_seguidores_cuenta",
    "Num_Interacciones":               "num_interacciones",
    "Velocidad_Viralizacion":          "velocidad_viralizacion",
    "Contenido_Reciclado":             "contenido_reciclado",
    "Corroboraciones_Independientes":  "corroboraciones_independientes",
}

# Normalizar nombres de columna del CSV (puede venir con espacios o variantes)
df.columns = df.columns.str.strip()

# Renombrar las que coincidan (ignora las que no están en el CSV)
df = df.rename(columns={k: v for k, v in columnas_map.items() if k in df.columns})

# Verificar que todas las columnas necesarias existan
columnas_requeridas = list(columnas_map.values())
faltantes = [c for c in columnas_requeridas if c not in df.columns]
if faltantes:
    print(f"ADVERTENCIA: columnas no encontradas en el CSV: {faltantes}")
    print(f"  Columnas disponibles: {list(df.columns)}")

# ── Limpieza y conversión de tipos ───────────────────────────────────────────

# contenido_reciclado: CSV tiene strings como "Sí (idéntico...)" → True, resto → False
if "contenido_reciclado" in df.columns:
    df["contenido_reciclado"] = (
        df["contenido_reciclado"]
        .astype(str)
        .str.strip()
        .str.startswith("Sí")
    )

# fecha_hora_publicacion: convertir a ISO 8601 para TIMESTAMPTZ
if "fecha_hora_publicacion" in df.columns:
    df["fecha_hora_publicacion"] = pd.to_datetime(
        df["fecha_hora_publicacion"], errors="coerce"
    ).dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

# Columnas numéricas: reemplazar NaN con None (Supabase acepta null)
numericas = [
    "id_publicacion_padre", "num_interacciones",
    "velocidad_viralizacion", "antiguedad_cuenta_dias",
    "num_seguidores_cuenta", "corroboraciones_independientes",
]
for col in numericas:
    if col in df.columns:
        df[col] = df[col].where(df[col].notna(), other=None)

# Convertir todo el DataFrame a una lista de dicts limpios
def limpiar_nan(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    return v

registros = [
    {k: limpiar_nan(v) for k, v in fila.items()}
    for fila in df.to_dict(orient="records")
]

# ── Carga por lotes ──────────────────────────────────────────────────────────
LOTE = 200
total    = len(registros)
errores  = 0

print(f"\nCargando {total} registros en lotes de {LOTE}…")

for i in range(0, total, LOTE):
    lote = registros[i : i + LOTE]
    try:
        resp = sb.table("publicaciones").upsert(lote, on_conflict="id_publicacion").execute()
        print(f"  Lote {i//LOTE + 1}/{math.ceil(total/LOTE)} — {len(lote)} filas OK")
    except Exception as e:
        errores += 1
        print(f"  Lote {i//LOTE + 1} ERROR: {e}")

print(f"\nCarga completada. Errores: {errores}")

if errores == 0:
    # Verificación rápida
    try:
        count_resp = sb.table("publicaciones").select("id_publicacion", count="exact").execute()
        print(f"Filas en Supabase: {count_resp.count}")
    except Exception as e:
        print(f"No se pudo verificar el conteo: {e}")
    print("\nSiguiente paso: ejecutar elt/supabase_sql.sql en el SQL Editor de Supabase.")
