import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen

EIA_API_BASE = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
EIA_FUEL_API_BASE = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
EIA_BALANCING_AUTHORITY = "SOCO"

LOW_CARBON_FUELS = {"NUC", "WAT", "WND", "SUN", "GEO"}
FOSSIL_FUELS = {"COL", "NG", "OIL"}


def get_live_grid_data():
    """
    Fetch the two latest hourly demand observations for the
    Southern Company balancing authority from the U.S. EIA API.

    Returns None if no API key is configured or if the external
    data source is temporarily unavailable.
    """
    api_key = os.getenv("EIA_API_KEY")

    if not api_key:
        return None

    params = [
        ("api_key", api_key),
        ("frequency", "hourly"),
        ("data[0]", "value"),
        ("facets[respondent][]", EIA_BALANCING_AUTHORITY),
        ("facets[type][]", "D"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", "2"),
    ]

    url = f"{EIA_API_BASE}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))

        rows = payload.get("response", {}).get("data", [])

        if not rows:
            return None

        latest = rows[0]
        latest_demand = float(latest["value"])
        previous_demand = None
        demand_change_percent = None

        if len(rows) > 1:
            previous_demand = float(rows[1]["value"])

            if previous_demand != 0:
                demand_change_percent = (
                    (latest_demand - previous_demand)
                    / previous_demand
                    * 100
                )

        if demand_change_percent is None:
            condition = "unknown"
        elif demand_change_percent >= 2:
            condition = "rising"
        elif demand_change_percent <= -2:
            condition = "falling"
        else:
            condition = "stable"

        return {
            "source": "U.S. Energy Information Administration",
            "dataset": "Form EIA-930 hourly electric grid data",
            "balancing_authority": EIA_BALANCING_AUTHORITY,
            "period": latest.get("period"),
            "demand_mwh": round(latest_demand, 2),
            "previous_demand_mwh": (
                round(previous_demand, 2)
                if previous_demand is not None
                else None
            ),
            "demand_change_percent": (
                round(demand_change_percent, 2)
                if demand_change_percent is not None
                else None
            ),
            "condition": condition,
        }

    except Exception as error:
        print("EIA live grid request failed:", error)
        return None


def get_live_carbon_signal():
    """
    Describe the latest EIA generation mix for SOCO.

    This is a relative generation-mix signal, not a direct
    hourly CO2-intensity measurement.
    """
    api_key = os.getenv("EIA_API_KEY")

    if not api_key:
        return None

    params = [
        ("api_key", api_key),
        ("frequency", "hourly"),
        ("data[0]", "value"),
        ("facets[respondent][]", EIA_BALANCING_AUTHORITY),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", "100"),
    ]

    url = f"{EIA_FUEL_API_BASE}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))

        rows = payload.get("response", {}).get("data", [])

        if not rows:
            return None

        latest_period = rows[0].get("period")
        generation_by_fuel = {}

        for row in rows:
            if row.get("period") != latest_period:
                continue

            fuel = (
                row.get("fueltype")
                or row.get("type")
                or row.get("fuel")
                or "UNK"
            )

            try:
                generation = float(row.get("value", 0) or 0)
            except (TypeError, ValueError):
                continue

            generation_by_fuel[fuel] = {
                "fuel": fuel,
                "generation_mwh": round(generation, 2),
            }

        positive = [
            item
            for item in generation_by_fuel.values()
            if item["generation_mwh"] > 0
        ]

        total_positive_generation = sum(
            item["generation_mwh"]
            for item in positive
        )

        if total_positive_generation <= 0:
            return None

        low_carbon_generation = sum(
            item["generation_mwh"]
            for item in positive
            if item["fuel"] in LOW_CARBON_FUELS
        )

        fossil_generation = sum(
            item["generation_mwh"]
            for item in positive
            if item["fuel"] in FOSSIL_FUELS
        )

        low_carbon_share = (
            low_carbon_generation
            / total_positive_generation
            * 100
        )

        fossil_share = (
            fossil_generation
            / total_positive_generation
            * 100
        )

        if low_carbon_share >= 60:
            signal = "lower_carbon_mix"
            message = (
                "A large share of current generation is coming from "
                "nuclear and renewable sources."
            )
        elif low_carbon_share >= 35:
            signal = "mixed_generation"
            message = (
                "The current grid mix includes a meaningful blend of "
                "lower-carbon and fossil generation."
            )
        else:
            signal = "fossil_heavy_mix"
            message = (
                "The current generation mix is more heavily dependent "
                "on fossil generation."
            )

        sorted_mix = sorted(
            positive,
            key=lambda item: item["generation_mwh"],
            reverse=True,
        )

        return {
            "source": "U.S. Energy Information Administration",
            "dataset": "Form EIA-930 hourly generation by energy source",
            "balancing_authority": EIA_BALANCING_AUTHORITY,
            "period": latest_period,
            "signal": signal,
            "message": message,
            "low_carbon_share_percent": round(low_carbon_share, 1),
            "fossil_share_percent": round(fossil_share, 1),
            "total_positive_generation_mwh": round(
                total_positive_generation,
                2,
            ),
            "generation_mix": sorted_mix,
            "method": (
                "Live generation-mix signal. Low-carbon share counts "
                "nuclear, hydro, wind, solar, and geothermal generation. "
                "This is not a direct hourly CO2-intensity measurement."
            ),
        }

    except Exception as error:
        print("EIA carbon-awareness request failed:", error)
        return None
