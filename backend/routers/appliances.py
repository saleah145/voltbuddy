import base64
import json
import os
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

import models
from database import get_db
from schemas import ApplianceCreate, ApplianceUpdate
from services.appliance_estimates import CATEGORY_ESTIMATES, get_estimate
from services.appliance_search import normalize_query
from services.catalog_logic import derive_profile
from services.retail_products import search_product_sources
from services.energy_matching import enrich_retail_product

router = APIRouter()

BUILT_IN_APPLIANCE_IDS = {"ev_charger", "gaming_pc", "space_heater", "refrigerator"}


class RetailProductSearchRequest(BaseModel):
    q: str = Field(min_length=2, max_length=300)
    category: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=8, ge=1, le=12)


class RetailEnergyEstimateRequest(BaseModel):
    product: dict
    category: str | None = Field(default=None, max_length=80)


class CatalogAISearchRequest(BaseModel):
    q: str = Field(min_length=2, max_length=300)
    category: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=8, ge=1, le=20)


AI_CATEGORY_ALIASES = {
    "fridge": "refrigerator",
    "refrigerator": "refrigerator",
    "freezer": "freezer",
    "washer": "washer",
    "washing machine": "washer",
    "dryer": "dryer",
    "dishwasher": "dishwasher",
    "tv": "tv",
    "television": "tv",
    "computer": "computer",
    "pc": "computer",
    "desktop": "computer",
    "laptop": "computer",
    "notebook": "computer",
    "display": "display",
    "monitor": "display",
    "air purifier": "air purifier",
    "air cleaner": "air purifier",
    "dehumidifier": "dehumidifier",
    "air conditioner": "air conditioner",
    "room ac": "air conditioner",
    "ev charger": "ev charger",
}


def _clean_ai_value(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"null", "none", "unknown", "n/a"}:
        return None
    return cleaned


def _canonical_ai_category(value):
    cleaned = _clean_ai_value(value)
    if not cleaned:
        return None
    lowered = normalize_query(cleaned).strip().lower()
    return AI_CATEGORY_ALIASES.get(lowered, lowered)


def _catalog_text_or_filter(term):
    contains = f"%{term.lower()}%"
    return or_(
        func.lower(models.CatalogProduct.brand).like(contains),
        func.lower(models.CatalogProduct.model_number).like(contains),
        func.lower(models.CatalogProduct.model_name).like(contains),
        func.lower(models.CatalogProduct.product_type).like(contains),
        func.lower(models.CatalogProduct.additional_model_information).like(contains),
        func.lower(models.CatalogProduct.features).like(contains),
    )


