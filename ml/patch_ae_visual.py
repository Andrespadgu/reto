"""
patch_ae_visual.py — reconstruye la seccion AE del dashboard con mejor diseno
Ejecutar desde la raiz:   python ml/patch_ae_visual.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "dashboard.html")

with open(PATH, encoding="utf-8") as f:
    html = f.read()

# ── 1. CSS NUEVO para seccion AE (reemplaza el bloque anterior) ───────────────
OLD_CSS_ANCHOR = "    /* AUTOENCODER SECTION */"
END_CSS_ANCHOR = "    @media(max-width:860px){"

if OLD_CSS_ANCHOR not in html:
    print("ERROR: ancla CSS no encontrada"); sys.exit(1)

start_css = html.index(OLD_CSS_ANCHOR)
end_css   = html.index(END_CSS_ANCHOR, start_css)

NEW_CSS = """    /* ── AUTOENCODER SECTION ─────────────────────────── */
    #ae-section { background:#fff; border-radius:var(--r); box-shadow:var(--sh);
                  padding:20px 24px; margin-bottom:18px;
                  border-top:3px solid #7c3aed; }

    .ae-header { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
    .ae-header .stitle { margin-bottom:0; }
    .ae-ml-badge { font-size:.62rem; font-weight:800; letter-spacing:.8px; text-transform:uppercase;
                   background:linear-gradient(135deg,#7c3aed,#4f46e5); color:#fff;
                   padding:3px 9px; border-radius:999px; }
    .ae-tech-note { font-size:.68rem; color:var(--slate); margin-left:auto; }

    /* Explain card */
    .ae-explain { display:grid; grid-template-columns:auto 1fr auto; gap:16px;
                  background:#faf5ff; border:1px solid #e9d5ff; border-radius:10px;
                  padding:14px 18px; margin-bottom:16px; align-items:start; }
    .ae-explain-icon { font-size:2rem; line-height:1; }
    .ae-explain-txt h4 { font-size:.88rem; font-weight:700; color:#6d28d9; margin-bottom:5px; }
    .ae-explain-txt p  { font-size:.81rem; color:#374151; line-height:1.58; }
    .ae-arch-box { background:#fff; border:1px solid #ddd6fe; border-radius:8px;
                   padding:10px 14px; text-align:center; min-width:160px; }
    .ae-arch-title { font-size:.65rem; font-weight:700; text-transform:uppercase;
                     letter-spacing:.6px; color:#7c3aed; margin-bottom:8px; }
    .ae-arch-flow { display:flex; flex-direction:column; gap:3px; align-items:center; }
    .ae-arch-node { font-size:.72rem; font-weight:700; padding:3px 12px;
                    border-radius:6px; color:#fff; width:80px; text-align:center; }
    .ae-arch-node.input    { background:#64748b; }
    .ae-arch-node.enc      { background:#7c3aed; }
    .ae-arch-node.bottleneck { background:#4f46e5; box-shadow:0 0 0 3px #c4b5fd; }
    .ae-arch-node.dec      { background:#8b5cf6; }
    .ae-arch-node.output   { background:#64748b; }
    .ae-arch-arrow { font-size:.65rem; color:#a78bfa; line-height:1; }

    /* Mid row */
    .ae-mid { display:grid; grid-template-columns:1fr 320px; gap:14px; margin-bottom:14px; }
    .ae-chart-wrap { }
    .ae-right { display:flex; flex-direction:column; gap:10px; }

    /* Metric mini cards */
    .ae-metrics { display:flex; flex-direction:column; gap:8px; }
    .ae-metric { border-radius:9px; padding:11px 14px; border:1px solid; display:flex; align-items:center; gap:12px; }
    .ae-metric.corr { background:#f5f3ff; border-color:#ddd6fe; }
    .ae-metric.anom { background:#fef2f2; border-color:#fecaca; }
    .ae-metric.divg { background:#fffbeb; border-color:#fcd34d; }
    .ae-metric-val { font-size:1.5rem; font-weight:900; line-height:1; flex-shrink:0; }
    .ae-metric.corr .ae-metric-val { color:#7c3aed; }
    .ae-metric.anom .ae-metric-val { color:#dc2626; }
    .ae-metric.divg .ae-metric-val { color:#d97706; }
    .ae-metric-txt .ae-metric-lbl { font-size:.7rem; font-weight:700; text-transform:uppercase;
                                    letter-spacing:.4px; color:var(--slate); }
    .ae-metric-txt .ae-metric-sub { font-size:.7rem; color:var(--slate); margin-top:1px; }

    /* Star finding */
    .ae-star { background:linear-gradient(135deg,#faf5ff,#eff6ff); border:1px solid #c4b5fd;
               border-radius:9px; padding:12px 14px; }
    .ae-star-tag { font-size:.62rem; font-weight:800; text-transform:uppercase; letter-spacing:.8px;
                   color:#7c3aed; margin-bottom:5px; }
    .ae-star h5 { font-size:.84rem; font-weight:700; color:#0f172a; margin-bottom:4px; }
    .ae-star p  { font-size:.77rem; color:#374151; line-height:1.5; }
    .ae-star .ae-score-pair { display:flex; gap:14px; margin-top:8px; }
    .ae-star .ae-sp-item { text-align:center; }
    .ae-star .ae-sp-val { font-size:1.25rem; font-weight:900; }
    .ae-star .ae-sp-val.bad  { color:#dc2626; }
    .ae-star .ae-sp-val.good { color:#16a34a; }
    .ae-star .ae-sp-lbl { font-size:.65rem; color:var(--slate); }

    /* Divergent table */
    .ae-div-wrap { }
    .ae-div-table { width:100%; border-collapse:collapse; font-size:.79rem; }
    .ae-div-table th { font-size:.67rem; font-weight:700; text-transform:uppercase;
                       letter-spacing:.4px; color:var(--slate); padding:6px 8px;
                       border-bottom:2px solid var(--border); text-align:left; white-space:nowrap; }
    .ae-div-table td { padding:8px 8px; border-bottom:1px solid var(--border); vertical-align:middle; }
    .ae-div-table tr.ae-star-row td { background:#faf5ff; }
    .ae-div-table tr:last-child td { border-bottom:none; }
    .ae-div-table tr:hover td { background:#f8fafc; }
    .ae-div-table tr.ae-star-row:hover td { background:#f0e9ff; }
    .ae-sc-ae  { font-weight:800; color:#dc2626; font-size:.88rem; }
    .ae-sc-reg { font-weight:800; color:#16a34a; font-size:.88rem; }
    .ae-sc-gap { font-size:.72rem; color:#7c3aed; font-weight:700; }
    .ae-why    { font-size:.71rem; color:var(--slate); font-style:italic; line-height:1.4;
                 max-width:240px; }

    @media(max-width:860px){
      .ae-explain { grid-template-columns:1fr; }
      .ae-arch-box { display:none; }
      .ae-mid { grid-template-columns:1fr; }
      .ae-right { flex-direction:row; flex-wrap:wrap; }
    }

"""

html = html[:start_css] + NEW_CSS + html[end_css:]

# ── 2. HTML DEL BLOQUE AE (reemplaza todo entre <!-- AUTOENCODER --> y <!-- GRÁFICAS -->) ──
AE_START = "  <!-- AUTOENCODER -->"
AE_END   = "  <!-- GRÁFICAS -->"

if AE_START not in html or AE_END not in html:
    print("ERROR: anclas HTML no encontradas"); sys.exit(1)

s = html.index(AE_START)
e = html.index(AE_END, s)

NEW_HTML = """  <!-- AUTOENCODER -->
  <div id="ae-section">

    <div class="ae-header">
      <div class="stitle">Autoencoder &mdash; Detector de Anomal&iacute;as sin Etiquetas</div>
      <span class="ae-ml-badge">ML</span>
      <span class="ae-tech-note">sklearn MLPRegressor &middot; 20 features &middot; 107 iter. &middot; loss 0.027</span>
    </div>

    <!-- Explicacion + Arquitectura -->
    <div class="ae-explain">
      <div class="ae-explain-icon">&#129504;</div>
      <div class="ae-explain-txt">
        <h4>Aprende qu&eacute; es comportamiento normal y detecta lo que no encaja</h4>
        <p>
          Se entren&oacute; <strong>solo con las 1.298 publicaciones de cuentas Verificadas y Fan_Antiguo</strong>.
          Aprendi&oacute; qu&eacute; combinaci&oacute;n de plataforma, tipo de publicaci&oacute;n, antig&uuml;edad, interacciones y
          velocidad define el comportamiento <em>normal</em>. Luego intent&oacute; reconstruir cada una de las
          3.210 publicaciones con ese conocimiento. Cuanto mayor el error de reconstrucci&oacute;n,
          m&aacute;s an&oacute;mala es esa publicaci&oacute;n. <strong>Sin reglas. Sin etiquetas. El patr&oacute;n emerge solo.</strong>
        </p>
      </div>
      <div class="ae-arch-box">
        <div class="ae-arch-title">Arquitectura</div>
        <div class="ae-arch-flow">
          <div class="ae-arch-node input">20 entradas</div>
          <div class="ae-arch-arrow">&#8595; encoder</div>
          <div class="ae-arch-node enc">12</div>
          <div class="ae-arch-arrow">&#8595;</div>
          <div class="ae-arch-node enc">6</div>
          <div class="ae-arch-arrow">&#8595;</div>
          <div class="ae-arch-node bottleneck">3 &#128274;</div>
          <div class="ae-arch-arrow">&#8595; decoder</div>
          <div class="ae-arch-node dec">6</div>
          <div class="ae-arch-arrow">&#8595;</div>
          <div class="ae-arch-node dec">12</div>
          <div class="ae-arch-arrow">&#8595;</div>
          <div class="ae-arch-node output">20 salidas</div>
        </div>
      </div>
    </div>

    <!-- Grafica + Metricas + Hallazgo estrella -->
    <div class="ae-mid">
      <div class="ae-chart-wrap card" style="padding:16px 18px">
        <div class="stitle" style="margin-bottom:10px">
          Puntuaci&oacute;n mediana por tipo de cuenta
          <span style="font-size:.68rem;font-weight:400;color:var(--slate);text-transform:none;letter-spacing:0">&nbsp;&mdash;&nbsp;AE vs Reglas</span>
        </div>
        <canvas id="ch-ae" height="190"></canvas>
        <p style="font-size:.72rem;color:var(--slate);margin-top:8px;line-height:1.5">
          El AE empuja a los an&oacute;malos <strong>m&aacute;s arriba</strong> y a los normales <strong>m&aacute;s abajo</strong>
          que las reglas &mdash; es m&aacute;s discriminante en ambas direcciones.
        </p>
      </div>

      <div class="ae-right">
        <div class="ae-metrics">
          <div class="ae-metric corr">
            <div class="ae-metric-val">0.797</div>
            <div class="ae-metric-txt">
              <div class="ae-metric-lbl">Correlaci&oacute;n AE &harr; Reglas</div>
              <div class="ae-metric-sub">Coinciden en el 80% del dataset</div>
            </div>
          </div>
          <div class="ae-metric anom">
            <div class="ae-metric-val">1.640</div>
            <div class="ae-metric-txt">
              <div class="ae-metric-lbl">Publicaciones an&oacute;malas</div>
              <div class="ae-metric-sub">Score AE &gt; 50 sobre 3.210 total</div>
            </div>
          </div>
          <div class="ae-metric divg">
            <div class="ae-metric-val">5</div>
            <div class="ae-metric-txt">
              <div class="ae-metric-lbl">Casos divergentes</div>
              <div class="ae-metric-sub">AE detecta, reglas ignoraban</div>
            </div>
          </div>
        </div>

        <div class="ae-star">
          <div class="ae-star-tag">&#11088; Hallazgo estrella del modelo</div>
          <h5>@tatianalopez_ &mdash; ID&nbsp;2219</h5>
          <p>Las reglas la ignoran casi por completo. El AE la marca como <strong>altamente an&oacute;mala</strong>:
          su combinaci&oacute;n de plataforma, tipo de publicaci&oacute;n y horarios es estad&iacute;sticamente
          imposible de reconstruir desde el baseline normal.</p>
          <div class="ae-score-pair">
            <div class="ae-sp-item">
              <div class="ae-sp-val bad">83.3</div>
              <div class="ae-sp-lbl">Score AE</div>
            </div>
            <div class="ae-sp-item" style="display:flex;align-items:center;font-size:1.2rem;color:#a78bfa;font-weight:900;padding-top:4px">vs</div>
            <div class="ae-sp-item">
              <div class="ae-sp-val good">19.7</div>
              <div class="ae-sp-lbl">Reglas</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabla casos divergentes -->
    <div class="ae-div-wrap">
      <div class="stitle" style="margin-bottom:10px">
        Publicaciones que el AE detect&oacute; y las reglas ignoraban
        <span style="font-size:.68rem;font-weight:400;color:var(--slate);text-transform:none;letter-spacing:0">&nbsp;&mdash;&nbsp;score AE &gt; 50 &amp; reglas &lt; 30</span>
      </div>
      <table class="ae-div-table">
        <thead><tr>
          <th>ID</th><th>Handle</th><th>Plataforma</th><th>Perfil</th>
          <th>Score AE</th><th>Reglas</th><th>Diferencia</th><th>Por qu&eacute; lo detect&oacute;</th>
        </tr></thead>
        <tbody id="ae-div-body"></tbody>
      </table>
    </div>

  </div>

"""

html = html[:s] + NEW_HTML + html[e:]

# ── 3. JS: reemplazar bloque AE_DATA + renderAE ───────────────────────────────
AE_JS_START = "/* ══════════════════════════════════════════════════════════════\n   AUTOENCODER DATA + RENDER"
AE_JS_END   = "function cargarEstatico() {"

if AE_JS_START not in html or AE_JS_END not in html:
    print("ERROR: anclas JS no encontradas"); sys.exit(1)

sj = html.index(AE_JS_START)
ej = html.index(AE_JS_END, sj)

NEW_JS = """/* ══════════════════════════════════════════════════════════════
   AUTOENCODER — datos y render
   Calculado con ml/autoencoder.py (sklearn MLPRegressor)
   Arquitectura: 20->12->6->3->6->12->20 | loss 0.027 | 107 iter.
══════════════════════════════════════════════════════════════ */
const AE_DATA = {
  perfiles: [
    { nombre:'Bot_Sospechoso', ae:65.5, reg:66.0, color:'#dc2626', badge:'bot'  },
    { nombre:'Cuenta_Nueva',   ae:62.5, reg:51.7, color:'#ea580c', badge:'new'  },
    { nombre:'Anonimo',        ae:57.3, reg:44.5, color:'#d97706', badge:'anon' },
    { nombre:'Fan_Antiguo',    ae:11.7, reg:28.8, color:'#16a34a', badge:'fan'  },
    { nombre:'Verificado',     ae:11.1, reg:22.6, color:'#2563eb', badge:'ver'  },
  ],
  divergentes: [
    { id:2219, handle:'@tatianalopez_', plat:'TikTok',       perfil:'Anonimo',   ae:83.3, reg:19.7, star:true,
      why:'Patron global imposible de reconstruir: plataforma + tipo + horario incompatible con cualquier cuenta normal.' },
    { id:1759, handle:'@tatianalopez_', plat:'X',            perfil:'Anonimo',   ae:51.5, reg:20.8, star:true,
      why:'Misma cuenta activa en multiples plataformas en pocas horas — coordinacion sospechosa.' },
    { id:900,  handle:'@kevinmoreno34', plat:'Foro anonimo', perfil:'Verificado', ae:51.3, reg:29.4, star:false,
      why:'Cuenta verificada en foro anonimo: cruce de plataforma estadisticamente inusual para su perfil.' },
    { id:177,  handle:'@tatianalopez_', plat:'X',            perfil:'Anonimo',   ae:50.7, reg:20.7, star:true,
      why:'Tercer post de la misma cuenta en distintos horarios — patron de presencia atipico.' },
    { id:672,  handle:'@hectorcun',     plat:'Foro anonimo', perfil:'Verificado', ae:50.7, reg:30.0, star:false,
      why:'Verificado en foro anonimo: combinacion de features fuera del rango aprendido.' },
  ],
};

let chAE = null;

function renderAE() {
  // ── Grafico comparativo AE vs Reglas (Chart.js horizontal bar) ──
  const ctx = $('ch-ae');
  if (!ctx) return;
  if (chAE) chAE.destroy();

  const labels  = AE_DATA.perfiles.map(p => p.nombre.replace('_', ' '));
  const aeVals  = AE_DATA.perfiles.map(p => p.ae);
  const regVals = AE_DATA.perfiles.map(p => p.reg);
  const colors  = AE_DATA.perfiles.map(p => p.color);

  chAE = new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Score Anomalia (AE)',
          data: aeVals,
          backgroundColor: colors.map(c => c + 'dd'),
          borderColor: colors,
          borderWidth: 1.5,
          borderRadius: 5,
        },
        {
          label: 'Indice Sospecha (Reglas)',
          data: regVals,
          backgroundColor: colors.map(() => 'rgba(100,116,139,0.18)'),
          borderColor: colors.map(() => '#94a3b8'),
          borderWidth: 1.5,
          borderRadius: 5,
          borderDash: [4,2],
        },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { font:{ size:11 }, boxWidth:12, padding:16 } },
        tooltip: {
          callbacks: {
            label: ctx => ' ' + ctx.dataset.label + ': ' + ctx.parsed.x.toFixed(1),
          },
        },
      },
      scales: {
        x: {
          min: 0, max: 100,
          grid: { color: '#e2e8f0' },
          ticks: { font:{ size:10 } },
          title: { display:true, text:'Puntuacion mediana (0-100)', font:{ size:10 }, color:'#64748b' },
        },
        y: {
          grid: { display:false },
          ticks: { font:{ size:11 } },
        },
      },
    },
  });

  // ── Tabla de casos divergentes ──
  const tbody = $('ae-div-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  AE_DATA.divergentes.forEach(d => {
    const pc  = d.perfil === 'Verificado' ? 'ver' : 'anon';
    const gap = (d.ae - d.reg).toFixed(1);
    const row = document.createElement('tr');
    if (d.star) row.className = 'ae-star-row';
    row.innerHTML =
      '<td><code style="font-size:.7rem;color:var(--slate)">#' + d.id + '</code></td>' +
      '<td><strong>' + d.handle + '</strong>' + (d.star ? ' <span style="font-size:.75rem">&#11088;</span>' : '') + '</td>' +
      '<td><span style="font-size:.78rem">' + d.plat + '</span></td>' +
      '<td><span class="badge ' + pc + '">' + d.perfil + '</span></td>' +
      '<td class="ae-sc-ae">' + d.ae + '</td>' +
      '<td class="ae-sc-reg">' + d.reg + '</td>' +
      '<td class="ae-sc-gap">+' + gap + '</td>' +
      '<td class="ae-why">' + d.why + '</td>';
    tbody.appendChild(row);
  });
}

"""

html = html[:sj] + NEW_JS + html[ej:]

# ── 4. GUARDAR ────────────────────────────────────────────────────────────────
with open(PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("[OK] dashboard.html actualizado")
print("     - CSS AE: rediseno completo con arch-box, ae-star, ae-mid")
print("     - HTML AE: explain + arquitectura + Chart.js + metricas + hallazgo estrella + tabla")
print("     - JS: Chart.js horizontal grouped bar (AE vs Reglas), tabla con star-row")
