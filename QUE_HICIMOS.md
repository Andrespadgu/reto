# Qué hicimos y cómo llegamos aquí

Este documento explica, sin tecnicismos, el camino que recorrimos desde tener solo un archivo
de datos hasta tener un sistema que puede decirle a alguien qué tan confiable es cada
publicación del caso "Cancelado".

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
  las 4 de la mañana — el 38% de todo el dataset apareció en esa hora.

---

## Paso 2 — Crear las señales de sospecha

Con lo que aprendimos, diseñamos **5 señales** que juntas forman el "índice de sospecha"
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

Aparte del índice de sospecha, creamos un **score de confiabilidad** independiente.
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
| **Cancelar** | 38.1% | Evidencia confiable y suficiente para actuar |

---

## Paso 5 — Traducir todo a la base de datos

Las fórmulas que diseñamos en Python las "instalamos" dentro de Supabase (la base de datos
en la nube) como una consulta permanente. Esto significa que el dashboard no tiene que
calcular nada — simplemente le pregunta a la base de datos y recibe los resultados ya
calculados para las 3.210 publicaciones.

También creamos 6 consultas listas para el dashboard:
- Cuántas publicaciones caen en cada decisión y en qué porcentaje
- Las 10 publicaciones más sospechosas
- Cómo se distribuyeron las publicaciones por plataforma
- La línea de tiempo hora a hora (para ver la ola viral)
- El semáforo de confiabilidad (cuántas publicaciones son verdes, amarillas, rojas)
- Las cuentas más sospechosas agrupadas por usuario

---

## Paso 6 — El chatbot de demostración

Para el pitch, construimos un chatbot que puede responder preguntas sobre el sistema.
**No usa inteligencia artificial real** — eso costaría dinero y podría fallar en vivo.
En cambio, tiene 15 respuestas pregrabadas para las preguntas que con mayor probabilidad
va a hacer el jurado:

- ¿Cómo funciona el índice de sospecha?
- ¿Por qué se recomienda cancelar?
- ¿Cuántas cuentas son bots?
- ¿Cómo detectaron el contenido reciclado?
- ¿Por qué no usaron Machine Learning?

El chatbot normaliza lo que escribe el usuario (ignora tildes, mayúsculas, errores de tipeo)
y busca la respuesta más cercana. Si no entiende la pregunta, responde de forma amable y
sugiere qué sí puede responder. Nunca falla — siempre da una respuesta.

---

## Dónde están los archivos

```
elt/
  eda_exploracion.py       ← el código que exploró los datos (Paso 1)
  features_derivadas.py    ← el código que diseñó y validó las 5 señales (Paso 2 y 3)
  calibracion_umbrales.py  ← el código que justificó los cortes 30 y 50 (Paso 4)
  supabase_sql.sql         ← las fórmulas instaladas en la base de datos (Paso 5)
chatbot/
  intenciones.json         ← las 15 respuestas pregrabadas (Paso 6)
  matcher.js               ← el motor que conecta preguntas con respuestas (Paso 6)
```

---

## Qué falta

- **La base de datos en la nube (Supabase):** un integrante del equipo está configurando
  el proyecto y subiendo los datos. Cuando esté listo, el dashboard puede conectarse.

- **El dashboard HTML:** el archivo visual que muestra todo — las gráficas, los porcentajes
  de decisión, la decisión final en grande, y el chatbot. Se construye sobre todo lo que
  ya está listo.
