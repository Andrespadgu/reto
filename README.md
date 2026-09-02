# Reto DSAA — "Cancelado"
**Data Science e Inteligencia Artificial · Facultad de Ingeniería**  
4 horas de desarrollo · Equipos de 4 integrantes · Pitch final de 6 minutos

---

## El caso

Son las 11:47 p. m. En una cuenta anónima de X aparece un clip de 14 segundos. En el audio (transcrito como texto en la base de datos, nunca como archivo real) se escucha una voz que suena como la de **Kai Duarte** —el creador de contenido más seguido entre los universitarios del país— admitiendo que amañó al ganador de un sorteo millonario prometido a sus seguidores hace un mes.

En cuarenta minutos el clip acumula 12.000 reposts. Tres marcas patrocinadoras anuncian que están "evaluando la situación". Aparecen testigos, capturas de conversaciones privadas y cuentas que nadie reconoce. Algunos fans defienden a Kai con pruebas propias. Otros usuarios notan algo raro: una de las "pruebas" más compartidas es idéntica a un escándalo de otro creador de hace tres años, con los nombres cambiados.

Para las 6:00 a. m., la plataforma y las marcas deben tomar una decisión. El problema: nadie sabe todavía qué es verdad.

**Nuestro equipo asume el rol del área de análisis contratada de emergencia** para construir una herramienta que le diga a quien toma la decisión qué tan confiable es cada pieza de evidencia, y por qué.

---

## Línea del tiempo del caso

| Hora | Evento |
|------|--------|
| **11:47 p. m.** | Clip de 14 segundos aparece en cuenta anónima de X. Se escucha una voz que "suena a" Kai Duarte admitiendo fraude en el sorteo. |
| **12:27 a. m.** | El clip acumula 12.000 reposts en 40 minutos. |
| **1:00 a. m.** | Tres marcas patrocinadoras (PulsoTech, UrbanKrew, NovaVolt) publican que están "evaluando la situación". |
| **1:30 a. m.** | Aparecen "testigos": capturas, conversaciones privadas, hilos armados por cuentas desconocidas. **Una de las pruebas más compartidas es reciclada de un caso de hace 3 años con los nombres cambiados.** |
| **6:00 a. m.** | Deadline de decisión: la plataforma y las marcas deben actuar. |

---

## La tensión del caso

| Lo que parece real | Lo que genera dudas |
|--------------------|---------------------|
| Testigos que dicen haber estado ahí | Testigos que solo buscan viralidad |
| Cuentas con años de antigüedad activa | Cuentas creadas esa misma noche |
| Evidencia que a simple vista parece genuina | Evidencia reciclada de otro contexto con nombres cambiados |

> *"Una reputación y varios millones de pesos dependen de separar la señal real del ruido fabricado — antes de que sea tarde."*

---

## La base de datos

**Versión:** v2.1 · **Registros:** 3.210 · **Archivo:** `BASE.csv`

Base 100% texto y datos tabulares. Sin imágenes ni videos reales: cuando la historia menciona una captura o un video, en la base aparece como texto (transcripción o descripción).

### Variables

| Grupo | Variable | Descripción |
|-------|----------|-------------|
| **Identificación** | `ID_Publicacion` | Identificador único de la publicación |
| | `ID_Publicacion_Padre` | A qué publicación responde o cita (vacío si es original) |
| | `ID_Usuario` | Identificador del usuario |
| | `Usuario_Handle` | Alias del usuario en la plataforma |
| **Clasificación** | `Plataforma` | Red social: X, TikTok, Instagram, Foro anónimo |
| | `Tipo_Publicacion` | Post original / Comentario / Repost-Cita / Descripción de captura / Transcripción de audio-video |
| **Contenido** | `Texto_Publicacion` | Texto real de la publicación o transcripción de la evidencia |
| | `Hashtags_Usados` | Hashtags incluidos en la publicación |
| | `Marca_Mencionada` | Marca referenciada: PulsoTech, UrbanKrew, NovaVolt (cuando aplica) |
| | `Fecha_Hora_Publicacion` | Timestamp exacto de la publicación |
| **Perfil del usuario** | `Perfil_Usuario` | Verificado / Cuenta_Nueva / Bot_Sospechoso / Fan_Antiguo / Anónimo |
| | `Antigüedad_Cuenta_Dias` | Días desde la creación de la cuenta |
| | `Num_Seguidores_Cuenta` | Número de seguidores |
| **Señales de comportamiento** | `Num_Interacciones` | Total de likes, comentarios y compartidos |
| | `Velocidad_Viralizacion` | Interacciones por minuto durante la primera hora |
| | `Contenido_Reciclado` | Si el contenido coincide con una publicación de otro contexto o fecha anterior |
| | `Corroboraciones_Independientes` | Cuántos usuarios sin conexión aparente describen el mismo hecho |

### Variables derivadas a crear (pendiente de diseño)

El reto exige **crear variables nuevas** a partir de las originales para calcular índices propios:

- `Indice_Sospecha` — cruza antigüedad de cuenta + velocidad de viralización + perfil de usuario
- `Tasa_Coordinacion` — detecta si cuentas sin relación aparente publican contenido similar en ventanas de tiempo cortas
- `Score_Confiabilidad` — puntuación final ponderada (0–100) por registro
- `Peso_Prueba` — ponderación de qué tan verificable es la evidencia presentada en el texto

---

## Las tres decisiones posibles

El sistema debe recomendar, con porcentajes basados en el análisis, cuál de estas acciones tomar:

| Decisión | Descripción |
|----------|-------------|
| **Cancelar / Romper contrato** | Las pruebas son suficientemente confiables para actuar contra Kai Duarte |
| **Bajar el video** | La evidencia justifica retirar el contenido pero no romper contratos |
| **Mantener / Dejar que siga su curso** | Las pruebas son demasiado débiles o fabricadas para actuar |

