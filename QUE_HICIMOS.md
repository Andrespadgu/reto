# Qué hicimos y cómo llegamos aquí

Este documento explica, sin tecnicismos, el camino que recorrimos desde tener solo un archivo
de datos hasta tener un sistema completo que analiza publicaciones, calcula scores, muestra
un dashboard interactivo, incluye un modelo de inteligencia artificial y tiene un chatbot
que puede responder preguntas del jurado en tiempo real.

---

## El punto de partida

Teníamos un archivo (`BASE.csv`) con **3.210 publicaciones** de redes sociales relacionadas
con el caso de Kai Duarte: posts, comentarios, reposts, transcripciones de audio y capturas
de pantalla descritas en texto. Todo mezclado — publicaciones reales, fabricadas, recicladas
de otro escándalo de 2023, y de cuentas creadas esa misma noche solo para amplificar el ruido.

La pregunta era: **¿cómo saber cuáles son confiables y cuáles son ruido fabricado?**

---

## Paso 1 — Entender qué había en los datos

Antes de hacer cualquier cálculo, miramos qué había realmente en el archivo.

Lo que encontramos más llamativo:

- **El 44% de las cuentas tenía menos de 30 días de antigüedad.** En un evento que duró
  7 horas, casi la mitad de quienes publicaron eran cuentas recién creadas. Eso es una
  señal enorme de que algo estaba coordinado.

- **Los bots tenían más seguidores que las cuentas verificadas.** Eso fue contra-intuitivo
  pero tiene lógica: los bots en este caso tenían cuentas compradas o infladas, no eran
  cuentas pequeñas y descartables. Por eso no pudimos usar el número de seguidores como
  señal de confianza — habría invertido el resultado.

- **Solo el 5.9% del contenido era reciclado**, pero ese 5.9% era el más directamente
  fabricado: texto idéntico al de un escándalo de otro creador de 2023, con los nombres
  cambiados.

- **La velocidad de viralización tenía un valor extremo**: el valor máximo era 12 veces
  mayor que el del 99% de los registros. Eso significaba que no podíamos medir la velocidad
  de forma directa — teníamos que compararla con el resto del dataset, no con una escala fija.

- **El evento duró solo 7 horas y 43 minutos.** El pico de publicaciones fue entre las 3 y
  las 4 de la mañana — el 38% de todo el dataset apareció en esa hora. Ese volumen a esa
  hora de la madrugada no es orgánico. Es una de las señales más fuertes del caso.

---

## Paso 2 — Crear las señales de sospecha

Con lo que aprendimos, diseñamos **5 señales** que juntas forman el "Índice de Sospecha"
de cada publicación. Cada señal tiene un peso según qué tan importante es:

**Señal 1 — El tipo de cuenta (peso: 35%)**
Es la señal más poderosa. Una cuenta marcada como Bot tiene sospecha máxima. Una cuenta nueva
o anónima tiene sospecha media. Una cuenta verificada o un fan antiguo tiene sospecha baja.
Vale el 35% porque el perfil de quien publica es lo más difícil de falsear a corto plazo.

**Señal 2 — Qué tan nueva es la cuenta (peso: 25%)**
Una cuenta creada hace 0 días no tiene historial que la respalde. Una cuenta de 10 años sí.
Cuanto más nueva la cuenta, más sospechosa. La medimos comparando cada cuenta con todas las
demás del dataset — no con un número fijo — porque hay cuentas desde 0 hasta 4.000 días.

**Señal 3 — Qué tan rápido se viralizó (peso: 20%)**
Una publicación que consigue miles de interacciones por minuto en la primera hora no lo hace
orgánicamente — hay amplificación coordinada. También la medimos comparando con el resto,
porque el valor máximo era tan extremo que una escala fija habría aplastado al 99% del dataset.

**Señal 4 — Si el contenido es reciclado (peso: 10%)**
Si el texto de la publicación coincide con contenido de otro contexto o de otro año, es la
prueba más directa de manipulación. Peso bajo (10%) porque solo afecta al 5.9% del dataset,
pero cuando aparece, pesa mucho individualmente.

