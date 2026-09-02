"""
ml/autoencoder.py — Detector de Anomalías Comportamentales
===========================================================
Autoencoder entrenado exclusivamente sobre publicaciones de cuentas
Verificadas y Fan_Antiguo. El error de reconstrucción para el resto
del dataset captura qué tan lejos está cada publicación de ese
comportamiento "normal" aprendido.

Arquitectura: Input(N) -> 12 -> 6 -> [3 bottleneck] -> 6 -> 12 -> Output(N)
Implementado con sklearn.MLPRegressor (target = input).

Uso:
    python ml/autoencoder.py

Salidas:
    ml/resultados_autoencoder.csv  — scores por publicación
    ml/figura_autoencoder.png      — visualización de 4 paneles
"""

import os, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor

# ── 0. RUTAS ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML   = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(ROOT, "BASE.csv")

# ── 1. CARGA ────────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV, encoding="latin-1")
df.columns = df.columns.str.strip()

# El nombre de la columna contiene ü — resolverlo de forma robusta
col_ant = next(c for c in df.columns if "ntig" in c)
df = df.rename(columns={col_ant: "antiguedad_cuenta_dias"})

print(f"[OK] Dataset cargado: {len(df)} publicaciones x {len(df.columns)} columnas")

# ── 2. FEATURE ENGINEERING ─────────────────────────────────────────────────────

# 2a. Contenido_Reciclado -> escala ordinal (No=0, Posible=0.5, Sí=1)
def reciclado_score(val):
    s = str(val).strip()
    if s.startswith("Sí"):   return 1.0
    if s == "Posible (similar a una publicación anterior)": return 0.5
    return 0.0

df["f_reciclado"] = df["Contenido_Reciclado"].apply(reciclado_score)

# 2b. Máscara de cuentas normales (anclas de entrenamiento)
normal_mask = df["Perfil_Usuario"].isin(["Verificado", "Fan_Antiguo"])
print(f"[OK] Cuentas normales para entrenamiento: {normal_mask.sum()} "
      f"(Verificado={df[df.Perfil_Usuario=='Verificado'].shape[0]}, "
      f"Fan_Antiguo={df[df.Perfil_Usuario=='Fan_Antiguo'].shape[0]})")

# 2c. Imputar NaN usando la mediana de las cuentas NORMALES
#     -> el modelo aprende qué es "normal", no la media global
median_ant   = df.loc[normal_mask, "antiguedad_cuenta_dias"].median()
median_inter = df.loc[normal_mask, "Num_Interacciones"].median()

df["antiguedad_cuenta_dias"] = df["antiguedad_cuenta_dias"].fillna(median_ant)
df["Num_Interacciones"]      = df["Num_Interacciones"].fillna(median_inter)

# 2d. Log-transform para distribuiciones muy sesgadas (colas largas)
df["log_antiguedad"]   = np.log1p(df["antiguedad_cuenta_dias"])
df["log_seguidores"]   = np.log1p(df["Num_Seguidores_Cuenta"])
df["log_interacciones"]= np.log1p(df["Num_Interacciones"])
df["log_velocidad"]    = np.log1p(df["Velocidad_Viralizacion"])
df["log_corrob"]       = np.log1p(df["Corroboraciones_Independientes"])

# 2e. One-hot encoding de categóricas
perfil_oh    = pd.get_dummies(df["Perfil_Usuario"],   prefix="perfil")
plataforma_oh= pd.get_dummies(df["Plataforma"],       prefix="plat")
tipo_oh      = pd.get_dummies(df["Tipo_Publicacion"], prefix="tipo")

# 2f. Ensamblar matriz de features
NUMERICAS = ["log_antiguedad","log_seguidores","log_interacciones",
             "log_velocidad","log_corrob","f_reciclado"]

X_raw = pd.concat([
    df[NUMERICAS].reset_index(drop=True),
    perfil_oh.reset_index(drop=True),
    plataforma_oh.reset_index(drop=True),
    tipo_oh.reset_index(drop=True),
], axis=1).astype(float)

FEATURES = X_raw.columns.tolist()
print(f"[OK] Feature matrix: {X_raw.shape[0]} x {X_raw.shape[1]} "
      f"({len(NUMERICAS)} numéricas + {X_raw.shape[1]-len(NUMERICAS)} one-hot)")

