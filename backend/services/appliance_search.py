from difflib import SequenceMatcher

SYNONYMS = {
    "fridge": "refrigerator",
    "freezer fridge": "refrigerator",
    "washing machine": "washer",
    "laundry machine": "washer",
    "television": "tv",
    "telly": "tv",
    "ac": "air conditioner",
    "a/c": "air conditioner",
    "air conditioning": "air conditioner",
    "ev": "ev charger",
    "electric car charger": "ev charger",
}


def normalize_query(value: str) -> str:
    cleaned = " ".join((value or "").lower().replace("-", " ").split())
    if cleaned in SYNONYMS:
        return SYNONYMS[cleaned]
    # Replace common phrases inside longer searches, e.g. "Samsung fridge".
    for alias, canonical in sorted(SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
        cleaned = cleaned.replace(alias, canonical)
    return " ".join(cleaned.split())


def appliance_search_score(appliance, query: str) -> float:
    q = normalize_query(query)
    if not q:
        return 0

    fields = [
        appliance.name or "",
        appliance.category or "",
        appliance.brand or "",
        appliance.model_number or "",
    ]
    haystack = " ".join(normalize_query(field) for field in fields if field)

    if q in haystack:
        return 1.0

    best = 0.0
    for field in fields:
        field = normalize_query(field)
        if not field:
            continue
        best = max(best, SequenceMatcher(None, q, field).ratio())
        for token in field.split():
            best = max(best, SequenceMatcher(None, q, token).ratio())
    return best


def rank_appliances(appliances, query: str, limit: int = 8):
    ranked = []
    for appliance in appliances:
        score = appliance_search_score(appliance, query)
        if score >= 0.48:
            ranked.append((score, appliance))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:limit]