**Señal 5 — El tipo de publicación (peso: 10%)**
Una transcripción de audio o descripción de captura es evidencia de segunda mano —
no verificable directamente. Un post original de alguien que dice haberlo vivido pesa más.

Estas 5 señales se combinan en un número entre 0 y 100. A más alto el número, más sospechosa
es la publicación.

---

## Paso 3 — Crear la señal de confiabilidad

Aparte del Índice de Sospecha, creamos un **Score de Confiabilidad** independiente.
No es simplemente "lo opuesto de la sospecha" — mide cosas distintas:

- **Qué tan antigua es la cuenta (40%):** Una cuenta con años de historia tiene un track
  record verificable. Es la señal más fuerte de credibilidad.

- **Cuánta gente sin relación entre sí dice lo mismo (40%):** Si 5 cuentas que no se conocen
  describen el mismo hecho, eso es mucho más creíble que una sola cuenta que lo afirma.
  En el dataset, el 58.8% de los registros tenía 0 corroboraciones — la mayoría de las
  publicaciones estaba sola en su versión de los hechos.

- **El tipo de publicación (20%):** Un post original pesa más que un repost de algo que
  alguien más dijo.

---

## Paso 4 — Decidir los umbrales de decisión

Este fue el paso más importante y el que más cuidado requirió.

La primera idea fue dividir el dataset en tres partes iguales: el tercio más sospechoso
recibe "cancelar", el tercio del medio "bajar video", y el tercio más limpio "mantener".
**Eso estaba mal.** Dividir en tercios iguales significa que aunque el 80% del contenido
fuera legítimo, el sistema igual recomendaría "cancelar" a un tercio de él. El resultado
no dependería de los datos — dependería de la aritmética.

La solución fue anclar los cortes en **dónde viven naturalmente cada tipo de cuenta**:

- Las cuentas Verificadas y los Fans Antiguos tienen índices de sospecha entre 19 y 27.
  El corte de "mantener" se puso en **30** — justo por encima de ese grupo, para que el
  94% de las cuentas verificadas quede en "mantener" y no sea falsamente acusada.

- Entre las cuentas Anónimas (índice promedio: 49) y las Cuentas Nuevas (índice promedio: 57)
  hay un salto natural. El corte de "cancelar" se puso en **50** — captura el 97.8% de los
  bots y el 82.1% de las cuentas nuevas, sin arrastrar a los Anónimos que pueden ser legítimos.

El resultado final con estos cortes:

| Decisión | % del dataset | Qué significa |
|---|---|---|
| **Mantener** | 36.4% | Evidencia demasiado débil para actuar |
| **Bajar el video** | 25.5% | Zona gris — retirar el contenido pero no romper contratos |
| **Cancelar** | 38.1% | Evidencia con señales suficientes para actuar |

---

## Paso 5 — El hallazgo que cambió la decisión final

Al ver los resultados, algo llamó la atención: la diferencia entre "cancelar" (38.1%) y
"mantener" (36.4%) era de **solo 1.7 puntos porcentuales**. Prácticamente un empate.

Tomar una decisión contractual irreversible — romper el contrato de Kai Duarte y notificar
a tres marcas patrocinadoras — basándose en una diferencia de 1.7% no es responsable.
El sistema tiene que ser honesto sobre eso.

Por eso creamos un cuarto estado: **"Evidencia Dividida"**. Cuando la diferencia entre
la primera y segunda opción es menor a 5 puntos, el dashboard no dice "CANCELAR" en rojo
sino que muestra un banner violeta con el mensaje "EVIDENCIA DIVIDIDA" y una recomendación
más cautelosa: bajar el video temporalmente, activar revisión humana y no tomar acciones
contractuales hasta validar las fuentes originales.

Este estado es también la respuesta más honesta que el sistema puede dar: el dataset está
genuinamente dividido, y eso en sí mismo es información.

---

## Paso 6 — Traducir todo a la base de datos