# ── 3. NORMALIZACIÓN ────────────────────────────────────────────────────────────
# El scaler se ajusta SOLO sobre cuentas normales:
# define el [0,1] en términos de comportamiento "esperado".
# Cuentas anómalas pueden salir del rango -> el autoencoder tendrá más error.
X_normal = X_raw[normal_mask].values
X_all    = X_raw.values

scaler = MinMaxScaler()
scaler.fit(X_normal)

X_normal_scaled = scaler.transform(X_normal)
X_all_scaled    = scaler.transform(X_all)
# Permitir que features anómalas superen el rango normal (no clipear)
# El autoencoder solo aprendió [0,1] -> error alto en valores fuera de rango

# ── 4. AUTOENCODER (MLP con target = input) ────────────────────────────────────
n = X_normal_scaled.shape[1]
print(f"\nEntrenando autoencoder {n}->12->6->3->6->12->{n}...")

ae = MLPRegressor(
    hidden_layer_sizes = (12, 6, 3, 6, 12),
    activation         = "relu",
    solver             = "adam",
    learning_rate_init = 0.001,
    max_iter           = 600,
    batch_size         = 64,
    random_state       = 42,
    early_stopping     = True,
    validation_fraction= 0.15,
    n_iter_no_change   = 40,
    tol                = 1e-6,
    verbose            = False,
)

ae.fit(X_normal_scaled, X_normal_scaled)
print(f"  [OK] Convergió en {ae.n_iter_} iteraciones")
print(f"  [OK] Loss de entrenamiento final: {ae.loss_:.6f}")

# ── 5. SCORE DE ANOMALÍA ────────────────────────────────────────────────────────
X_pred      = ae.predict(X_all_scaled)
# MSE por fila = error de reconstrucción individual
recon_error = np.mean((X_all_scaled - X_pred) ** 2, axis=1)

# Normalizar a 0-100 usando los percentiles 2 y 98 de TODAS las filas
# (robusto a outliers extremos que distorsionarían la escala)
p2, p98 = np.percentile(recon_error, [2, 98])
score_anomalia = np.clip((recon_error - p2) / (p98 - p2 + 1e-12), 0, 1) * 100

df["recon_error"]    = recon_error
df["score_anomalia"] = score_anomalia

# ── 6. ÍNDICE DE SOSPECHA BASADO EN REGLAS (para comparación) ───────────────────
perfil_map = {"Bot_Sospechoso":1.0,"Cuenta_Nueva":0.67,"Anónimo":0.5,
              "Fan_Antiguo":0.15,"Verificado":0.0}
tipo_map   = {"Transcripción de audio/video":0.9,"Descripción de captura":0.8,
              "Repost/Cita":0.5,"Comentario":0.3,"Post original":0.2}

df["f_perfil"]       = df["Perfil_Usuario"].map(perfil_map).fillna(0.5)
df["f_ant_inv"]      = 1 - df["antiguedad_cuenta_dias"] / (df["antiguedad_cuenta_dias"].max()+1)
df["f_velocidad_r"]  = df["Velocidad_Viralizacion"] / (df["Velocidad_Viralizacion"].max()+1e-9)
df["f_tipo"]         = df["Tipo_Publicacion"].map(tipo_map).fillna(0.5)

df["indice_sospecha"] = 100 * (
    0.35 * df["f_perfil"] +
    0.25 * df["f_ant_inv"] +
    0.20 * df["f_velocidad_r"] +
    0.10 * df["f_reciclado"] +
    0.10 * df["f_tipo"]
)

# ── 7. IMPORTANCIA DE FEATURES (permutation importance) ─────────────────────────
print("\nCalculando importancia de features por permutación...")
base_err   = recon_error.mean()
importancia = {}

rng = np.random.RandomState(42)
for i, fname in enumerate(FEATURES):
    X_perm        = X_all_scaled.copy()
    X_perm[:, i]  = rng.permutation(X_perm[:, i])
    err_perm       = np.mean((X_perm - ae.predict(X_perm)) ** 2, axis=1)
    importancia[fname] = err_perm.mean() - base_err   # cuánto sube el error al romper esa feature

imp_df = (pd.DataFrame({"feature": FEATURES, "delta_error": list(importancia.values())})
          .sort_values("delta_error", ascending=False)
          .reset_index(drop=True))

# ── 8. ESTADÍSTICAS EN CONSOLA ───────────────────────────────────────────────────
print("\n" + "="*55)
print("  SCORE DE ANOMALÍA (0-100) POR PERFIL DE USUARIO")
print("="*55)
stats = (df.groupby("Perfil_Usuario")["score_anomalia"]
         .agg(["mean","median","max","count"])
         .sort_values("mean", ascending=False)
         .rename(columns={"mean":"Media","median":"Mediana","max":"Máx","count":"N"}))
