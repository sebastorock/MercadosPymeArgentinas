# Mercado Raiz

## Proposito

Mercado Raiz es un agente de apoyo a la decision comercial para una PyME argentina ficticia que trabaja con productores y artesanos regionales. Su primera version responde una pregunta acotada:

> ¿Que mercados internacionales conviene priorizar para exportar yerba mate argentina?

El sistema no autoriza exportaciones ni reemplaza la evaluacion comercial. Produce un ranking explicable para que una persona responsable decida si vale la pena profundizar cada mercado.

## Decision que apoya

El usuario propone entre 2 y 12 paises candidatos y una prioridad estrategica. El agente consulta datos publicos, calcula un puntaje por pais y devuelve un ranking estructurado, evidencias y alertas.

La primera version usa el codigo HS 0903 (mate) como definicion operativa del producto. Esta decision deja fuera productos relacionados que no esten clasificados de ese modo; se registra como limitacion deliberada.

## Fuentes y herramientas reales

1. **World Bank Indicators API v2:** PBI per capita, poblacion, inflacion, estabilidad politica y calidad regulatoria.
2. **UN Comtrade Preview API:** importaciones mundiales de HS 0903, importaciones originadas en Argentina y crecimiento comercial. Es la fuente primaria de aceptacion porque permite consultar el codigo HS 0903 con precision.
3. **WITS REST API:** aranceles cuando esten disponibles. WITS usa grupos propios de productos, por lo que el conector valida el catalogo antes de utilizar una respuesta.

Las respuestas crudas de las APIs se guardan por corrida junto a la entrada y la salida. El sistema no inventa valores cuando una fuente no devuelve un dato.

## Ranking v1

El puntaje total se expresa entre 0 y 100 y es una suma ponderada de cuatro dimensiones.

| Dimension | Peso | Senales iniciales |
|---|---:|---|
| Demanda y aceptacion | 45% | importaciones totales de HS 0903, importaciones desde Argentina, crecimiento cuando haya serie disponible |
| Acceso comercial | 25% | arancel aplicable a Argentina; si no existe, se alerta y se reduce la confianza |
| Capacidad de compra | 15% | PBI per capita y poblacion |
| Riesgo de operar | 15% | inflacion, estabilidad politica y calidad regulatoria |

Cada senal se normaliza solo frente a los paises incluidos en esa corrida. Los indicadores con una relacion negativa con la conveniencia, como inflacion y arancel, se invierten. Los pesos y subpesos son visibles en la salida.

La recomendacion no se emite si faltan datos criticos de comercio o si la cobertura de datos de un pais es menor a 70%. En ese caso se devuelve `REVISAR_DATOS`, no una posicion engañosa del ranking.

## Supervision humana (L0-L4)

- **L0 - automatico:** descargar datos publicos, validar formato, normalizar y calcular puntajes.
- **L1 - informacion:** mostrar ranking, fuentes, fechas y alertas.
- **L2 - revision:** una persona revisa los tres primeros mercados, los datos faltantes y las alertas antes de usar el resultado.
- **L3 - aprobacion:** responsable comercial aprueba si se inicia contacto, cotizacion o investigacion adicional.
- **L4 - firma:** responsable comercial de la PyME firma cualquier decision de inversion, precio, contrato o exportacion. El agente no ejecuta ninguna accion externa.

## Estructura

```text
prompts/       contrato del agente
corridas/      entradas, respuestas crudas, salidas y metadatos de tres corridas reales
src/           implementacion reproducible
DECISIONES.md  iteraciones y decisiones de alcance
```

## Como se reproducira una corrida

El comando y las dependencias se documentaran antes de generar las corridas de evidencia. Cada corrida conservara fecha/hora UTC, paises solicitados, prioridad, respuestas originales de API, parametros del ranking y salida JSON. Esto permite reconstruir el resultado aunque los datos externos cambien con el tiempo.

## Limitaciones conocidas de v1

- Los datos de comercio suelen ser anuales y pueden publicarse con demora.
- Las importaciones son evidencia de compra observada; no prueban por si solas preferencia del consumidor ni rentabilidad.
- HS 0903 representa yerba mate, no toda la oferta regional argentina.
- El ranking prioriza mercados para investigar, no predice ventas ni recomienda una inversion.

## Economia del sistema

La recoleccion y el calculo son deterministas y no usan tokens. La explicacion redactada por un modelo se separara del calculo: se usara un modelo pequeno y se registraran tokens de entrada y salida por corrida. La estimacion semanal/anual se completara con los datos de las tres corridas reales.

La capa de explicacion esta gobernada por los prompts incluidos: recibe solo una salida JSON verificada, no altera puntajes y debe marcar las alertas de cobertura. El calculo y las evidencias de las cinco corridas quedan disponibles aun si esa capa no esta activa.

## Estado

Implementado. Hay cinco corridas reproducibles en `corridas/`; el dashboard local permite explorarlas y simular pesos y mercados.
