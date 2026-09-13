"""Ranking reproducible de mercados para yerba mate argentina.

Este modulo no consulta APIs ni usa un modelo generativo: transforma datos ya
guardados en una corrida en un ranking determinista y auditable.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIMENSIONS = {
    "demanda_y_aceptacion": {
        "weight": 45,
        "metrics": {
            "importacion_total_per_capita_usd": {"weight": 12, "higher_is_better": True, "required": True},
            "importacion_desde_argentina_per_capita_usd": {"weight": 18, "higher_is_better": True, "required": True},
            "crecimiento_importacion_3y_pct": {"weight": 15, "higher_is_better": True, "required": True},
        },
    },
    "acceso_comercial": {
        "weight": 25,
        "metrics": {
            "arancel_pct": {"weight": 25, "higher_is_better": False, "required": False},
        },
    },
    "capacidad_de_compra": {
        "weight": 15,
        "metrics": {
            "pbi_per_capita_usd": {"weight": 10, "higher_is_better": True, "required": False},
            "poblacion": {"weight": 5, "higher_is_better": True, "required": False},
        },
    },
    "riesgo_de_operar": {
        "weight": 15,
        "metrics": {
            "inflacion_pct": {"weight": 5, "higher_is_better": False, "required": False},
            "estabilidad_politica": {"weight": 5, "higher_is_better": True, "required": False},
            "calidad_regulatoria": {"weight": 5, "higher_is_better": True, "required": False},
        },
    },
}


def numeric(value: Any) -> float | None:
    """Convierte un valor a numero finito; nulos y valores no numericos quedan vacios."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def minmax(values: dict[str, float | None], higher_is_better: bool) -> dict[str, float | None]:
    available = [value for value in values.values() if value is not None]
    if not available:
        return {key: None for key in values}
    low, high = min(available), max(available)
    if low == high:
        return {key: 50.0 if value is not None else None for key, value in values.items()}
    scores = {}
    for key, value in values.items():
        if value is None:
            scores[key] = None
            continue
        score = 100 * (value - low) / (high - low)
        scores[key] = round(score if higher_is_better else 100 - score, 2)
    return scores


def prepare_market(raw: dict[str, Any]) -> dict[str, Any]:
    market = dict(raw)
    population = numeric(market.get("poblacion"))
    total_imports = numeric(market.get("importacion_total_usd"))
    arg_imports = numeric(market.get("importacion_desde_argentina_usd"))
    market["importacion_total_per_capita_usd"] = (total_imports / population) if total_imports is not None and population and population > 0 else None
    market["importacion_desde_argentina_per_capita_usd"] = (arg_imports / population) if arg_imports is not None and population and population > 0 else None
    for dimension in DIMENSIONS.values():
        for metric in dimension["metrics"]:
            market[metric] = numeric(market.get(metric))
    return market


def score_markets(raw_markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markets = [prepare_market(market) for market in raw_markets]
    metric_scores: dict[str, dict[str, float | None]] = {}
    for dimension in DIMENSIONS.values():
        for metric, config in dimension["metrics"].items():
            values = {market["pais_iso3"]: market.get(metric) for market in markets}
            metric_scores[metric] = minmax(values, config["higher_is_better"])

    ranked = []
    for market in markets:
        iso3 = market["pais_iso3"]
        missing = []
        available_weight = 0
        total_weight = 0
        dimension_scores = {}
        evidence = []
        for dimension_name, dimension in DIMENSIONS.items():
            present_weight = 0
            weighted_score = 0.0
            for metric, config in dimension["metrics"].items():
                total_weight += config["weight"]
                score = metric_scores[metric][iso3]
                value = market.get(metric)
                if score is None:
                    missing.append(metric)
                    continue
                available_weight += config["weight"]
                present_weight += config["weight"]
                weighted_score += score * config["weight"]
                evidence.append({"metrica": metric, "valor": round(value, 6), "puntaje_normalizado": score})
            dimension_scores[dimension_name] = round(weighted_score / present_weight, 2) if present_weight else None

        required_missing = [
            metric
            for metric, config in DIMENSIONS["demanda_y_aceptacion"]["metrics"].items()
            if config["required"] and market.get(metric) is None
        ]
        coverage = round(available_weight / total_weight, 3)
        weighted_total = sum(
            DIMENSIONS[name]["weight"] * score / 100
            for name, score in dimension_scores.items()
            if score is not None
        )
        # Reescala solo las dimensiones disponibles; la confianza conserva la penalizacion por faltantes.
        present_dimension_weight = sum(
            DIMENSIONS[name]["weight"] for name, score in dimension_scores.items() if score is not None
        )
        total_score = round(100 * weighted_total / present_dimension_weight, 2) if present_dimension_weight else None
        alerts = []
        if required_missing:
            alerts.append("Faltan datos criticos de comercio: " + ", ".join(required_missing))
        if coverage < 0.7:
            alerts.append(f"Cobertura de datos insuficiente ({coverage:.0%}); minimo requerido: 70%.")
        status = "RECOMENDADO" if not alerts else "REVISAR_DATOS"
        ranked.append({
            "pais_iso3": iso3,
            "pais": market.get("pais", iso3),
            "estado": status,
            "puntaje_total": total_score,
            "puntajes_dimension": dimension_scores,
            "evidencia": evidence,
            "alertas": alerts,
            "confianza_datos": coverage,
        })

    ranked.sort(key=lambda item: (item["estado"] != "RECOMENDADO", -(item["puntaje_total"] or -1), item["pais_iso3"]))
    for position, market in enumerate(ranked, start=1):
        market["posicion"] = position
    return ranked


def build_output(payload: dict[str, Any]) -> dict[str, Any]:
    markets = payload.get("mercados", [])
    if not isinstance(markets, list) or len(markets) < 2:
        raise ValueError("La entrada debe incluir al menos dos mercados en 'mercados'.")
    result = {
        "producto": {"nombre": "yerba mate", "hs": "0903"},
        "fecha_de_corrida_utc": payload.get("fecha_de_corrida_utc") or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "prioridad": payload.get("prioridad", "equilibrada"),
        "metodologia": {
            "pesos": {name: spec["weight"] for name, spec in DIMENSIONS.items()},
            "normalizacion": "min-max dentro de los paises con datos validos; 50 si todos empatan",
            "cobertura_minima": 0.7,
        },
        "ranking": score_markets(markets),
        "recomendacion_humana_requerida": True,
        "limitaciones": [
            "Las importaciones observadas no prueban preferencia del consumidor ni rentabilidad.",
            "Los datos de comercio pueden tener rezago de publicacion.",
            "El ranking prioriza investigacion comercial; no autoriza exportaciones ni inversiones.",
        ],
        "fuentes": payload.get("fuentes", []),
    }
    return result


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python src/ranking.py entrada.json salida.json")
    source, target = map(Path, sys.argv[1:])
    payload = json.loads(source.read_text(encoding="utf-8"))
    output = build_output(payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