Las fórmulas que diseñamos se instalaron dentro de **Supabase** (la base de datos en la nube)
como una consulta permanente. Esto significa que el dashboard no tiene que calcular nada
por su cuenta — simplemente le pregunta a la base de datos y recibe los resultados ya
calculados para las 3.210 publicaciones.

También preparamos 6 consultas listas:
- Cuántas publicaciones caen en cada decisión y en qué porcentaje
- Las 10 publicaciones más sospechosas
- Cómo se distribuyeron las publicaciones por plataforma
- La línea de tiempo hora a hora (para ver la ola viral de las 3 AM)
- El semáforo de confiabilidad (cuántas publicaciones son verdes, amarillas, rojas)
- Las cuentas más sospechosas agrupadas por usuario

El flujo es: los datos brutos llegan a Supabase sin modificarse → Supabase calcula los
scores con SQL → el dashboard lee esos resultados en tiempo real. Nunca se modifica el
archivo original.

---

## Paso 7 — El dashboard visual

Construimos un archivo HTML que funciona como el panel de control de todo el análisis.
Al abrirlo en el navegador, muestra:

**El banner de veredicto** (lo primero que se ve): un rectángulo grande que dice cuál es
la decisión recomendada — violeta para "Evidencia Dividida" en este caso — con la
recomendación operativa específica paso a paso.

**Los tres porcentajes de decisión**: cancelar, bajar el video, mantener — cada uno con
su barra de progreso y la cantidad de publicaciones que lo respaldan.

**5 señales clave en tarjetas**: cuántos bots se detectaron, cuánto contenido reciclado,
el pico de las 3 AM, las publicaciones sin corroboración, y cuántas cuentas verificadas
están en calma. Cada una con un número y una interpretación en una línea.

**5 hallazgos del análisis**: los patrones más importantes explicados en lenguaje directo,
sin términos técnicos.

**Gráficas**: la línea de tiempo hora por hora del evento, la distribución por plataforma,
el semáforo de confiabilidad, las cuentas más sospechosas y las publicaciones más
sospechosas con sus señales activas.

**El indicador de conexión**: una luz verde en la esquina del header que confirma que los
datos vienen de Supabase en tiempo real.

**El chatbot** (botón flotante abajo a la derecha): visible y accesible en cualquier
momento del pitch.

---

## Paso 8 — El modelo de inteligencia artificial (Autoencoder)

Además del sistema de reglas, construimos un **modelo de machine learning** que funciona
de una manera completamente diferente: no tiene reglas. Nadie le dijo qué hace sospechosa
a una publicación.

**Cómo funciona en términos simples:**

Imagina que el modelo es un estudiante que durante semanas solo lee publicaciones de cuentas
confiables — verificadas y fans antiguos. Aprende qué hace "normal" a esas publicaciones:
la forma en que combinan su antigüedad, su plataforma, su velocidad de viralización, su tipo
de contenido y otras 16 características.

Luego le mostramos una publicación nueva — digamos, un bot. El modelo intenta "describirla"
usando solo lo que aprendió de las cuentas normales. Y falla. Esa incapacidad de describir
lo que ve es el **Score de Anomalía**: mientras más alto, más diferente es esa publicación
de todo lo que el modelo consideraba normal.

No hay reglas. No hay pesos manuales. El modelo encontró el patrón solo.

**Lo que encontró:**

| Tipo de cuenta | Score de Anomalía promedio |
|---|---|
| Bot Sospechoso | 72.4 — muy anómalo |
| Cuenta Nueva | 65.7 — muy anómalo |
| Anónimo | 60.9 — moderadamente anómalo |
| Fan Antiguo | 15.8 — normal (era parte del entrenamiento) |
| Verificado | 15.6 — normal (era parte del entrenamiento) |

La separación entre el grupo normal (≈15) y el grupo anómalo (60-72) emergió sola, sin
que nadie codificara esa distinción.

**El hallazgo más llamativo — el caso de @tatianalopez_:**

Las reglas le daban a esta cuenta un Índice de Sospecha de 19.7 — prácticamente la marcaban
como confiable. La cuenta tiene 4.000 días de antigüedad, sin velocidad viral extrema,
sin contenido reciclado. Individualmente, ninguna señal encendía una alarma.