def _ai_catalog_candidates(db, interpretation, category_override, limit):
    """
    Search the real catalog in stages so descriptive AI clues help without
    over-constraining the query into zero results.
    """
    category = _canonical_ai_category(category_override) or _canonical_ai_category(
        interpretation.get("category")
    )
    brand = _clean_ai_value(interpretation.get("brand"))
    model_number = _clean_ai_value(interpretation.get("model_number"))
    product_type = _clean_ai_value(interpretation.get("product_type"))
    capacity = interpretation.get("capacity")
    feature_terms = interpretation.get("feature_terms") or []

    def base_query():
        query = db.query(models.CatalogProduct)
        if category:
            query = query.filter(
                func.lower(models.CatalogProduct.category) == category.lower()
            )
        return query

    # Stage 1: strongest structured clues.
    query = base_query()
    if model_number:
        query = query.filter(
            func.lower(models.CatalogProduct.model_number).like(
                f"%{model_number.lower()}%"
            )
        )
    if brand:
        query = query.filter(
            func.lower(models.CatalogProduct.brand).like(f"%{brand.lower()}%")
        )
    if capacity is not None:
        try:
            capacity = float(capacity)
            tolerance = max(0.5, capacity * 0.03)
            query = query.filter(
                models.CatalogProduct.capacity.isnot(None),
                models.CatalogProduct.capacity.between(
                    capacity - tolerance,
                    capacity + tolerance,
                ),
            )
        except (TypeError, ValueError):
            capacity = None

    rows = (
        query.order_by(
            desc(models.CatalogProduct.annual_kwh.isnot(None)),
            models.CatalogProduct.brand,
            models.CatalogProduct.model_number,
        )
        .limit(limit)
        .all()
    )

    # Stage 2: category + brand + descriptive clues.
    if not rows:
        query = base_query()
        if brand:
            query = query.filter(
                func.lower(models.CatalogProduct.brand).like(f"%{brand.lower()}%")
            )

        descriptive = []
        if product_type:
            descriptive.append(product_type)
        descriptive.extend(
            str(term).strip()
            for term in feature_terms
            if str(term).strip()
        )

        if descriptive:
            query = query.filter(
                or_(*[_catalog_text_or_filter(term) for term in descriptive[:5]])
            )

        rows = (
            query.order_by(
                desc(models.CatalogProduct.annual_kwh.isnot(None)),
                models.CatalogProduct.brand,
                models.CatalogProduct.model_number,
            )
            .limit(limit)
            .all()
        )

    # Stage 3: safest broad fallback is category + brand, then category only.
    if not rows and brand:
        query = base_query().filter(
            func.lower(models.CatalogProduct.brand).like(f"%{brand.lower()}%")
        )
        rows = (
            query.order_by(
                desc(models.CatalogProduct.annual_kwh.isnot(None)),
                models.CatalogProduct.model_number,
            )
            .limit(limit)
            .all()
        )

    if not rows and category:
        rows = (
            base_query()
            .order_by(
                desc(models.CatalogProduct.annual_kwh.isnot(None)),
                models.CatalogProduct.brand,
                models.CatalogProduct.model_number,
            )
            .limit(limit)
            .all()
        )

    return rows, category


def serialize_appliance(appliance):
    return {
        "id": appliance.id,
        "name": appliance.name,
        "kw": appliance.kw,
        "interruptible": appliance.interruptible,
        "priority": appliance.priority,
        "category": appliance.category,
        "brand": appliance.brand,
        "model_number": appliance.model_number,
        "annual_kwh": appliance.annual_kwh,
        "typical_runtime_hours": appliance.typical_runtime_hours,
        "preferred_start_hour": appliance.preferred_start_hour,
        "earliest_start_hour": appliance.earliest_start_hour,
        "latest_finish_hour": appliance.latest_finish_hour,
        "schedule_flexibility": appliance.schedule_flexibility or "auto",
        "source": appliance.source,
        "is_catalog": bool(appliance.is_catalog),
        "is_estimate": bool(appliance.is_estimate),
        "catalog_product_id": appliance.catalog_product_id,
    }


def serialize_catalog(product):
    return {
        "id": product.id,
        "energy_star_id": product.energy_star_id,
        "category": product.category,
        "brand": product.brand,
        "model_name": product.model_name,
        "model_number": product.model_number,
        "product_type": product.product_type,
        "annual_kwh": product.annual_kwh,
        "rated_power_kw": product.rated_power_kw,
        "capacity": product.capacity,
        "capacity_unit": product.capacity_unit,
        "upc": product.upc,
        "additional_model_information": product.additional_model_information,
        "features": product.features,
        "source_dataset": product.source_dataset,
        "source_url": product.source_url,
        "image_url": product.image_url if product.image_verified else None,
        "product_url": product.product_url,
        "image_source": product.image_source,
        "image_verified": bool(product.image_verified),
        "image_match_type": product.image_match_type,
        "image_confidence": product.image_confidence,
        "energy_star_certified": bool(product.energy_star_certified),
    }


