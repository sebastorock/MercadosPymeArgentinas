# Decisiones e iteraciones

## 2026-09-13 - Alcance inicial

Se definio un agente de priorizacion de mercados internacionales para una PyME argentina ficticia que comercializa productos regionales y artesanales.

**Alternativa considerada:** un ranking generico para cualquier producto tradicional.

**Decision:** reducir el alcance a yerba mate en la version 1.

**Motivo:** el producto tiene una clasificacion comercial internacional clara (HS 0903), lo que hace posible contrastar demanda e importaciones de origen argentino con datos observables. Ponchos, alpargatas, camisetas y dulce de leche se consideraran extensiones futuras, porque sus clasificaciones requieren reglas adicionales y podrian mezclar productos no equivalentes.

## 2026-09-13 - Criterio de aceptacion

**Problema:** la "popularidad" no debe inferirse de una afirmacion del modelo ni de datos no verificables.

**Decision:** usar importaciones del producto desde Argentina, importaciones totales de la categoria y su crecimiento como evidencia de aceptacion y demanda revelada.

**Limite:** estos datos no prueban preferencia del consumidor final ni margen comercial. El agente lo declara en las alertas y requiere revision humana.

## 2026-09-13 - Fuentes de datos

**Decision inicial:** combinar World Bank Indicators API v2 con WITS REST API.

**Motivo:** la primera aporta contexto economico, institucional y de riesgo; la segunda aporta comercio y aranceles por producto, comprador y proveedor. Se conservaran las respuestas originales para que cada resultado pueda auditarse.

## 2026-09-13 - Validacion temprana de conectores

Se consultaron con exito la World Bank Indicators API v2 y el catalogo de indicadores de WITS REST API. La primera devolvio datos de PBI per capita para Espana; la segunda devolvio metadatos de comercio, incluyendo `MPRT-TRD-VL` (valor de importacion) y `CNTRY-GRWTH` (crecimiento comercial).

**Falla encontrada:** una consulta preliminar con el codigo `0903` enviado directamente a WITS devolvio HTTP 400.

**Decision:** no asumir que el codigo HS usado internamente por WITS coincide literalmente con `0903`. Antes de ejecutar corridas, el conector debe consultar y validar el catalogo de productos de WITS, guardar la respuesta cruda y registrar la correspondencia seleccionada. Si no se encuentra una correspondencia inequívoca para yerba mate, la corrida queda bloqueada como `REVISAR_DATOS` en vez de usar una categoria mas amplia sin declararlo.

## 2026-09-13 - Fuente primaria de aceptacion de producto

**Hallazgo:** el catalogo de WITS TradeStats expone grupos de producto agregados; una consulta directa para `0903` no se resolvio como un producto valido. En cambio, la Preview API publica de UN Comtrade acepto una consulta de importaciones con `cmdCode=0903`, pais reportante, Argentina como socio y flujo de importacion.

**Decision:** usar UN Comtrade como fuente primaria para el valor importado de yerba mate y su origen argentino. WITS se conserva para validar aranceles solo si su catalogo produce una correspondencia verificable. Esta combinacion distingue demanda de producto de las condiciones de acceso comercial.

## 2026-09-13 - Calculo separado de la redaccion

**Decision:** el ranking se calcula con codigo determinista en `src/ranking.py`, separado de cualquier explicacion generada por un modelo.

**Motivo:** el orden de los paises debe poder reconstruirse sin depender de una respuesta probabilistica. El codigo normaliza cada metrica min-max dentro de la corrida, invierte las variables negativas (arancel e inflacion), conserva la evidencia usada y aplica una cobertura minima de 70%. El modelo, cuando se incorpore, solo explicara el resultado estructurado y no podra modificar los puntajes.

## 2026-09-13 - Interpretacion de corridas con cobertura limitada

Las cinco corridas se guardaron como `REVISAR_DATOS` porque algunos indicadores de comercio o gobierno no estaban disponibles en la fuente para todos los mercados. Esta no es una recomendacion de exportacion: es una lista de investigacion priorizada. La salida conserva los datos disponibles, las alertas y la confianza, y exige validacion humana antes de cualquier contacto comercial, precio, contrato o envio.

## 2026-09-13 - Capa de explicacion

El ranking y los estados se calculan sin lenguaje natural. Los prompts en `prompts/` restringen una capa posterior de explicacion para que solo convierta el JSON verificado en una recomendacion legible, cite evidencia y no cambie puntajes. Esta separacion reduce costo y riesgo: el modelo pequeno explica; el codigo reproducible decide el orden.

## 2026-09-13 - Primera corrida: fallo de adaptacion de codigos

La primera ejecucion con ESP, USA, DEU, JPN, BRA, CHL, MEX y URY se detuvo antes de descargar indicadores porque el adaptador esperaba el campo `ISO3` en la tabla de paises de UN Comtrade. La respuesta real usa `PartnerCodeIsoAlpha3` y `PartnerCode`.

**Decision:** corregir el adaptador para usar los nombres de campo oficiales y conservar alternativas defensivas. La carpeta de esta ejecucion fallida quedo vacia; no se la considera evidencia de una corrida real porque no hubo consultas de mercado ni salida de ranking.

## 2026-09-13 - Gobierno

El agente opera en L0-L1 para descarga, calculo y reporte. La decision de avanzar comercialmente pertenece a una persona responsable en L2-L4. El sistema no envia mensajes, contrata, cotiza, modifica bases de datos externas ni ejecuta transacciones.
