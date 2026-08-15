from __future__ import annotations

CATEGORY_DEFAULTS = {
    "refrigerator": {"interruptible": False, "priority": "critical", "runtime": 24.0, "cycles": 365},
    "washer": {"interruptible": True, "priority": "low", "runtime": 1.0, "cycles": 295},
    "dryer": {"interruptible": True, "priority": "low", "runtime": 1.0, "cycles": 283},
    "dishwasher": {"interruptible": True, "priority": "low", "runtime": 1.5, "cycles": 215},
    "tv": {"interruptible": False, "priority": "medium", "runtime": 4.0, "cycles": 365},
    "air conditioner": {"interruptible": True, "priority": "medium", "runtime": 6.0, "cycles": 120},
    "ev charger": {"interruptible": True, "priority": "low", "runtime": 4.0, "cycles": 250},
}


def derive_profile(product):
    defaults = CATEGORY_DEFAULTS.get(product.category, {"interruptible": True, "priority": "low", "runtime": 1.0, "cycles": 365})

    kw = product.rated_power_kw
    if not kw and product.annual_kwh:
        annual_runtime = max(defaults["runtime"] * defaults["cycles"], 1)
        kw = product.annual_kwh / annual_runtime
    if not kw:
        kw = 0.5

    # Keep simulator-safe values until the 24-hour scheduling engine gets a richer duty-cycle model.
    kw = max(0.01, min(float(kw), 50.0))

    label = " ".join(part for part in [product.brand, product.model_name or product.model_number] if part).strip()
    return {
        "name": label or product.model_number,
        "kw": round(kw, 4),
        "interruptible": defaults["interruptible"],
        "priority": defaults["priority"],
        "typical_runtime_hours": defaults["runtime"],
    }
