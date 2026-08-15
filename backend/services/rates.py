from fastapi import HTTPException

GEORGIA_POWER_PLAN = "Overnight Advantage"

SUPER_OFF_PEAK_RATE = 0.021859
OFF_PEAK_RATE = 0.101676
ON_PEAK_RATE = 0.297868


def get_grid_rate(
    hour: int,
    month: int = 8,
    weekday: int = 2,
):
    """
    Georgia Power Overnight Advantage model.

    weekday follows Python's convention:
    Monday = 0 ... Sunday = 6.

    On-peak:
    June-September, Monday-Friday, 2 PM-7 PM.

    Super off-peak:
    Every day, 11 PM-7 AM.

    All other hours:
    Off-peak.
    """
    if hour < 0 or hour > 23:
        raise HTTPException(
            status_code=400,
            detail="Hour must be between 0 and 23.",
        )

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12.",
        )

    if weekday < 0 or weekday > 6:
        raise HTTPException(
            status_code=400,
            detail="Weekday must be between 0 and 6.",
        )

    is_summer = 6 <= month <= 9
    is_weekday = weekday <= 4

    if hour >= 23 or hour < 7:
        return {
            "tier": "super_off_peak",
            "rate": SUPER_OFF_PEAK_RATE,
            "carbon_intensity": None,
            "rate_plan": GEORGIA_POWER_PLAN,
            "rate_source": "Georgia Power",
            "rate_type": "published_time_of_use_energy_charge",
        }

    if is_summer and is_weekday and 14 <= hour < 19:
        return {
            "tier": "on_peak",
            "rate": ON_PEAK_RATE,
            "carbon_intensity": None,
            "rate_plan": GEORGIA_POWER_PLAN,
            "rate_source": "Georgia Power",
            "rate_type": "published_time_of_use_energy_charge",
        }

    return {
        "tier": "off_peak",
        "rate": OFF_PEAK_RATE,
        "carbon_intensity": None,
        "rate_plan": GEORGIA_POWER_PLAN,
        "rate_source": "Georgia Power",
        "rate_type": "published_time_of_use_energy_charge",
    }
