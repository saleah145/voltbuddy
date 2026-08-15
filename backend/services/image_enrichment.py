from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


BRAVE_IMAGE_SEARCH_URL = "https://api.search.brave.com/res/v1/images/search"


# Conservative manufacturer-domain hints.
# The code can still inspect other results, but automatic verification requires
# a trusted manufacturer-domain match when a brand mapping is available.
BRAND_DOMAINS = {
    "samsung": ("samsung.com",),
    "lg": ("lg.com",),
    "ge": ("geappliances.com",),
    "ge appliances": ("geappliances.com",),
    "whirlpool": ("whirlpool.com",),
    "maytag": ("maytag.com",),
    "kitchenaid": ("kitchenaid.com",),
    "bosch": ("bosch-home.com",),
    "frigidaire": ("frigidaire.com", "curtisint.com"),
    "electrolux": ("electrolux.com",),
    "miele": ("mieleusa.com", "miele.com"),
    "haier": ("haierappliances.com", "haier.com"),
    "hisense": ("hisense-usa.com", "hisense.com"),
    "sony": ("sony.com",),
    "tcl": ("tcl.com",),
    "vizio": ("vizio.com",),
    "panasonic": ("panasonic.com",),
    "sharp": ("sharpusa.com", "sharpconsumer.com"),
}

TRUSTED_RETAILER_DOMAINS = (
    "lowes.com",
    "homedepot.com",
    "bestbuy.com",
    "ajmadison.com",
    "abt.com",
    "costco.com",
)




@dataclass
class Candidate:
    image_url: str
    page_url: str | None
    source_domain: str | None
    title: str | None
    provider_confidence: str | None
    score: float
    match_type: str
    page_match_type: str
    matched_alias: str | None
    page_matched_alias: str | None
    reasons: list[str]