def make_id(name: str):
    slug = "".join(ch if ch.isalnum() else "_" for ch in name.lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_") or "appliance"
    return f"{slug}_{uuid4().hex[:6]}"


@router.get("/appliances")
def get_appliances(db: Session = Depends(get_db)):
    return [serialize_appliance(a) for a in db.query(models.Appliance).order_by(models.Appliance.name).all()]


@router.get("/catalog/filters")
def catalog_filters(db: Session = Depends(get_db)):
    categories = [row[0] for row in db.query(models.CatalogProduct.category).distinct().order_by(models.CatalogProduct.category).all()]
    brands = [row[0] for row in db.query(models.CatalogProduct.brand).filter(models.CatalogProduct.brand.isnot(None)).distinct().order_by(models.CatalogProduct.brand).limit(400).all()]
    return {
        "categories": categories,
        "brands": brands,
        "count": db.query(func.count(models.CatalogProduct.id)).scalar() or 0,
    }



CAPACITY_SEARCH_PATTERN = re.compile(
    r"(?P<capacity>\d{1,2}(?:\.\d+)?)\s*"
    r"(?:cu(?:bic)?\.?\s*(?:ft|feet|foot)|cubic\s*(?:ft|feet|foot))\b",
    re.IGNORECASE,
)

SEARCH_NOISE_TERMS = {
    "cu",
    "cubic",
    "ft",
    "feet",
    "foot",
}

CATEGORY_SEARCH_ALIASES = {
    "fridge": "refrigerator",
    "fridges": "refrigerator",
    "refrigerators": "refrigerator",
    "washing": "washer",
    "machine": "washer",
    "washers": "washer",
    "dryers": "dryer",
    "dishwashers": "dishwasher",
    "televisions": "tv",
}


def parse_human_catalog_query(value: str):
    """
    Split a consumer-style query into text terms + structured capacity.

    Examples:
      "Frigidaire 25.6-cu ft" -> terms=["frigidaire"], capacity=25.6
      "Samsung 25 cu ft refrigerator" -> terms=["samsung", "refrigerator"], capacity=25
      "LG bottom freezer 24 cubic feet" -> terms=["lg", "bottom", "freezer"], capacity=24
      "RF27CG5400" -> terms=["rf27cg5400"], capacity=None
    """
    normalized = normalize_query(value).strip() if value else ""
    if not normalized:
        return [], None

    capacity = None

    # normalize_query changes hyphens to spaces, which makes phrases such as
    # "25.6-cu ft" easy to recognize here.
    match = CAPACITY_SEARCH_PATTERN.search(normalized)
    if match:
        capacity = float(match.group("capacity"))
        normalized = (
            normalized[: match.start()] + " " + normalized[match.end() :]
        )

    raw_terms = [
        term.strip(".,()[]{}")
        for term in normalized.split()
        if term.strip(".,()[]{}")
    ]

    terms = []
    for term in raw_terms:
        lowered = term.lower()

        if lowered in SEARCH_NOISE_TERMS:
            continue

        canonical = CATEGORY_SEARCH_ALIASES.get(lowered, lowered)

        # Avoid accidental duplicate terms after synonym normalization.
        if len(canonical) > 1 and canonical not in terms:
            terms.append(canonical)

    return terms, capacity


@router.get("/catalog/search")
def search_catalog(
    q: str = Query(default="", max_length=120),
    category: str | None = Query(default=None, max_length=80),
    brand: str | None = Query(default=None, max_length=80),
    sort: str = Query(default="relevance"),
    limit: int = Query(default=24, ge=1, le=60),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.CatalogProduct)
    terms, requested_capacity = parse_human_catalog_query(q)

    if category:
        query = query.filter(func.lower(models.CatalogProduct.category) == category.strip().lower())
    if brand:
        query = query.filter(func.lower(models.CatalogProduct.brand) == brand.strip().lower())

    # Capacity is a numeric field, not searchable text. Treat common consumer
    # phrases such as "25.6 cu ft" as structured data instead of forcing
    # "25.6", "cu", and "ft" to match text columns.
    if requested_capacity is not None:
        capacity_tolerance = max(0.25, requested_capacity * 0.015)
        query = query.filter(
            models.CatalogProduct.capacity.isnot(None),
            models.CatalogProduct.capacity.between(
                requested_capacity - capacity_tolerance,
                requested_capacity + capacity_tolerance,
            ),
        )

    for term in terms:
        # Text terms can represent a brand, model/model family, appliance
        # category, or human-facing product type such as "bottom freezer".
        prefix = f"{term}%"
        contains = f"%{term}%"
        query = query.filter(or_(
            func.lower(models.CatalogProduct.brand).like(prefix),
            func.lower(models.CatalogProduct.model_number).like(prefix),
            func.lower(models.CatalogProduct.model_name).like(contains),
            func.lower(models.CatalogProduct.category).like(prefix),
            func.lower(models.CatalogProduct.product_type).like(contains),
            func.lower(models.CatalogProduct.additional_model_information).like(contains),
        ))

    if sort == "energy_low":
        query = query.order_by(asc(models.CatalogProduct.annual_kwh).nullslast(), models.CatalogProduct.brand, models.CatalogProduct.model_number)
    elif sort == "energy_high":
        query = query.order_by(desc(models.CatalogProduct.annual_kwh).nullslast(), models.CatalogProduct.brand, models.CatalogProduct.model_number)
    elif sort == "brand":
        query = query.order_by(models.CatalogProduct.brand, models.CatalogProduct.model_number)
    else:
        # Exact model-number and brand matches naturally bubble up, then models with real annual energy values.
        query = query.order_by(
            desc(models.CatalogProduct.annual_kwh.isnot(None)),
            models.CatalogProduct.brand,
            models.CatalogProduct.model_number,
        )

    # Fetch one extra row so the frontend can show that more matches exist
    # without forcing PostgreSQL to count the full result set first.
    rows = query.offset(offset).limit(limit + 1).all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return {
        "items": [serialize_catalog(item) for item in items],
        "total": None,
        "has_more": has_more,
        "offset": offset,
        "limit": limit,
    }


@router.post("/retail/search")
def search_retail_products(
    request: RetailProductSearchRequest,
    db: Session = Depends(get_db),
):
    """
    Live public product discovery:
    upc.dev first, UPCitemdb as a rate-conscious fallback.

    Product-source rows are not persisted in VoltBuddy.
    ENERGY STAR remains the energy authority.
    """
    try:
        products, source_notes = search_product_sources(
            request.q,
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not search external product sources: {exc}",
        )

    enriched = [
        enrich_retail_product(
            db,
            models,
            product,
            requested_category=request.category,
        )
        for product in products
    ]

    # Comparable ENERGY STAR data is retained as private context for the
    # AI estimate endpoint, but wider-search cards do not present that median
    # as the product's final estimate. The user selects a product first.
    for item in enriched:
        item.pop("energy_estimate", None)

    exact_count = sum(1 for item in enriched if item.get("energy"))

    return {
        "query": request.q,
        "products": enriched,
        "count": len(enriched),
        "exact_energy_matches": exact_count,
        "estimated_energy_matches": 0,
        "product_sources": source_notes,
        "energy_source": "ENERGY STAR catalog",
        "retail_content_persisted": False,
        "requires_external_api_key": False,
    }


@router.post("/retail/estimate-energy")
def estimate_selected_retail_product_energy(
    request: RetailEnergyEstimateRequest,
    db: Session = Depends(get_db),
):
    """
    Estimate annual kWh only AFTER the user selects a wider-search product.

    Priority:
    1. Exact ENERGY STAR match -> return verified annual kWh.
    2. Otherwise, ask the configured OpenAI model for an explicit estimate,
       grounded in the selected product identity plus ENERGY STAR comparable
       context when available.

    The AI result is always labeled as an estimate.
    """
    product = dict(request.product or {})
    if not product.get("name"):
        raise HTTPException(status_code=400, detail="Selected product is missing a name.")

    enriched = enrich_retail_product(
        db,
        models,
        product,
        requested_category=request.category,
    )
    category = enriched.get("voltbuddy_category") or request.category

    # If the selected external product resolves to an exact ENERGY STAR row,
    # do not ask AI to replace verified data.
    exact_energy = enriched.get("energy")
    if exact_energy and exact_energy.get("annual_kwh") is not None:
        catalog_product = None
        catalog_id = exact_energy.get("catalog_product_id")
        if catalog_id is not None:
            catalog_product = (
                db.query(models.CatalogProduct)
                .filter(models.CatalogProduct.id == catalog_id)
                .first()
            )

        if catalog_product:
            profile = derive_profile(catalog_product)
            kw = profile["kw"]
            runtime = profile["typical_runtime_hours"]
            interruptible = profile["interruptible"]
            priority = profile["priority"]
        else:
            _, generic = get_estimate(category or "")
            generic = generic or {}
            kw = float(generic.get("kw") or 0.5)
            runtime = float(generic.get("runtime") or 1.0)
            interruptible = bool(generic.get("interruptible", True))
            priority = str(generic.get("priority") or "medium")

        return {
            "status": "verified",
            "annual_kwh": float(exact_energy["annual_kwh"]),
            "confidence": "verified",
            "basis": (
                "VoltBuddy matched this selected product to an exact ENERGY STAR "
                "record by UPC or model number."
            ),
            "energy_source": "ENERGY STAR",
            "match_type": exact_energy.get("match_type"),
            "reference_context": None,
            "appliance_profile": {
                "name": str(product.get("name") or "Selected appliance")[:80],
                "kw": kw,
                "interruptible": interruptible,
                "priority": priority,
                "category": category,
                "brand": product.get("brand"),
                "model_number": product.get("model_number"),
                "annual_kwh": float(exact_energy["annual_kwh"]),
                "typical_runtime_hours": runtime,
                "source": (
                    f"{product.get('retail_source') or 'UPC product database'} product identity "
                    "· ENERGY STAR verified energy"
                ),
                "is_estimate": False,
            },
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI energy estimation is not configured. "
                "Set OPENAI_API_KEY on the backend."
            ),
        )

    # Re-run enrichment specifically to collect comparable ENERGY STAR context.
    # energy_matching.py computes a deterministic comparable summary; here it is
    # evidence for the model, not the final number shown to the user.
    comparison = enriched.get("energy_estimate")
    normalized_category, generic = get_estimate(category or "")
    category = normalized_category or category

    reference = {
        "category": category,
        "generic_category_kwh": generic.get("annual_kwh") if generic else None,
        "comparable_count": comparison.get("comparable_count") if comparison else 0,
        "comparable_median_kwh": comparison.get("annual_kwh") if comparison else None,
        "comparable_range_low_kwh": comparison.get("range_low_kwh") if comparison else None,
        "comparable_range_high_kwh": comparison.get("range_high_kwh") if comparison else None,
        "comparables": (comparison.get("comparables") or [])[:6] if comparison else [],
    }

    product_evidence = {
        "name": product.get("name"),
        "brand": product.get("brand"),
        "model_number": product.get("model_number"),
        "upc": product.get("upc"),
        "category": category,
        "category_path": product.get("category_path") or [],
        "short_description": product.get("short_description"),
        "retail_source": product.get("retail_source"),
    }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv(
            "OPENAI_ENERGY_MODEL",
            os.getenv("OPENAI_TEXT_MODEL", "gpt-5"),
        )

        prompt = (
            "Estimate the selected household product's likely annual electricity "
            "use in kWh/year. This is explicitly an ESTIMATE, not a verified "
            "manufacturer specification. Use the selected product identity and the "
            "ENERGY STAR comparison evidence below. If comparable certified models "
            "are provided, use them as the strongest numeric anchor. If they are not "
            "provided, use the generic category benchmark as a loose anchor and lower "
            "your confidence. Do not claim the product is ENERGY STAR certified unless "
            "the evidence says so. Return ONLY valid JSON with exactly these keys: "
            "annual_kwh, confidence, basis. annual_kwh must be one positive number. "
            "confidence must be high, medium, or low. basis must be one short sentence "
            "explaining what evidence drove the estimate.\n\n"
            f"SELECTED PRODUCT:\n{json.dumps(product_evidence, ensure_ascii=False)}\n\n"
            f"ENERGY REFERENCE CONTEXT:\n{json.dumps(reference, ensure_ascii=False)}"
        )

        response = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }],
        )

        raw_text = response.output_text.strip()
        match = re.search(r"\{.*\}", raw_text, re.S)
        result = json.loads(match.group(0) if match else raw_text)

        annual_kwh = float(result.get("annual_kwh"))
        if not (0 < annual_kwh <= 50000):
            raise ValueError("AI estimate was outside the accepted kWh range.")

        confidence = str(result.get("confidence") or "low").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"

        basis = str(result.get("basis") or "").strip()
        if not basis:
            basis = "Estimated from the selected product identity and available energy references."

    except Exception as exc:
        message = str(exc)
        if "insufficient_quota" in message or "429" in message:
            raise HTTPException(
                status_code=503,
                detail="AI energy estimation is temporarily unavailable.",
            )
        raise HTTPException(
            status_code=502,
            detail=f"Could not estimate annual energy with AI: {exc}",
        )

    # The optimizer still needs an operating power/runtime profile. Keep these
    # separate from the AI annual-kWh estimate and use VoltBuddy's category
    # defaults when an exact product power spec is unavailable.
    generic = generic or {}
    kw = float(generic.get("kw") or 0.5)
    runtime = float(generic.get("runtime") or 1.0)
    interruptible = bool(generic.get("interruptible", True))
    priority = str(generic.get("priority") or "medium")

    return {
        "status": "ai_estimated",
        "annual_kwh": round(annual_kwh, 1),
        "confidence": confidence,
        "basis": basis,
        "energy_source": "OpenAI estimate grounded in VoltBuddy energy references",
        "match_type": None,
        "reference_context": reference,
        "appliance_profile": {
            "name": str(product.get("name") or "Selected appliance")[:80],
            "kw": kw,
            "interruptible": interruptible,
            "priority": priority,
            "category": category,
            "brand": product.get("brand"),
            "model_number": product.get("model_number"),
            "annual_kwh": round(annual_kwh, 1),
            "typical_runtime_hours": runtime,
            "source": (
                f"{product.get('retail_source') or 'UPC product database'} product identity "
                "· AI-estimated annual energy"
            ),
            "is_estimate": True,
        },
    }


