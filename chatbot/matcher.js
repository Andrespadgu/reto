/**
 * matcher.js — Motor de matching del chatbot de demo
 * Proyecto: Sistema Indice de Sospecha / Score Confiabilidad — caso "Cancelado"
 *
 * Sin dependencias externas. Funciona con apertura directa de un HTML en el navegador
 * (fetch local) o incluido como <script> con el JSON incrustado (ver seccion INTEGRACION).
 *
 * API publica:
 *   ChatbotMatcher.init(catalogo)  -> carga el objeto JSON ya parseado
 *   ChatbotMatcher.responder(texto) -> devuelve un string (nunca undefined, nunca error)
 *
 * Si el JSON se carga via fetch, usar:
 *   ChatbotMatcher.cargarDesdeURL("chatbot/intenciones.json").then(() => { ... })
 */

const ChatbotMatcher = (() => {
  // ── Estado interno ──────────────────────────────────────────────────────────
  let _catalogo = null;

  // Umbral minimo de similitud para activar el fallback de similitud aproximada.
  // Validado contra el dataset real: 0.72 evita falsos positivos en preguntas
  // fuera del guion (clima, bolsa, etc.) mientras cubre todos los typos del caso.
  const UMBRAL_SIMILITUD = 0.72;

  // ── Normalizacion de texto ──────────────────────────────────────────────────
  // Elimina tildes, convierte a minusculas y borra todo lo que no sea letra o numero.
  // Esto hace que "Indice_Sospecha", "índice sospecha" e "indice   sospecha!" sean iguales.
  function _normalizar(texto) {
    if (typeof texto !== "string") return "";
    return texto
      .toLowerCase()
      // NFD separa la letra base del acento; luego se borran los combinados (u0300-u036f)
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      // Conservar solo letras, numeros y espacios
      .replace(/[^a-z0-9\s]/g, " ")
      // Colapsar espacios multiples
      .replace(/\s+/g, " ")
      .trim();
  }

  // ── Similitud tipo SequenceMatcher (algoritmo de longest common subsequence) ──
  // Implementacion minima sin dependencias. Calcula cuantos caracteres comparten
  // dos strings en el mismo orden relativo, y devuelve un ratio 0.0-1.0.
  // Es suficiente para tolerar errores de tipeo de 1-3 caracteres en keywords cortas.
  function _similitud(a, b) {
    if (!a || !b) return 0;
    if (a === b) return 1;

    const la = a.length;
    const lb = b.length;

    // Para strings muy distintos en largo, la similitud maxima ya es baja:
    // evita comparaciones costosas.
    if (Math.max(la, lb) / (Math.min(la, lb) || 1) > 3) return 0;

    // Matriz de programacion dinamica para LCS
    const dp = Array.from({ length: la + 1 }, () => new Array(lb + 1).fill(0));
    let lcs = 0;
    for (let i = 1; i <= la; i++) {
      for (let j = 1; j <= lb; j++) {
        if (a[i - 1] === b[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
          if (dp[i][j] > lcs) lcs = dp[i][j];
        }
      }
    }
    // Ratio: 2 * LCS / (len_a + len_b) — igual que difflib.SequenceMatcher
    return (2 * lcs) / (la + lb);
  }

  // ── Seleccion aleatoria de respuesta ───────────────────────────────────────
  // Si el jurado repite la misma pregunta, el bot da una respuesta diferente.
  function _elegirRespuesta(lista) {
    if (!lista || lista.length === 0) return null;
    return lista[Math.floor(Math.random() * lista.length)];
  }

  // ── Motor de matching principal ─────────────────────────────────────────────
  /**
   * Dado un texto de entrada, devuelve la mejor respuesta del catalogo.
   * Estrategia en tres niveles (de mayor a menor prioridad):
   *
   * 1. Keyword exacta: si alguna keyword normalizada esta CONTENIDA en el texto
   *    normalizado, esa intencion gana de inmediato. Favorece keywords largas
   *    (mas especificas) sobre las cortas.
   *
   * 2. Similitud aproximada: si ninguna keyword exacta coincide, se compara
   *    cada keyword contra el texto completo usando _similitud(). Si la mejor
   *    puntuacion supera UMBRAL_SIMILITUD, se usa esa intencion.
   *
   * 3. Fallback: si ningun nivel supera el umbral, se devuelve un mensaje del
   *    array "fallback" del JSON. Nunca se devuelve undefined ni error.
   *
   * @param {string} textoUsuario
   * @returns {string}
   */
  function responder(textoUsuario) {
    if (!_catalogo) {
      return "El sistema de chat no esta listo aun. Intenta en un momento.";
    }
    if (!textoUsuario || textoUsuario.trim() === "") {
      return _elegirRespuesta(_catalogo.fallback) || "Escribe una pregunta para comenzar.";
    }

    const textoNorm = _normalizar(textoUsuario);
    const intenciones = _catalogo.intenciones || [];

    // ── Nivel 1: busqueda de keyword exacta (substring) ──────────────────────
    // Se evalua cada keyword de cada intencion. Si hay mas de una coincidencia,
    // gana la que tiene la keyword MAS LARGA (mas especifica).
    let mejorExacta = null;
    let largoCandidato = 0;

    for (const intencion of intenciones) {
      for (const kw of intencion.keywords || []) {
        const kwNorm = _normalizar(kw);
        if (kwNorm.length === 0) continue;
        if (textoNorm.includes(kwNorm)) {
          if (kwNorm.length > largoCandidato) {
            largoCandidato = kwNorm.length;
            mejorExacta = intencion;
          }
        }
      }
    }

    if (mejorExacta) {
      return _elegirRespuesta(mejorExacta.respuestas) || _fallback();
    }

    // ── Nivel 2: similitud aproximada (tolera typos y variantes) ─────────────
    // Se compara cada keyword contra el TEXTO COMPLETO del usuario (no solo la keyword).
    // Esto permite que "como calculas sospecha" active la intencion aunque no sea
    // ninguna keyword exacta del catalogo.
    let mejorIntencion = null;
    let mejorScore = 0;

    for (const intencion of intenciones) {
      for (const kw of intencion.keywords || []) {
        const kwNorm = _normalizar(kw);
        if (kwNorm.length === 0) continue;

        // Opcion A: similitud directa keyword vs texto completo
        const s1 = _similitud(kwNorm, textoNorm);
        // Opcion B: el texto contiene una subcadena muy parecida a la keyword
        // Se evalua una ventana deslizante del mismo largo que la keyword
        let s2 = 0;
        if (textoNorm.length >= kwNorm.length) {
          const ventana = kwNorm.length;
          for (let i = 0; i <= textoNorm.length - ventana; i += 2) {
            const sub = textoNorm.slice(i, i + ventana);
            const s = _similitud(kwNorm, sub);
            if (s > s2) s2 = s;
          }
        }

        const scoreKw = Math.max(s1, s2);
        if (scoreKw > mejorScore) {
          mejorScore = scoreKw;
          mejorIntencion = intencion;
        }
      }
    }

    if (mejorIntencion && mejorScore >= UMBRAL_SIMILITUD) {
      return _elegirRespuesta(mejorIntencion.respuestas) || _fallback();
    }

    // ── Nivel 3: fallback ─────────────────────────────────────────────────────
    return _fallback();
  }

  function _fallback() {
    const lista = (_catalogo && _catalogo.fallback) || [
      "No tengo esa informacion en este demo. Puedo explicarte el Indice_Sospecha, el Score_Confiabilidad o las tres decisiones del sistema.",
    ];
    return _elegirRespuesta(lista);
  }

  // ── API de inicializacion ───────────────────────────────────────────────────
  /**
   * Carga el catalogo desde un objeto JavaScript ya parseado.
   * Usar cuando el JSON esta incrustado en el HTML.
   */
  function init(catalogoObj) {
    _catalogo = catalogoObj;
  }

  /**
   * Carga el catalogo desde una URL via fetch.
   * Usar cuando el HTML se sirve desde un servidor local o Supabase Storage.
   * Devuelve una Promise que resuelve cuando el catalogo esta listo.
   *
   * @param {string} url - Ruta al archivo intenciones.json
   * @returns {Promise<void>}
   */
  function cargarDesdeURL(url) {
    return fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error("No se pudo cargar el catalogo: " + r.status);
        return r.json();
      })
      .then(function (data) {
        _catalogo = data;
      })
      .catch(function (err) {
        console.error("[ChatbotMatcher] Error cargando intenciones.json:", err);
        // El fallback de emergencia evita que el chat quede roto
        _catalogo = {
          intenciones: [],
          fallback: [
            "El sistema de chat esta en modo reducido. Por favor recarga la pagina.",
          ],
        };
      });
  }

  // ── Exportar API publica ────────────────────────────────────────────────────
  return { init, cargarDesdeURL, responder };
})();