print(stats.to_string())

corr = df["score_anomalia"].corr(df["indice_sospecha"])
print(f"\n  Correlación Score_Anomalía <-> Índice_Sospecha: {corr:.3f}")

divergencias_ae  = ((df["score_anomalia"]>50) & (df["indice_sospecha"]<30)).sum()
divergencias_reg = ((df["indice_sospecha"]>50) & (df["score_anomalia"]<30)).sum()
print(f"  AE detecta anómalo pero reglas dicen seguro:  {divergencias_ae} publicaciones")
print(f"  Reglas detectan sospechoso pero AE dice OK:   {divergencias_reg} publicaciones")

print("\n  TOP 10 FEATURES MÁS IMPORTANTES:")
print(imp_df.head(10).to_string(index=False))

# ── 9. GUARDAR CSV ───────────────────────────────────────────────────────────────
OUTPUT_COLS = [
    "ID_Publicacion","Usuario_Handle","Plataforma","Perfil_Usuario",
    "Tipo_Publicacion","Contenido_Reciclado","antiguedad_cuenta_dias",
    "Velocidad_Viralizacion","Corroboraciones_Independientes",
    "recon_error","score_anomalia","indice_sospecha",
]
out_path = os.path.join(ML, "resultados_autoencoder.csv")
df[OUTPUT_COLS].to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"\n[OK] CSV guardado en: {out_path}")

# ── 10. VISUALIZACIÓN ────────────────────────────────────────────────────────────
COLORES_PERFIL = {
    "Bot_Sospechoso": "#dc2626",
    "Cuenta_Nueva":   "#ea580c",
    "Anónimo":        "#d97706",
    "Fan_Antiguo":    "#16a34a",
    "Verificado":     "#2563eb",
}

fig = plt.figure(figsize=(18, 13), facecolor="#f8fafc")
fig.suptitle("Autoencoder de Anomalías Comportamentales — Caso Kai Duarte",
             fontsize=15, fontweight="bold", y=0.99, color="#0f172a")

gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.35,
                       left=0.06, right=0.97, top=0.93, bottom=0.06)

# ── Panel A: distribución del score por perfil ───────────────────────────────
ax1 = fig.add_subplot(gs[0, :2])
perfiles_orden = ["Bot_Sospechoso","Cuenta_Nueva","Anónimo","Fan_Antiguo","Verificado"]
for perfil in perfiles_orden:
    sub = df[df["Perfil_Usuario"] == perfil]["score_anomalia"]
    ax1.hist(sub, bins=40, alpha=0.65, color=COLORES_PERFIL[perfil],
             label=f"{perfil} (n={len(sub)})", density=True)

ax1.axvline(50, color="#7c3aed", ls="--", lw=1.5, label="Umbral 50 (cancelar)")
ax1.axvline(30, color="#64748b", ls=":",  lw=1.5, label="Umbral 30 (bajar video)")
ax1.set_title("A · Distribución del Score de Anomalía por Perfil",
              fontsize=11, fontweight="bold", color="#0f172a", pad=6)
ax1.set_xlabel("Score de Anomalía (0 = normal, 100 = muy anómalo)", fontsize=9)
ax1.set_ylabel("Densidad", fontsize=9)
ax1.legend(fontsize=7.5, framealpha=0.9)
ax1.spines[["top","right"]].set_visible(False)

# ── Panel B: mediana por perfil ──────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 2])
medianas = df.groupby("Perfil_Usuario")["score_anomalia"].median().reindex(perfiles_orden)
bars = ax2.barh(perfiles_orden, medianas.values,
                color=[COLORES_PERFIL[p] for p in perfiles_orden], edgecolor="none", height=0.6)
for bar, val in zip(bars, medianas.values):
    ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
             f"{val:.1f}", va="center", fontsize=9, fontweight="bold", color="#0f172a")
ax2.axvline(50, color="#7c3aed", ls="--", lw=1.2)
ax2.set_xlim(0, 105)
ax2.set_title("B · Mediana por Perfil", fontsize=11, fontweight="bold", color="#0f172a", pad=6)
ax2.set_xlabel("Mediana Score Anomalía", fontsize=9)
ax2.spines[["top","right"]].set_visible(False)
ax2.tick_params(axis="y", labelsize=8.5)