@router.post("/catalog/ai-search")
def ai_search_catalog(
    request: CatalogAISearchRequest,
    db: Session = Depends(get_db),
):
    """
    AI is a query interpreter only. It never supplies product energy specs.
    Every returned product must already exist in catalog_products.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI search is not configured. Set OPENAI_API_KEY on the backend.",
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_SEARCH_MODEL", os.getenv("OPENAI_TEXT_MODEL", "gpt-5"))

        response = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": (
                        "You translate a casual household-appliance search into structured "
                        "catalog clues. Return ONLY valid JSON with exactly these keys: "
                        "category, brand, model_number, product_type, capacity, capacity_unit, "
                        "feature_terms, clean_query, interpretation. "
                        "category must be one of: refrigerator, freezer, washer, dryer, "
                        "dishwasher, tv, computer, display, air purifier, dehumidifier, "
                        "air conditioner, ev charger, or null. "
                        "feature_terms must be an array of short strings. capacity must be a "
                        "number or null. Never invent a model number, brand, wattage, kWh, "
                        "energy use, price, or certification. Use null when the user did not "
                        "provide enough evidence. The interpretation should be one short "
                        "plain-English sentence explaining what you think they mean.\n\n"
                        f"User search: {request.q}"
                    ),
                }],
            }],
        )

        raw_text = response.output_text.strip()
        match = re.search(r"\{.*\}", raw_text, re.S)
        interpretation = json.loads(match.group(0) if match else raw_text)

        if not isinstance(interpretation, dict):
            raise ValueError("AI search did not return an object.")

    except Exception as exc:
        message = str(exc)
        if "insufficient_quota" in message or "429" in message:
            raise HTTPException(
                status_code=503,
                detail="AI search is temporarily unavailable. Normal catalog search still works.",
            )
        raise HTTPException(
            status_code=502,
            detail=f"Could not interpret that search with AI: {exc}",
        )

    # Normalize the fields we expose back to the frontend.
    normalized = {
        "category": _canonical_ai_category(interpretation.get("category")),
        "brand": _clean_ai_value(interpretation.get("brand")),
        "model_number": _clean_ai_value(interpretation.get("model_number")),
        "product_type": _clean_ai_value(interpretation.get("product_type")),
        "capacity": interpretation.get("capacity"),
        "capacity_unit": _clean_ai_value(interpretation.get("capacity_unit")),
        "feature_terms": [
            str(term).strip()
            for term in (interpretation.get("feature_terms") or [])
            if str(term).strip()
        ][:6],
        "clean_query": _clean_ai_value(interpretation.get("clean_query")) or request.q,
        "interpretation": _clean_ai_value(interpretation.get("interpretation"))
        or "VoltBuddy interpreted your description and searched the catalog.",
    }

    rows, resolved_category = _ai_catalog_candidates(
        db,
        normalized,
        request.category,
        request.limit,
    )
    normalized["category"] = resolved_category

    return {
        "query": request.q,
        "interpretation": normalized,
        "items": [serialize_catalog(item) for item in rows],
        "count": len(rows),
        "source": "ai_query_interpretation_plus_catalog",
        "energy_data_source": "catalog_only",
    }


@router.post("/catalog/{catalog_product_id}/add")
def add_catalog_product(catalog_product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.CatalogProduct).filter(models.CatalogProduct.id == catalog_product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Catalog product not found.")

    existing = db.query(models.Appliance).filter(models.Appliance.catalog_product_id == catalog_product_id).first()
    if existing:
        return serialize_appliance(existing)

    profile = derive_profile(product)
    appliance = models.Appliance(
        id=make_id(profile["name"]),
        name=profile["name"],
        kw=profile["kw"],
        interruptible=profile["interruptible"],
        priority=profile["priority"],
        category=product.category,
        brand=product.brand,
        model_number=product.model_number,
        annual_kwh=product.annual_kwh,
        typical_runtime_hours=profile["typical_runtime_hours"],
        source=f"{product.source_dataset} · ENERGY STAR",
        is_catalog=True,
        is_estimate=False,
        catalog_product_id=product.id,
    )
    db.add(appliance)
    db.commit()
    db.refresh(appliance)
    return serialize_appliance(appliance)


@router.get("/appliances/estimate")
def estimate_appliance(category: str = Query(min_length=1, max_length=80)):
    normalized, estimate = get_estimate(category)
    if not estimate:
        raise HTTPException(status_code=404, detail={"message": "No estimate is available for that category.", "available_categories": sorted(CATEGORY_ESTIMATES)})
    return {
        "category": normalized,
        "name": estimate["name"],
        "kw": estimate["kw"],
        "annual_kwh": estimate["annual_kwh"],
        "typical_runtime_hours": estimate["runtime"],
        "interruptible": estimate["interruptible"],
        "priority": estimate["priority"],
        "source": "VoltBuddy generic category estimate",
        "is_estimate": True,
    }


@router.post("/appliances/identify-image")
async def identify_appliance_image(image: UploadFile = File(...), db: Session = Depends(get_db)):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, or WebP image.")
    raw = await image.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Photo identification is not configured. Set OPENAI_API_KEY on the backend.")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        encoded = base64.b64encode(raw).decode("utf-8")
        data_url = f"data:{image.content_type};base64,{encoded}"
        model = os.getenv("OPENAI_VISION_MODEL", "gpt-5")
        response = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": (
                        "Identify this household appliance for catalog search. Return ONLY JSON with keys: category, brand, model_number, description, confidence. "
                        "Use null when brand or model number is not visible. confidence must be high, medium, or low. "
                        "Do not invent wattage, kWh, energy use, or model numbers. Prefer text visible on the model/serial label. "
                        "Normalize category toward refrigerator, washer, dryer, dishwasher, tv, air conditioner, or ev charger when appropriate."
                    )},
                    {"type": "input_image", "image_url": data_url, "detail": "high"},
                ],
            }],
        )
        text = response.output_text.strip()
        match = re.search(r"\{.*\}", text, re.S)
        result = json.loads(match.group(0) if match else text)
    except Exception as exc:
        message = str(exc)
        if "insufficient_quota" in message or "429" in message:
            raise HTTPException(status_code=503, detail="Photo identification is temporarily unavailable. You can still search the catalog or use an estimated profile.")
        raise HTTPException(status_code=502, detail=f"Could not analyze the image: {exc}")

    category, _ = get_estimate(result.get("category") or "")
    category = category or (result.get("category") or "").strip().lower()
    query_parts = [result.get("brand"), result.get("model_number")]
    search_text = " ".join(part for part in query_parts if part).strip()

    catalog_query = db.query(models.CatalogProduct)
    if category:
        catalog_query = catalog_query.filter(func.lower(models.CatalogProduct.category) == category.lower())
    if result.get("model_number"):
        model_like = f"%{result['model_number'].strip().lower()}%"
        catalog_query = catalog_query.filter(func.lower(models.CatalogProduct.model_number).like(model_like))
    elif result.get("brand"):
        brand_like = f"%{result['brand'].strip().lower()}%"
        catalog_query = catalog_query.filter(func.lower(models.CatalogProduct.brand).like(brand_like))

    matches = catalog_query.order_by(desc(models.CatalogProduct.annual_kwh.isnot(None))).limit(8).all()

    normalized_category, estimate = get_estimate(category)
    return {
        "identification": {
            "category": normalized_category or category,
            "brand": result.get("brand"),
            "model_number": result.get("model_number"),
            "description": result.get("description"),
            "confidence": result.get("confidence", "low"),
            "search_text": search_text,
        },
        "matches": [serialize_catalog(product) for product in matches],
        "estimate": None if not estimate else {
            "category": normalized_category,
            "name": estimate["name"], "kw": estimate["kw"], "annual_kwh": estimate["annual_kwh"],
            "typical_runtime_hours": estimate["runtime"], "interruptible": estimate["interruptible"],
            "priority": estimate["priority"], "source": "VoltBuddy generic category estimate", "is_estimate": True,
        },
    }


@router.post("/appliances")
def create_appliance(appliance: ApplianceCreate, db: Session = Depends(get_db)):
    new_appliance = models.Appliance(
        id=make_id(appliance.name),
        name=appliance.name,
        kw=appliance.kw,
        interruptible=appliance.interruptible,
        priority=appliance.priority,
        category=appliance.category,
        brand=appliance.brand,
        model_number=appliance.model_number,
        annual_kwh=appliance.annual_kwh,
        typical_runtime_hours=appliance.typical_runtime_hours,
        preferred_start_hour=appliance.preferred_start_hour,
        earliest_start_hour=appliance.earliest_start_hour,
        latest_finish_hour=appliance.latest_finish_hour,
        schedule_flexibility=appliance.schedule_flexibility or "auto",
        source=appliance.source or "User entered",
        is_catalog=False,
        is_estimate=appliance.is_estimate,
    )
    db.add(new_appliance)
    db.commit()
    db.refresh(new_appliance)
    return serialize_appliance(new_appliance)


@router.patch("/appliances/{appliance_id}")
def update_appliance(appliance_id: str, update: ApplianceUpdate, db: Session = Depends(get_db)):
    appliance = db.query(models.Appliance).filter(models.Appliance.id == appliance_id).first()
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found.")
    if appliance_id in BUILT_IN_APPLIANCE_IDS or appliance.is_catalog:
        raise HTTPException(status_code=400, detail="Catalog and built-in appliances are read-only.")
    for field, value in update.model_dump().items():
        setattr(appliance, field, value)
    db.commit()
    db.refresh(appliance)
    return serialize_appliance(appliance)


@router.delete("/appliances/{appliance_id}")
def delete_appliance(appliance_id: str, db: Session = Depends(get_db)):
    appliance = db.query(models.Appliance).filter(models.Appliance.id == appliance_id).first()
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found.")
    if appliance_id in BUILT_IN_APPLIANCE_IDS:
        raise HTTPException(status_code=400, detail="Built-in appliances cannot be deleted.")
    db.query(models.HomeAppliance).filter(models.HomeAppliance.appliance_id == appliance_id).delete(synchronize_session=False)
    db.delete(appliance)
    db.commit()
    return {"deleted": True, "appliance_id": appliance_id}