// ══════════════════════════════════════════════════════════════════════════════
// INTEGRACION — Pegar este bloque en el HTML del dashboard
// ══════════════════════════════════════════════════════════════════════════════
//
// OPCION A: con servidor local (o Supabase Storage / Vercel)
// -----------------------------------------------------------
//
//   <script src="chatbot/matcher.js"></script>
//   <script>
//     ChatbotMatcher.cargarDesdeURL("chatbot/intenciones.json").then(() => {
//       console.log("Chatbot listo");
//     });
//   </script>
//
//
// OPCION B: apertura directa como archivo (file://) — sin servidor
// ---------------------------------------------------------------
// fetch no funciona con file://, asi que se incrusta el JSON directamente:
//
//   <script src="chatbot/matcher.js"></script>
//   <script>
//     // Pegar aqui el contenido de intenciones.json como objeto JS:
//     const CATALOGO_INCRUSTADO = { "meta": {...}, "intenciones": [...], "fallback": [...] };
//     ChatbotMatcher.init(CATALOGO_INCRUSTADO);
//   </script>
//
//
// INTERFAZ DE CHAT (HTML+JS minimal — pegar en el body del dashboard)
// -------------------------------------------------------------------
//
//   <div id="chat-container" style="
//       max-width: 480px;
//       font-family: sans-serif;
//       border: 1px solid #e2e8f0;
//       border-radius: 12px;
//       overflow: hidden;
//   ">
//     <div id="chat-header" style="
//         background: #1e293b;
//         color: #f8fafc;
//         padding: 12px 16px;
//         font-weight: 600;
//     ">
//       Asistente — Caso Kai Duarte
//     </div>
//     <div id="chat-mensajes" style="
//         height: 340px;
//         overflow-y: auto;
//         padding: 16px;
//         background: #f8fafc;
//         display: flex;
//         flex-direction: column;
//         gap: 10px;
//     "></div>
//     <div style="display: flex; border-top: 1px solid #e2e8f0;">
//       <input
//         id="chat-input"
//         type="text"
//         placeholder="Escribe tu pregunta sobre el caso..."
//         style="flex:1; padding: 12px; border: none; outline: none; font-size: 14px;"
//         onkeydown="if(event.key==='Enter') chatEnviar()"
//       />
//       <button onclick="chatEnviar()" style="
//           padding: 12px 18px;
//           background: #3b82f6;
//           color: white;
//           border: none;
//           cursor: pointer;
//           font-weight: 600;
//       ">Enviar</button>
//     </div>
//   </div>
//
//   <script>
//     function chatAgregarMensaje(texto, esBot) {
//       const cont = document.getElementById("chat-mensajes");
//       const burbuja = document.createElement("div");
//       burbuja.style.cssText = [
//         "max-width: 85%",
//         "padding: 10px 14px",
//         "border-radius: 10px",
//         "font-size: 14px",
//         "line-height: 1.5",
//         esBot
//           ? "background: #ffffff; border: 1px solid #e2e8f0; align-self: flex-start;"
//           : "background: #3b82f6; color: white; align-self: flex-end;",
//       ].join(";");
//       burbuja.textContent = texto;
//       cont.appendChild(burbuja);
//       cont.scrollTop = cont.scrollHeight;
//     }
//
//     function chatEnviar() {
//       const input = document.getElementById("chat-input");
//       const texto = input.value.trim();
//       if (!texto) return;
//       chatAgregarMensaje(texto, false);
//       input.value = "";
//       // Pequeño delay para que se vea natural en la demo
//       setTimeout(() => {
//         chatAgregarMensaje(ChatbotMatcher.responder(texto), true);
//       }, 320);
//     }
//
//     // Mensaje de bienvenida
//     chatAgregarMensaje(
//       "Hola. Puedo explicarte como funciona el sistema de analisis del caso Kai Duarte: " +
//       "el Indice_Sospecha, el Score_Confiabilidad, las tres decisiones, y los datos del dataset. " +
//       "¿Por donde empezamos?",
//       true
//     );
//   </script>
//
// ══════════════════════════════════════════════════════════════════════════════