def normalize_identifier(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def model_family_base(model_number: str | None) -> str:
    raw = (model_number or "").strip()
    # ENERGY STAR uses * and sometimes # as model-family wildcards.
    raw = re.split(r"[*#]", raw, maxsplit=1)[0]
    return normalize_identifier(raw)


def hostname(url: str | None) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def domain_matches(host: str, allowed: tuple[str, ...]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def trusted_domains_for_brand(brand: str | None) -> tuple[str, ...]:
    key = (brand or "").strip().lower()
    return BRAND_DOMAINS.get(key, ())



def split_aliases(value: str | None) -> list[str]:
    if not value:
        return []

    raw_parts = re.split(r"[;,\n|]+", value)

    aliases = []
    seen = set()

    GENERIC_WORDS = {
        "refrigerator",
        "fridge",
        "freezer",
        "washer",
        "dryer",
        "dishwasher",
        "television",
        "tv",
        "appliance",
        "compact refrigerator",
        "room air conditioner",
        "air conditioner",
    }

    for raw in raw_parts:
        candidate = raw.strip()
        if not candidate:
            continue

        candidate = re.sub(
            r"^(?:model(?:\s*number)?|sku|retail(?:\s*model)?|alternate(?:\s*model)?)\s*[:#-]\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip()

        lowered = candidate.lower()
        if lowered in GENERIC_WORDS:
            continue

        normalized = normalize_identifier(candidate)

        # Real model/SKU aliases should look like identifiers, not prose.
        # Require:
        # - at least 5 normalized chars
        # - at least one letter
        # - at least one digit
        # This rejects generic text such as "Refrigerator".
        if (
            len(normalized) < 5
            or not re.search(r"[a-z]", normalized)
            or not re.search(r"\d", normalized)
        ):
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        aliases.append(candidate)

    return aliases


def product_model_aliases(product) -> list[str]:
    """
    Return every useful identity string VoltBuddy knows for the catalog row:
    - primary ENERGY STAR model_number
    - wildcard-free family base
    - additional_model_information aliases
    - legacy 'features' field aliases from earlier catalog syncs
    """
    values = []

    primary = (product.model_number or "").strip()
    if primary:
        values.append(primary)

        family_base = re.split(r"[*#]", primary, maxsplit=1)[0].strip()
        if family_base and family_base != primary:
            values.append(family_base)

    values.extend(split_aliases(product.additional_model_information))

    # In the current VoltBuddy catalog, many ENERGY STAR family members ended
    # up in `features` from the original dataset normalization. Preserve them
    # as aliases rather than throwing away useful model identity evidence.
    values.extend(split_aliases(product.features))

    unique = []
    seen = set()

    for value in values:
        normalized = normalize_identifier(value)
        if len(normalized) < 4 or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(value)

    return unique


def match_aliases_in_text(product, searchable: str) -> tuple[str | None, str | None]:
    """
    Return (match_type, matched_alias).

    exact: full non-wildcard primary or alias appears
    family: wildcard-family base appears
    alias: alternate ENERGY STAR family/SKU appears
    """
    searchable_norm = normalize_identifier(searchable)

    primary = (product.model_number or "").strip()
    primary_norm = normalize_identifier(primary)

    if (
        primary_norm
        and "*" not in primary
        and "#" not in primary
        and primary_norm in searchable_norm
    ):
        return "exact", primary

    family_base = re.split(r"[*#]", primary, maxsplit=1)[0].strip()
    family_norm = normalize_identifier(family_base)

    if family_norm and len(family_norm) >= 6 and family_norm in searchable_norm:
        return "family", family_base

    for alias in product_model_aliases(product):
        alias_norm = normalize_identifier(alias)

        if not alias_norm or len(alias_norm) < 7:
            continue

        # Ignore the primary values already evaluated above.
        if alias_norm in {primary_norm, family_norm}:
            continue

        if alias_norm in searchable_norm:
            return "alias", alias

    return None, None


def build_query(product, manufacturer_only: bool = True) -> str:
    brand = (product.brand or "").strip()
    model = (product.model_number or "").strip()
    family = re.split(r"[*#]", model, maxsplit=1)[0].strip()
    upc = (product.upc or "").strip()

    trusted_domains = trusted_domains_for_brand(brand)

    preferred_domain = trusted_domains[0] if trusted_domains else ""
    normalized_model = (model or "").upper()

    # Many Frigidaire EFR/RFR compact appliances are licensed/cataloged by
    # Curtis International. Prefer that authoritative catalog for those SKUs.
    if (
        brand.strip().lower() == "frigidaire"
        and normalized_model.startswith(("EFR", "RFR"))
        and "curtisint.com" in trusted_domains
    ):
        preferred_domain = "curtisint.com"

    site_filter = (
        f"site:{preferred_domain}"
        if manufacturer_only and preferred_domain
        else ""
    )

    parts = [site_filter, brand, family or model]

    aliases = product_model_aliases(product)
    alternate_alias = next(
        (
            alias
            for alias in aliases
            if normalize_identifier(alias)
            not in {
                normalize_identifier(model),
                normalize_identifier(family),
            }
        ),
        None,
    )

    if alternate_alias:
        parts.append(alternate_alias)

    if upc:
        parts.append(upc)

    parts.append(product.category or "appliance")

    return " ".join(part for part in parts if part)


def brave_image_search(query: str, count: int = 20) -> list[dict[str, Any]]:
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        raise RuntimeError(
            "BRAVE_SEARCH_API_KEY is not set. "
            "Create a Brave Search API key and export it before running enrichment."
        )

    response = requests.get(
        BRAVE_IMAGE_SEARCH_URL,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        },
        params={
            "q": query,
            "country": "US",
            "search_lang": "en",
            "count": max(1, min(count, 50)),
            "safesearch": "strict",
            "spellcheck": "false",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("results") or []


def score_candidate(product, result: dict[str, Any]) -> Candidate | None:
    properties = result.get("properties") or {}
    image_url = properties.get("url")
    page_url = result.get("url")
    if not image_url:
        return None

    title = result.get("title") or ""
    source_domain = (
        (result.get("meta_url") or {}).get("hostname")
        or result.get("source")
        or hostname(page_url)
    )
    source_domain = (source_domain or "").lower().removeprefix("www.")

    # IMPORTANT: only external candidate evidence belongs here.
    # Never append product aliases/metadata to the text being tested, or the
    # catalog row can accidentally "match itself".
    page_searchable = " ".join(
        [
            title,
            page_url or "",
        ]
    ).lower()

    searchable = " ".join(
        [
            page_searchable,
            image_url or "",
        ]
    ).lower()

    searchable_norm = normalize_identifier(searchable)

    brand_norm = normalize_identifier(product.brand)
    upc_norm = normalize_identifier(product.upc)

    reasons: list[str] = []
    score = 0.0

    trusted_domains = trusted_domains_for_brand(product.brand)
    manufacturer_domain = bool(
        trusted_domains and domain_matches(source_domain, trusted_domains)
    )
    trusted_retailer = domain_matches(
        source_domain,
        TRUSTED_RETAILER_DOMAINS,
    )

    if manufacturer_domain:
        score += 0.40
        reasons.append("manufacturer domain")
    elif trusted_retailer:
        score += 0.24
        reasons.append("trusted retailer")
    elif trusted_domains:
        score -= 0.12
        reasons.append("non-manufacturer domain")

    brand_match = bool(brand_norm and brand_norm in searchable_norm)
    if brand_match:
        score += 0.10
        reasons.append("brand")

    alias_match_type, matched_alias = match_aliases_in_text(
        product,
        searchable,
    )
    page_match_type, page_matched_alias = match_aliases_in_text(
        product,
        page_searchable,
    )

    if alias_match_type == "exact":
        score += 0.35
        reasons.append("exact model")
        match_type = "exact"
    elif alias_match_type == "family":
        score += 0.28
        reasons.append("model family")
        match_type = "family"
    elif alias_match_type == "alias":
        score += 0.30
        reasons.append(f"ENERGY STAR alias {matched_alias}")
        match_type = "alias"
    else:
        match_type = "weak"

    if page_match_type in {"exact", "family", "alias"}:
        score += 0.06
        reasons.append(f"page confirms {page_match_type}")

    page_searchable_norm = normalize_identifier(page_searchable)

    if upc_norm and len(upc_norm) >= 8 and upc_norm in searchable_norm:
        score += 0.25
        reasons.append("UPC")
        if match_type == "weak":
            match_type = "upc"

        if upc_norm in page_searchable_norm:
            reasons.append("page confirms UPC")
            if page_match_type == "weak":
                page_match_type = "upc"

    provider_confidence = (result.get("confidence") or "").lower()
    if provider_confidence == "high":
        score += 0.05
        reasons.append("search confidence high")
    elif provider_confidence == "medium":
        score += 0.02

    width = properties.get("width")
    height = properties.get("height")
    if isinstance(width, int) and isinstance(height, int):
        if width >= 500 and height >= 500:
            score += 0.03
            reasons.append("usable resolution")

    score = max(0.0, min(score, 1.0))

    return Candidate(
        image_url=image_url,
        page_url=page_url,
        source_domain=source_domain or None,
        title=title or None,
        provider_confidence=provider_confidence or None,
        score=score,
        match_type=match_type,
        page_match_type=page_match_type or "weak",
        matched_alias=matched_alias,
        page_matched_alias=page_matched_alias,
        reasons=reasons,
    )


def choose_best_candidate(product, results: list[dict[str, Any]]) -> Candidate | None:
    candidates = [
        candidate
        for result in results
        if (candidate := score_candidate(product, result)) is not None
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[0]


def can_auto_verify(product, candidate: Candidate, threshold: float = 0.83) -> bool:
    trusted_domains = trusted_domains_for_brand(product.brand)
    source = candidate.source_domain or ""

    manufacturer_domain = bool(
        trusted_domains and domain_matches(source, trusted_domains)
    )
    trusted_retailer = domain_matches(
        source,
        TRUSTED_RETAILER_DOMAINS,
    )

    if candidate.match_type not in {"exact", "family", "alias", "upc"}:
        return False

    if manufacturer_domain:
        return candidate.score >= threshold

    # Retailer fallback is intentionally stricter:
    # - must be from a curated appliance retailer
    # - must match the exact model/family/UPC
    # - use a slightly lower threshold only because retailer pages do not
    #   receive the +0.40 manufacturer-domain score
    if trusted_retailer:
        # Retailers are only safe when the product page/title itself confirms
        # the identity. An image filename alone is not enough because retailer
        # pages sometimes embed photos from related/wrong variants.
        if candidate.page_match_type not in {"exact", "family", "alias", "upc"}:
            return False

        return candidate.score >= 0.72

    return False


def search_best_candidate(product, count: int = 20):
    """
    Two-pass search:
    1) manufacturer-domain search for known brands
    2) broad search fallback, where only curated retailers can verify
    """
    manufacturer_results = brave_image_search(
        build_query(product, manufacturer_only=True),
        count=count,
    )
    manufacturer_candidate = choose_best_candidate(
        product,
        manufacturer_results,
    )

    if (
        manufacturer_candidate
        and can_auto_verify(product, manufacturer_candidate)
    ):
        return manufacturer_candidate, "manufacturer"

    fallback_results = brave_image_search(
        build_query(product, manufacturer_only=False),
        count=count,
    )
    fallback_candidate = choose_best_candidate(
        product,
        fallback_results,
    )

    if fallback_candidate:
        return fallback_candidate, "fallback"

    return manufacturer_candidate, "manufacturer"

