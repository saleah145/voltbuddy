import re

import requests


UPC_DEV_SEARCH = "https://upc.dev/v1/search"
UPCITEMDB_SEARCH = "https://api.upcitemdb.com/prod/trial/search"


def _clean_query(query: str):
    return re.sub(r"\s+", " ", (query or "").strip())


def _normalize_upc(value):
    return re.sub(r"\D", "", str(value or ""))


def _extract_model_from_name(name, brand=None):
    """
    Product databases do not always expose a separate model field.
    This conservative helper only returns obvious model-like tokens.
    """
    text = str(name or "")
    brand_text = str(brand or "").strip()
    if brand_text:
        text = re.sub(re.escape(brand_text), " ", text, flags=re.I)

    candidates = re.findall(
        r"\b(?=[A-Z0-9-]{5,}\b)(?=[A-Z0-9-]*[A-Z])(?=[A-Z0-9-]*\d)[A-Z0-9-]+\b",
        text.upper(),
    )
    return candidates[0] if candidates else None


def _serialize_upc_dev(item):
    upc = item.get("upc") or item.get("gtin")
    brand = item.get("brand")
    name = item.get("name")

    return {
        "retail_source": "upc.dev",
        "sku": upc,
        "gtin": item.get("gtin"),
        "name": name,
        "brand": brand,
        "model_number": item.get("model_number") or _extract_model_from_name(name, brand),
        "upc": upc,
        "image_url": item.get("image") or item.get("image_url"),
        "product_url": (
            f"https://upc.dev/product/{upc}"
            if upc
            else None
        ),
        "short_description": item.get("description"),
        "category_path": [item.get("category")] if item.get("category") else [],
        "source_score": item.get("score"),
    }


def _serialize_upcitemdb(item):
    upc = item.get("upc") or item.get("ean")
    brand = item.get("brand")
    name = item.get("title") or item.get("name")
    images = item.get("images") or []

    return {
        "retail_source": "UPCitemdb",
        "sku": upc,
        "gtin": item.get("ean") or upc,
        "name": name,
        "brand": brand,
        "model_number": item.get("model") or _extract_model_from_name(name, brand),
        "upc": upc,
        "image_url": images[0] if images else None,
        "product_url": None,
        "short_description": item.get("description"),
        "category_path": [item.get("category")] if item.get("category") else [],
        "source_score": None,
    }


def search_upc_dev(query: str, limit: int = 8):
    response = requests.get(
        UPC_DEV_SEARCH,
        params={"q": _clean_query(query)},
        headers={"Accept": "application/json"},
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()

    # upc.dev has returned both legacy {results:[...]} and documented
    # {ok:true,data:{products:[...]}} response shapes, so support both.
    rows = payload.get("results")
    if rows is None:
        rows = (payload.get("data") or {}).get("products") or []

    return [_serialize_upc_dev(item) for item in rows[:limit]]


def search_upcitemdb(query: str, limit: int = 8):
    response = requests.get(
        UPCITEMDB_SEARCH,
        params={"s": _clean_query(query), "type": "json"},
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("items") or []
    return [_serialize_upcitemdb(item) for item in rows[:limit]]


def _product_key(item):
    upc = _normalize_upc(item.get("upc") or item.get("gtin"))
    if upc:
        return f"upc:{upc}"

    brand = re.sub(r"[^a-z0-9]", "", str(item.get("brand") or "").lower())
    model = re.sub(r"[^a-z0-9]", "", str(item.get("model_number") or "").lower())
    if brand and model:
        return f"model:{brand}:{model}"

    name = re.sub(r"[^a-z0-9]", "", str(item.get("name") or "").lower())
    return f"name:{name}"


def search_product_sources(query: str, limit: int = 8):
    """
    No API key required.

    1. Search upc.dev public endpoint.
    2. Search UPCitemdb only if the first source is sparse.
    3. Merge/deduplicate by UPC, then brand+model, then name.
    """
    query = _clean_query(query)
    if len(query) < 2:
        return [], []

    source_notes = []
    merged = []
    seen = set()

    try:
        primary = search_upc_dev(query, limit=limit)
        source_notes.append({
            "source": "upc.dev",
            "ok": True,
            "count": len(primary),
        })
    except Exception as exc:
        primary = []
        source_notes.append({
            "source": "upc.dev",
            "ok": False,
            "count": 0,
            "error": str(exc),
        })

    for item in primary:
        key = _product_key(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)

    # UPCitemdb's free plan has much tighter search limits, so only consume a
    # fallback search when upc.dev did not already provide enough candidates.
    if len(merged) < min(5, limit):
        try:
            fallback = search_upcitemdb(query, limit=limit)
            source_notes.append({
                "source": "UPCitemdb",
                "ok": True,
                "count": len(fallback),
            })
        except Exception as exc:
            fallback = []
            source_notes.append({
                "source": "UPCitemdb",
                "ok": False,
                "count": 0,
                "error": str(exc),
            })

        for item in fallback:
            key = _product_key(item)
            if key not in seen:
                seen.add(key)
                merged.append(item)
                if len(merged) >= limit:
                    break
    else:
        source_notes.append({
            "source": "UPCitemdb",
            "ok": True,
            "count": 0,
            "skipped": "upc.dev already returned enough candidates",
        })

    return merged[:limit], source_notes
