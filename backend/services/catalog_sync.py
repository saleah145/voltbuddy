from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy.orm import Session

import models

SOCRATA_BASE = "https://data.energystar.gov/resource"


@dataclass(frozen=True)
class DatasetConfig:
    dataset_id: str
    category: str
    label: str
    annual_fields: tuple[str, ...]
    capacity_fields: tuple[tuple[str, str], ...] = ()
    power_fields: tuple[str, ...] = ()
    feature_fields: tuple[str, ...] = ()
    product_type_fields: tuple[str, ...] = ("product_type", "type")


DATASETS = {
    "refrigerator": DatasetConfig(
        "p5st-her9", "refrigerator", "ENERGY STAR Residential Refrigerators",
        ("annual_energy_use_kwh_yr", "annual_energy_use_kwh_year"),
        (("capacity_total_volume_ft3", "cu ft"),),
        feature_fields=("configuration", "additional_model_information"),
    ),
    "washer": DatasetConfig(
        "bghd-e2wd", "washer", "ENERGY STAR Residential Clothes Washers",
        ("annual_energy_use_kwh_year", "annual_energy_use_kwh_yr"),
        (("volume_cubic_feet", "cu ft"),),
        feature_fields=("load_configuration", "connected", "additional_model_information"),
    ),
    "dryer": DatasetConfig(
        "t9u7-4d2j", "dryer", "ENERGY STAR Residential Clothes Dryers",
        ("estimated_annual_energy_use_kwh_yr", "annual_energy_use_kwh_year"),
        (("drum_capacity_cu_ft", "cu ft"),),
        feature_fields=("type", "additional_model_information"),
    ),
    "dishwasher": DatasetConfig(
        "q8py-6w3f", "dishwasher", "ENERGY STAR Residential Dishwashers",
        ("annual_energy_use_kwh_year", "annual_energy_use_kwh_yr"),
        feature_fields=("drying_method", "tub_material", "additional_product_features"),
    ),
    "tv": DatasetConfig(
        "pd96-rr3d", "tv", "ENERGY STAR Televisions",
        ("annual_energy_consumption_kwh_year", "annual_energy_consumption_kwh_yr", "annual_energy_use_kwh_year"),
        feature_fields=("product_type", "additional_model_information"),
    ),
    "air conditioner": DatasetConfig(
        "5xn2-dv4h", "air conditioner", "ENERGY STAR Room Air Conditioners",
        ("annual_energy_use_kwh_yr", "annual_energy_use_kwh_year"),
        (("cooling_capacity_btu_hour", "Btu/hr"),),
        power_fields=("rated_cooling_power_watts", "input_power_watts"),
        feature_fields=("type", "installation_mounting_type", "heating_mode"),
    ),
    "ev charger": DatasetConfig(
        "5jwe-c8xm", "ev charger", "ENERGY STAR EV Chargers AC",
        ("annual_energy_use_kwh_yr",),
        power_fields=("maximum_nameplate_output_current_a",),
        feature_fields=("input_voltage_v", "network_protocol_capable", "connected_functionality"),
    ),
    "computer": DatasetConfig(
        "rxdj-2c88", "computer", "ENERGY STAR Computers",
        (),
        feature_fields=("type", "processor_brand", "operating_system_name", "additional_model_information"),
    ),
    "display": DatasetConfig(
        "qbg3-d468", "display", "ENERGY STAR Displays",
        (),
        (("screen_size_inches", "in"),),
        feature_fields=("display_type", "panel_type", "native_resolution_pixels", "additional_model_information"),
        product_type_fields=("display_type",),
    ),
    "air purifier": DatasetConfig(
        "gaa3-swy6", "air purifier", "ENERGY STAR Room Air Cleaners",
        (),
        (("room_size_sq_ft", "sq ft"),),
        feature_fields=("room_size_sq_ft", "smoke_free_clean_air_delivery", "additional_model_information"),
    ),
    "dehumidifier": DatasetConfig(
        "mgiu-hu4z", "dehumidifier", "ENERGY STAR Dehumidifiers",
        ("annual_energy_consumption_kwh_yr",),
        (("dehumidifier_water_removal_capacity_per_appendix_x1_pints_day", "pints/day"),),
        feature_fields=("dehumidifier_type", "refrigerant_type", "additional_model_information"),
        product_type_fields=("dehumidifier_type",),
    ),
    "freezer": DatasetConfig(
        "8t9c-g3tn", "freezer", "ENERGY STAR Residential Freezers",
        ("annual_energy_use_kwh_yr",),
        (("capacity_total_volume_ft3", "cu ft"),),
        feature_fields=("type", "defrost_type", "compact", "built_in", "additional_model_information"),
    ),
}