Los porcentajes se calcularán con base en las variables de peso y los índices derivados (diseño pendiente).

---

## Nuestra solución: Dashboard interactivo

### Qué construimos

Un **archivo HTML autocontenido** (sin backend propio) conectado a **Supabase** como base de datos, diseñado de forma genérica para que funcione con cualquier caso similar —no solo el de Kai Duarte.

### Arquitectura

```
CSV(s) del caso
      │
      ▼
 Supabase (nueva instancia)
      │
      ▼
 dashboard.html  ──────────────────────────────────────┐
      │                                                  │
      ├── Selector de caso (Caso 1 / Caso 2 / Caso 3)  │
      ├── Gráficas de análisis exploratorio              │
      ├── Panel de decisión con porcentajes              │
      ├── Decisión final destacada                       │
      └── Chatbot (respuestas simuladas pregrabadas) ────┘
```

### Funcionalidades del dashboard

#### 1. Selector de caso
El usuario puede subir múltiples archivos CSV a Supabase (Caso 1, Caso 2, Caso 3…) y elegir cuál visualizar desde un menú desplegable. El dashboard recarga los datos del caso seleccionado dinámicamente.

#### 2. Gráficas de análisis
- Distribución de publicaciones por plataforma y tipo
- Línea de tiempo de viralización con marcadores de contenido sospechoso
- Mapa de cuentas sospechosas (coordenadas o tablero de red)
- Histograma de score de confiabilidad por publicación (semáforo: verde / amarillo / rojo)
- Ranking de cuentas por índice de sospecha

#### 3. Panel de porcentajes de decisión
Sección prominente que muestra, basada en el análisis de los datos:

```
🔴 Cancelar / Romper contrato:  XX%
🟡 Bajar el video:               XX%
🟢 Mantener:                     XX%
```

Los porcentajes se derivan de los índices calculados sobre los registros del CSV seleccionado.

#### 4. Decisión final
En grande, centrado, con el color de su categoría:

```
┌─────────────────────────────────────┐
│  DECISIÓN RECOMENDADA               │
│  ██ CANCELAR / ROMPER CONTRATO      │
│  Confianza: 80%                     │
└─────────────────────────────────────┘
```

#### 5. Chatbot (simulado)
Panel lateral de chat donde el usuario puede hacer preguntas sobre el caso. Las respuestas son simulaciones pregrabadas basadas en las preguntas más esperadas durante el pitch, para evitar consumo de tokens en una demostración académica.

**Preguntas cubiertas (simuladas):**
- "¿Por qué se recomienda cancelar?"
- "¿Cuántas cuentas sospechosas hay?"
- "¿Cuál es la publicación más confiable?"
- "¿Qué hashtags dominan el ruido?"
- "Muéstrame las publicaciones recicladas"

Cuando el usuario hace una pregunta, el chatbot muestra la respuesta en texto **y genera un sub-dashboard dinámico** con las gráficas relevantes para esa pregunta.

El módulo también soporta **consultas SQL directas a Supabase** (modo avanzado), permitiendo al equipo demostrar integración real con la base de datos.

### Tecnologías

| Componente | Tecnología |
|------------|------------|
| Frontend | HTML + CSS + JavaScript (vanilla, sin frameworks) |
| Gráficas | Chart.js (CDN, sin instalación) |
| Base de datos | Supabase (nuevo proyecto, anon key pública) |
| Chatbot | Respuestas simuladas en JSON pregrabado + consultas SQL via Supabase JS client |
| Deploy | Archivo estático — se abre directo en navegador o se sube a GitHub Pages |

---

## Generalización del sistema

La solución está diseñada para funcionar con **cualquier caso de cancelación o controversia en redes sociales**, siempre que el CSV tenga columnas equivalentes a las del caso Kai Duarte. El dashboard detecta automáticamente las columnas disponibles y adapta las gráficas.

Flujo para un nuevo caso:
1. Exportar o preparar el CSV con los datos del nuevo caso
2. Subir el CSV a Supabase (tabla dinámica por caso)
3. Seleccionar el nuevo caso en el menú del dashboard
4. El análisis y los porcentajes se recalculan automáticamente

---

## Criterios de evaluación del reto

| Criterio | Peso en la evaluación |
|----------|----------------------|
| Análisis y manejo de los datos | ✅ |
| Uso de Data Science e Inteligencia Artificial | ✅ |
| Desempeño de la solución (señal vs ruido) | ✅ |
| Calidad del prototipo o interfaz gráfica | ✅ |
| Explicabilidad de los resultados | ✅ |
| Aprovechamiento de todo el equipo | ✅ |
| Presentación final (pitch de 6 minutos) | ✅ |

---

## Distribución del equipo por nivel

| Nivel | Semestres | Responsabilidad |
|-------|-----------|-----------------|
| **Inicial** | 1.° – 3.° | Limpieza de texto, reglas simples de sospecha, construcción de la interfaz HTML |
| **Intermedio** | 4.° – 6.° | Similitud de texto para detectar contenido reciclado, features numéricas para los índices |
| **Avanzado** | 7.° – 8.° | Modelo de confiabilidad, capa de explicabilidad, detección de coordinación entre cuentas |

---

## Estructura del repositorio

```
reto/
├── BASE.csv            # Base de datos sintética v2.1 (3.210 registros)
├── RETO.pdf            # Presentación oficial del reto (DSAA)
├── CANCELADO.pdf       # Propuesta completa del reto con columnas y criterios
└── README.md           # Este archivo
```

> **Próximo archivo a construir:** `dashboard.html` — el prototipo funcional que integra todo lo descrito arriba.