El modelo de inteligencia artificial le dio un Score de Anomalía de **83.3**. La razón:
la combinación completa de sus comportamientos — plataforma, tipo de publicaciones, horario,
interacciones, frecuencia — es estadísticamente imposible de reconstruir desde el patrón
de cuentas normales. No es que una cosa esté mal; es que todo junto no encaja.

Eso es lo que puede hacer un modelo de ML que un sistema de reglas no puede: detectar
anomalías en el patrón global aunque ninguna señal individual sea extrema.

**La relación entre los dos sistemas:**

Los dos sistemas coinciden en el 80% del análisis (correlación de 0.797). Eso es bueno:
significa que se validan mutuamente. El 20% restante son los casos más interesantes:
el modelo encontró 5 publicaciones que las reglas ignoraban, y ningún caso donde las
reglas alertaran pero el modelo dijera que todo estaba bien.

La sección del autoencoder está visible en el dashboard, con el explicación del modelo,
las barras de score por perfil y la tabla de los 5 casos divergentes.

---

## Paso 9 — El chatbot de demostración

Para el pitch, construimos un chatbot que puede responder preguntas sobre todo el sistema.
**No usa inteligencia artificial real de un proveedor externo** — eso costaría dinero y
podría fallar en vivo sin internet. En cambio, tiene **19 respuestas pregrabadas** para
las preguntas que con mayor probabilidad va a hacer el jurado, organizadas en grupos:

- Sobre el Índice de Sospecha y cómo se calcula
- Sobre el Score de Confiabilidad
- Sobre las tres decisiones (cancelar, bajar el video, mantener)
- Sobre el autoencoder y el Score de Anomalía
- Sobre el caso @tatianalopez_ (el hallazgo más llamativo del ML)
- Sobre los bots y las cuentas nuevas detectadas
- Sobre el contenido reciclado
- Sobre el pico de las 3 AM
- Sobre la "Evidencia Dividida" y por qué no se recomienda cancelar directamente
- Sobre la arquitectura técnica del sistema

El chatbot normaliza lo que escribe el usuario — ignora tildes, mayúsculas, errores de
tipeo — y busca la respuesta más cercana. Si no entiende la pregunta, responde de forma
amable y sugiere qué sí puede responder. Nunca falla: siempre da una respuesta.

---

## Dónde están los archivos

```
BASE.csv                      ← los datos originales (nunca se modifican)
dashboard.html                ← el panel visual completo (abrir en el navegador)
QUE_HICIMOS.md                ← este documento

elt/
  crear_tabla.sql             ← crea la tabla en Supabase
  cargar_csv.py               ← sube los datos a Supabase
  supabase_sql.sql            ← instala las fórmulas en la base de datos
  grants.sql                  ← da permisos de lectura al dashboard

ml/
  autoencoder.py              ← el modelo de inteligencia artificial (ejecutar con Python)
  resultados_autoencoder.csv  ← los scores de anomalía para las 3.210 publicaciones
  figura_autoencoder.png      ← visualización de 4 paneles con los resultados del modelo

chatbot/
  intenciones.json            ← las 19 respuestas pregrabadas
  matcher.js                  ← el motor que conecta preguntas con respuestas
```

---

## Resultado final

El sistema entrega tres cosas concretas para la decisión del caso Kai Duarte:

1. **Un veredicto con matiz:** "Evidencia Dividida" — no un binario irresponsable, sino
   una recomendación escalonada que reconoce la ambigüedad real del dataset.

2. **Dos sistemas que se validan:** las reglas manuales (auditables, explicables) y el
   autoencoder (que aprende sin reglas). Coinciden en el 80% y se complementan en el 20%.

3. **Un hallazgo que solo el ML podía ver:** @tatianalopez_, ignorada por las reglas con
   un score de 19.7, marcada como altamente anómala por el modelo con 83.3. La combinación
   de comportamientos que ninguna regla individual capturaba.
