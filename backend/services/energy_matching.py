import math
import re
from statistics import median

from sqlalchemy import desc, func, or_


CATEGORY_HINTS = {
    "refrigerator": ("refrigerator", "fridge"),
    "freezer": ("freezer",),
    "washer": ("washer", "washing machine"),
    "dryer": ("dryer",),
    "dishwasher": ("dishwasher",),
    "tv": ("television", "tv"),
    "computer": ("computer", "desktop", "laptop", "notebook", "workstation"),
    "display": ("monitor", "display"),
    "air purifier": ("air purifier", "air cleaner"),
    "dehumidifier": ("dehumidifier",),
    "air conditioner": ("air conditioner", "room ac", "window ac"),
    "ev charger": ("ev charger", "vehicle charger", "level 2 charger"),
}


def normalize_identifier(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def normalize_upc(value):
    return re.sub(r"\D", "", str(value or ""))


def split_catalog_upcs(value):
    if not value:
        return []
    return {
        normalize_upc(piece)
        for piece in re.split(r"[,;|/\s]+", str(value))
        if normalize_upc(piece)
    }


def infer_voltbuddy_category(product, requested_category=None):
    if requested_category:
        return requested_category.strip().lower()

    haystack = " ".join([
        str(product.get("name") or ""),
        str(product.get("short_description") or ""),
        " ".join(product.get("category_path") or []),
    ]).lower()

    # Order specific categories before generic computer/display language.
    for category, hints in CATEGORY_HINTS.items():
        if any(hint in haystack for hint in hints):
            return category
    return None


def _exact_upc_match(db, models, category, retail_upc):
    upc = normalize_upc(retail_upc)
    if not upc:
        return None

    query = db.query(models.CatalogProduct).filter(
        models.CatalogProduct.upc.isnot(None)
    )
    if category:
        query = query.filter(
            func.lower(models.CatalogProduct.category) == category.lower()
        )

    # Narrow in SQL first, then verify exact token matching in Python because
    # ENERGY STAR rows may contain more than one UPC in a text field.
    candidates = query.filter(
        models.CatalogProduct.upc.like(f"%{upc}%")
    ).limit(25).all()

    for candidate in candidates:
        if upc in split_catalog_upcs(candidate.upc):
            return candidate
    return None


def _exact_model_match(db, models, category, brand, model_number):
    model_norm = normalize_identifier(model_number)
    if not model_norm:
        return None

    query = db.query(models.CatalogProduct)
    if category:
        query = query.filter(
            func.lower(models.CatalogProduct.category) == category.lower()
        )

    # SQL contains narrows candidates; Python normalization confirms exactness.
    candidates = query.filter(
        func.lower(models.CatalogProduct.model_number).like(
            f"%{str(model_number).lower()}%"
        )
    ).limit(40).all()

    brand_norm = normalize_identifier(brand)
    for candidate in candidates:
        if normalize_identifier(candidate.model_number) != model_norm:
            continue

        if brand_norm:
            catalog_brand = normalize_identifier(candidate.brand)
            # ENERGY STAR can list multiple brand aliases; manufacturer only
            # needs to appear inside that source string.
            if brand_norm not in catalog_brand and catalog_brand not in brand_norm:
                continue

        return candidate
    return None


def _similarity_candidates(db, models, category, product, limit=12):
    if not category:
        return []

    query = db.query(models.CatalogProduct).filter(
        func.lower(models.CatalogProduct.category) == category.lower(),
        models.CatalogProduct.annual_kwh.isnot(None),
        models.CatalogProduct.annual_kwh > 0,
    )

    brand = str(product.get("brand") or "").strip()
    if brand:
        brand_rows = query.filter(
            func.lower(models.CatalogProduct.brand).like(f"%{brand.lower()}%")
        ).limit(limit).all()
        if len(brand_rows) >= 3:
            return brand_rows

    # Use product-type/title clues when brand comparables are sparse.
    words = re.findall(
        r"[a-z0-9]+",
        " ".join([
            str(product.get("name") or ""),
            str(product.get("short_description") or ""),
        ]).lower(),
    )
    useful = [
        word for word in words
        if len(word) >= 4 and word not in {
            "with", "from", "inch", "inches", "best", "buy", "energy",
            "smart", "black", "white", "stainless",
        }
    ][:6]

    if useful:
        conditions = []
        for word in useful:
            contains = f"%{word}%"
            conditions.extend([
                func.lower(models.CatalogProduct.product_type).like(contains),
                func.lower(models.CatalogProduct.model_name).like(contains),
                func.lower(models.CatalogProduct.additional_model_information).like(contains),
            ])
        typed = query.filter(or_(*conditions)).limit(limit).all()
        if len(typed) >= 3:
            return typed

    return (
        query.order_by(
            desc(models.CatalogProduct.energy_star_certified),
            models.CatalogProduct.brand,
        )
        .limit(limit)
        .all()
    )


def _serialize_energy_match(product, match_type, confidence):
    return {
        "catalog_product_id": product.id,
        "energy_star_id": product.energy_star_id,
        "category": product.category,
        "brand": product.brand,
        "model_number": product.model_number,
        "annual_kwh": product.annual_kwh,
        "capacity": product.capacity,
        "capacity_unit": product.capacity_unit,
        "source_dataset": product.source_dataset,
        "source_url": product.source_url,
        "energy_star_certified": bool(product.energy_star_certified),
        "match_type": match_type,
        "confidence": confidence,
    }


def enrich_retail_product(db, models, retail_product, requested_category=None):
    category = infer_voltbuddy_category(
        retail_product,
        requested_category=requested_category,
    )

    exact = _exact_upc_match(
        db, models, category, retail_product.get("upc")
    )
    if exact:
        return {
            **retail_product,
            "voltbuddy_category": category or exact.category,
            "energy": _serialize_energy_match(
                exact, "upc_exact", "high"
            ),
            "energy_estimate": None,
        }

    exact = _exact_model_match(
        db,
        models,
        category,
        retail_product.get("brand"),
        retail_product.get("model_number"),
    )
    if exact:
        return {
            **retail_product,
            "voltbuddy_category": category or exact.category,
            "energy": _serialize_energy_match(
                exact, "brand_model_exact", "high"
            ),
            "energy_estimate": None,
        }

    comparable = _similarity_candidates(
        db, models, category, retail_product
    )
    usable = [
        row for row in comparable
        if row.annual_kwh is not None
        and math.isfinite(float(row.annual_kwh))
        and float(row.annual_kwh) > 0
    ]

    if usable:
        values = [float(row.annual_kwh) for row in usable]
        estimate = float(median(values))

        # Confidence is based on evidence count and whether same-brand
        # comparables exist. The number remains deterministic.
        retail_brand = normalize_identifier(retail_product.get("brand"))
        same_brand = sum(
            1 for row in usable
            if retail_brand
            and retail_brand in normalize_identifier(row.brand)
        )
        if len(usable) >= 5 and same_brand >= 3:
            confidence = "medium"
        elif len(usable) >= 5:
            confidence = "low-medium"
        else:
            confidence = "low"

        return {
            **retail_product,
            "voltbuddy_category": category,
            "energy": None,
            "energy_estimate": {
                "annual_kwh": round(estimate, 1),
                "confidence": confidence,
                "comparable_count": len(usable),
                "same_brand_comparable_count": same_brand,
                "method": "median_of_comparable_energy_star_products",
                "range_low_kwh": round(min(values), 1),
                "range_high_kwh": round(max(values), 1),
                "comparables": [
                    {
                        "catalog_product_id": row.id,
                        "brand": row.brand,
                        "model_number": row.model_number,
                        "annual_kwh": row.annual_kwh,
                        "product_type": row.product_type,
                        "capacity": row.capacity,
                        "capacity_unit": row.capacity_unit,
                    }
                    for row in usable[:6]
                ],
            },
        }

    return {
        **retail_product,
        "voltbuddy_category": category,
        "energy": None,
        "energy_estimate": None,
    }
