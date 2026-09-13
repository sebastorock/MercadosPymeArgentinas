"""Descarga y conserva datos publicos para una corrida de Mercado Raiz.

Uso:
  python src/collect_data.py ESP USA DEU JPN --output corridas/2026-09-13-exploratoria

No sobrescribe una corrida existente. Guarda cada respuesta API en `raw/` y
escribe `entrada_ranking.json`, lista para `ranking.py`.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WB_INDICATORS = {
    "pbi_per_capita_usd": "NY.GDP.PCAP.CD",
    "poblacion": "SP.POP.TOTL",
    "inflacion_pct": "FP.CPI.TOTL.ZG",
    "estabilidad_politica": "PV.EST",
    "calidad_regulatoria": "GE.REG.EST",
}
COMTRADE_PERIODS = (2024,)
COMTRADE_ARGENTINA_PARTNER = 32


def request_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "MercadoRaiz/1.0 (academic project)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=12) as response:  # noqa: S310 - public fixed endpoints
                payload = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    payload = gzip.decompress(payload)
            return json.loads(payload.decode("utf-8-sig"))
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Reintentos agotados")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cached_json(path: Path, url: str) -> Any:
    """Reutiliza evidencia cruda ya guardada; evita repetir consultas lentas."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = request_json(url)
    write_json(path, data)
    return data


def latest_world_bank_value(data: Any) -> tuple[float | None, str | None]:
    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        return None, None
    for observation in data[1]:
        if observation.get("value") is not None:
            return float(observation["value"]), str(observation.get("date"))
    return None, None


def comtrade_values(data: Any) -> dict[int, float]:
    rows = data.get("data", []) if isinstance(data, dict) else []
    values: dict[int, float] = {}
    for row in rows:
        if row.get("partner2Code") != 0 or row.get("customsCode") != "C00" or row.get("motCode") != 0:
            continue
        value = row.get("primaryValue", row.get("primary_value"))
        year = row.get("refYear")
        if value is not None and year is not None:
            values[int(year)] = float(value)
    return values


def cagr_percent(series: list[float | None]) -> float | None:
    valid = [(index, value) for index, value in enumerate(series) if value is not None and value > 0]
    if len(valid) < 2:
        return None
    first_index, first = valid[0]
    last_index, last = valid[-1]
    years = last_index - first_index
    if years <= 0:
        return None
    return ((last / first) ** (1 / years) - 1) * 100


def get_comtrade_codes() -> dict[str, int]:
    data = request_json("https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json")
    records = data.get("results", data) if isinstance(data, dict) else data
    output = {}
    for record in records:
        # La tabla oficial usa PascalCase; se mantienen alternativas para
        # tolerar una futura variante del endpoint.
        iso3 = record.get("PartnerCodeIsoAlpha3") or record.get("ISO3") or record.get("iso3")
        code = record.get("PartnerCode") or record.get("id") or record.get("areaCode") or record.get("partnerCode")
        if iso3 and code is not None:
            output[str(iso3).upper()] = int(code)
    return output


def collect_market(iso3: str, numeric_code: int, raw_dir: Path) -> dict[str, Any]:
    market: dict[str, Any] = {"pais_iso3": iso3, "pais": iso3, "fuentes": {}}
    for field, indicator in WB_INDICATORS.items():
        url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}?format=json&date=2019:2025&per_page=100"
        data = cached_json(raw_dir / f"world_bank_{iso3}_{indicator}.json", url)
        value, year = latest_world_bank_value(data)
        market[field] = value
        market["fuentes"][field] = {"fuente": "World Bank Indicators API v2", "indicador": indicator, "ano": year, "url": url}

    totals: list[float | None] = []
    argentina: list[float | None] = []
    for partner, target in ((0, totals), (COMTRADE_ARGENTINA_PARTNER, argentina)):
        values: dict[int, float] = {}
        for period in COMTRADE_PERIODS:
            parameters = urllib.parse.urlencode({
                "period": period,
                "reporterCode": numeric_code,
                "partnerCode": partner,
                "flowCode": "M",
                "cmdCode": "0903",
                "maxRecords": 20,
            })
            url = f"https://comtradeapi.un.org/public/v1/preview/C/A/HS?{parameters}"
            suffix = "mundo" if partner == 0 else "argentina"
            data = cached_json(raw_dir / f"comtrade_{iso3}_{period}_{suffix}.json", url)
            by_year = comtrade_values(data)
            values.update(by_year)
            time.sleep(0.3)
        target.extend(values.get(period) for period in COMTRADE_PERIODS)
    market["importacion_total_usd"] = totals[-1]
    market["importacion_desde_argentina_usd"] = argentina[-1]
    market["crecimiento_importacion_3y_pct"] = cagr_percent(totals)
    market["fuentes"]["comercio"] = {
        "fuente": "UN Comtrade Preview API",
        "hs": "0903",
        "periodos": list(COMTRADE_PERIODS),
        "importacion_total_usd_por_ano": totals,
        "importacion_desde_argentina_usd_por_ano": argentina,
    }
    return market


def main() -> None:
    parser = argparse.ArgumentParser(description="Recolecta datos publicos para Mercado Raiz.")
    parser.add_argument("countries", nargs="+", help="Codigos ISO3 de 2 a 12 mercados candidatos.")
    parser.add_argument("--output", required=True, help="Directorio nuevo de la corrida.")
    parser.add_argument("--priority", default="equilibrada", choices=("equilibrada", "crecimiento", "bajo_riesgo", "acceso_comercial"))
    args = parser.parse_args()
    countries = [country.upper() for country in args.countries]
    if not 2 <= len(countries) <= 12 or len(set(countries)) != len(countries):
        raise SystemExit("Indique entre 2 y 12 codigos ISO3 distintos.")
    output = Path(args.output)
    if output.exists() and (output / "salida.json").exists():
        raise SystemExit(f"La corrida ya esta completa: {output}")
    raw_dir = output / "raw"
    output.mkdir(parents=True, exist_ok=True)
    codes = get_comtrade_codes()
    absent = [country for country in countries if country not in codes]
    if absent:
        raise SystemExit("No se encontraron codigos UN Comtrade para: " + ", ".join(absent))
    markets = [collect_market(country, codes[country], raw_dir) for country in countries]
    payload = {
        "fecha_de_corrida_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "prioridad": args.priority,
        "mercados": markets,
        "fuentes": [
            "World Bank Indicators API v2",
            "UN Comtrade Preview API",
        ],
    }
    write_json(output / "entrada_ranking.json", payload)
    from ranking import build_output
    write_json(output / "salida.json", build_output(payload))
    index_path = output.parent / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"corridas": []}
    index["corridas"] = [item for item in index.get("corridas", []) if item.get("id") != output.name]
    index["corridas"].append({"id": output.name, "fecha": payload["fecha_de_corrida_utc"], "prioridad": args.priority, "archivo": f"{output.name}/salida.json"})
    index["corridas"].sort(key=lambda item: item["fecha"])
    write_json(index_path, index)
    print(f"Datos guardados en {output}")


if __name__ == "__main__":
    main()