# ── Panel C: scatter AE vs Reglas ───────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, :2])
for perfil in perfiles_orden:
    sub = df[df["Perfil_Usuario"] == perfil]
    ax3.scatter(sub["indice_sospecha"], sub["score_anomalia"],
                alpha=0.30, s=12, color=COLORES_PERFIL[perfil], label=perfil)

# Cuadrantes
ax3.axhline(50, color="#7c3aed", ls="--", lw=1.0, alpha=0.7)
ax3.axvline(50, color="#7c3aed", ls="--", lw=1.0, alpha=0.7)
ax3.text(2,  95, "AE alerta\nReglas no",   fontsize=7.5, color="#dc2626",
         va="top",    ha="left",  style="italic")
ax3.text(95, 2,  "Reglas alertan\nAE no",   fontsize=7.5, color="#2563eb",
         va="bottom", ha="right", style="italic")
ax3.text(95, 95, "Ambos\nalertan",          fontsize=7.5, color="#7c3aed",
         va="top",    ha="right", style="italic")
ax3.text(2,  2,  "Ambos\ndicen OK",         fontsize=7.5, color="#16a34a",
         va="bottom", ha="left",  style="italic")

ax3.set_title(f"C · Autoencoder vs Índice de Reglas  (r = {corr:.3f})",
              fontsize=11, fontweight="bold", color="#0f172a", pad=6)
ax3.set_xlabel("Índice de Sospecha (reglas, 0-100)", fontsize=9)
ax3.set_ylabel("Score de Anomalía (autoencoder, 0-100)", fontsize=9)
ax3.legend(fontsize=7.5, framealpha=0.9, markerscale=2)
ax3.set_xlim(-2, 102); ax3.set_ylim(-2, 102)
ax3.spines[["top","right"]].set_visible(False)

# ── Panel D: top features ────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 2])
top_imp = imp_df.head(10)
# Limpiar nombres de features para el gráfico
labels = (top_imp["feature"]
          .str.replace("perfil_","perfil: ", regex=False)
          .str.replace("plat_","plat: ", regex=False)
          .str.replace("tipo_","tipo: ", regex=False)
          .str.replace("log_","", regex=False))
colors = ["#dc2626" if d > 0 else "#16a34a" for d in top_imp["delta_error"]]
ax4.barh(range(len(top_imp)), top_imp["delta_error"].values,
         color=colors, edgecolor="none", height=0.65)
ax4.set_yticks(range(len(top_imp)))
ax4.set_yticklabels(labels.values, fontsize=8)
ax4.invert_yaxis()
ax4.axvline(0, color="#64748b", lw=0.8)
ax4.set_title("D · Importancia de Features\n(aumento del error al permutar)",
              fontsize=10, fontweight="bold", color="#0f172a", pad=6)
ax4.set_xlabel("Delta Error promedio", fontsize=9)
ax4.spines[["top","right"]].set_visible(False)
ax4.tick_params(axis="x", labelsize=8)

# Nota al pie
fig.text(0.06, 0.01,
         f"Entrenado en {normal_mask.sum()} publicaciones normales (Verificado + Fan_Antiguo). "
         f"Dataset completo: 3.210 publicaciones. Correlación AE<->Reglas: r={corr:.3f}.",
         fontsize=8, color="#64748b", style="italic")

fig_path = os.path.join(ML, "figura_autoencoder.png")
fig.savefig(fig_path, dpi=150, bbox_inches="tight")
print(f"[OK] Figura guardada en: {fig_path}")
plt.show()

# ── 11. RESUMEN FINAL ─────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  RESUMEN — CASOS DIVERGENTES (nuevos hallazgos)")
print("="*55)
divergentes_ae = df[(df["score_anomalia"] > 50) & (df["indice_sospecha"] < 30)]
if len(divergentes_ae):
    print(f"\n  El AE marca anómalas pero las reglas las ignoraban ({len(divergentes_ae)} pubs):")
    print(divergentes_ae[["ID_Publicacion","Usuario_Handle","Perfil_Usuario",
                           "score_anomalia","indice_sospecha"]].head(5).to_string(index=False))

divergentes_reg = df[(df["indice_sospecha"] > 50) & (df["score_anomalia"] < 30)]
if len(divergentes_reg):
    print(f"\n  Las reglas las marcan sospechosas pero el AE dice que son normales ({len(divergentes_reg)} pubs):")
    print(divergentes_reg[["ID_Publicacion","Usuario_Handle","Perfil_Usuario",
                            "score_anomalia","indice_sospecha"]].head(5).to_string(index=False))
