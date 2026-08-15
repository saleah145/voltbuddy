# Conservative generic profiles. These are intentionally labeled estimates,
# not manufacturer specifications.
CATEGORY_ESTIMATES = {
    "refrigerator": {"name": "Estimated refrigerator", "kw": 0.15, "annual_kwh": 650, "runtime": 24, "interruptible": False, "priority": "critical"},
    "washer": {"name": "Estimated washing machine", "kw": 0.5, "annual_kwh": 150, "runtime": 1.0, "interruptible": True, "priority": "low"},
    "dryer": {"name": "Estimated clothes dryer", "kw": 3.0, "annual_kwh": 900, "runtime": 1.0, "interruptible": True, "priority": "low"},
    "dishwasher": {"name": "Estimated dishwasher", "kw": 1.4, "annual_kwh": 300, "runtime": 1.5, "interruptible": True, "priority": "low"},
    "tv": {"name": "Estimated television", "kw": 0.12, "annual_kwh": 110, "runtime": 4.0, "interruptible": False, "priority": "medium"},
    "gaming pc": {"name": "Estimated gaming PC", "kw": 0.5, "annual_kwh": 500, "runtime": 4.0, "interruptible": False, "priority": "medium"},
    "space heater": {"name": "Estimated space heater", "kw": 1.5, "annual_kwh": 600, "runtime": 3.0, "interruptible": True, "priority": "medium"},
    "air conditioner": {"name": "Estimated room air conditioner", "kw": 1.2, "annual_kwh": 900, "runtime": 6.0, "interruptible": True, "priority": "medium"},
    "ev charger": {"name": "Estimated EV charger", "kw": 7.2, "annual_kwh": 3000, "runtime": 4.0, "interruptible": True, "priority": "low"},
}


def get_estimate(category: str):
    key = " ".join((category or "").lower().replace("-", " ").split())
    aliases = {"fridge": "refrigerator", "washing machine": "washer", "television": "tv", "ac": "air conditioner", "ev": "ev charger"}
    key = aliases.get(key, key)
    return key, CATEGORY_ESTIMATES.get(key)