def _first(row: dict[str, Any], fields: tuple[str, ...]):
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return value
    return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _feature_text(row: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    parts = []
    for field in fields:
        value = row.get(field)
        if value not in (None, "", "No", "N/A"):
            parts.append(str(value))
    return " · ".join(dict.fromkeys(parts))[:1200] or None


def normalize_row(config: DatasetConfig, row: dict[str, Any]) -> dict[str, Any] | None:
    model_number = _first(row, ("model_number", "model_no", "model"))
    if not model_number:
        return None

    brand = _first(row, ("brand_name", "brand"))
    model_name = _first(row, ("model_name", "product_name"))
    energy_star_id = _first(row, ("pd_id", "energy_star_unique_id"))
    annual_kwh = _float(_first(row, config.annual_fields))

    capacity = None
    capacity_unit = None
    for field, unit in config.capacity_fields:
        maybe = _float(row.get(field))
        if maybe is not None:
            capacity, capacity_unit = maybe, unit
            break

    rated_power_kw = None
    power_value = _float(_first(row, config.power_fields)) if config.power_fields else None
    if power_value is not None:
        # Most ENERGY STAR power fields are watts; if clearly tiny, preserve as kW.
        rated_power_kw = power_value / 1000 if power_value > 50 else power_value

    product_type = _first(row, config.product_type_fields)
    source_key = f"{config.dataset_id}:{energy_star_id or brand or ''}:{model_number}"
    source_url = f"https://data.energystar.gov/d/{config.dataset_id}"

    return {
        "source_key": source_key[:240],
        "energy_star_id": str(energy_star_id) if energy_star_id is not None else None,
        "category": config.category,
        "brand": str(brand).strip() if brand else None,
        "model_name": str(model_name).strip() if model_name else None,
        "model_number": str(model_number).strip(),
        "product_type": str(product_type).strip() if product_type else None,
        "annual_kwh": annual_kwh,
        "rated_power_kw": rated_power_kw,
        "capacity": capacity,
        "capacity_unit": capacity_unit,
        "upc": str(row.get("upc")).strip() if row.get("upc") else None,
        "additional_model_information": (
            str(row.get("additional_model_information")).strip()
            if row.get("additional_model_information")
            else None
        ),
        "features": _feature_text(row, config.feature_fields),
        "source_dataset": config.label,
        "source_url": source_url,
        "energy_star_certified": True,
        "last_synced_at": datetime.now(timezone.utc),
    }


def fetch_dataset(config: DatasetConfig, limit: int = 5000, offset: int = 0) -> list[dict[str, Any]]:
    url = f"{SOCRATA_BASE}/{config.dataset_id}.json"
    response = requests.get(url, params={"$limit": limit, "$offset": offset}, timeout=45)
    response.raise_for_status()
    return response.json()


def sync_category(db: Session, category: str, limit: int = 5000) -> dict[str, int | str]:
    config = DATASETS[category]
    rows = fetch_dataset(config, limit=limit)
    upserted = 0
    skipped = 0

    for row in rows:
        normalized = normalize_row(config, row)
        if not normalized:
            skipped += 1
            continue

        product = (
            db.query(models.CatalogProduct)
            .filter(models.CatalogProduct.source_key == normalized["source_key"])
            .first()
        )
        if product is None:
            product = models.CatalogProduct(**normalized)
            db.add(product)
        else:
            for key, value in normalized.items():
                setattr(product, key, value)
        upserted += 1

    db.commit()
    return {"category": category, "fetched": len(rows), "upserted": upserted, "skipped": skipped}
