# User prompt - plantilla de corrida v1

Analiza la priorizacion de mercados para exportar **yerba mate argentina (HS 0903)**.

Entrada esperada:

```json
{
  "paises_candidatos": ["ISO3", "..."],
  "prioridad": "equilibrada | crecimiento | bajo_riesgo | acceso_comercial",
  "fecha_de_corrida_utc": "ISO-8601",
  "datos_world_bank": [],
  "datos_wits": [],
  "parametros_ranking": {}
}
```

Usa los datos entregados para calcular y explicar el ranking. La salida debe tener exactamente esta estructura:

```json
{
  "producto": {"nombre": "yerba mate", "hs": "0903"},
  "fecha_de_corrida_utc": "",
  "prioridad": "",
  "metodologia": {
    "pesos": {},
    "normalizacion": "min-max dentro de los paises con datos validos",
    "cobertura_minima": 0.7
  },
  "ranking": [
    {
      "posicion": 1,
      "pais_iso3": "",
      "pais": "",
      "estado": "RECOMENDADO | REVISAR_DATOS | NO_ELEGIBLE",
      "puntaje_total": 0,
      "puntajes_dimension": {},
      "evidencia": [],
      "alertas": [],
      "confianza_datos": 0
    }
  ],
  "recomendacion_humana_requerida": true,
  "limitaciones": [],
  "fuentes": []
}
```
