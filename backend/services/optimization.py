from math import ceil


def evaluate_appliance(
    appliance,
    grid,
    live_grid=None,
    carbon_signal=None,
):
    """
    Existing deterministic single-hour optimization score.

    Kept for backward compatibility with the current simulator UI/history while
    the 24-hour planner adds a second, schedule-oriented optimization layer.
    """
    original_cost_per_hour = appliance.kw * grid["rate"]

    score = 0
    score_factors = []

    if grid["tier"] == "on_peak":
        score += 45
        score_factors.append("Georgia Power is in the summer on-peak period.")
    elif grid["tier"] == "off_peak":
        score += 10
        score_factors.append("Electricity is in the standard off-peak period.")
    else:
        score -= 20
        score_factors.append("Electricity is in the super off-peak period.")

    if appliance.kw >= 5:
        score += 25
        score_factors.append("This appliance has very high power demand.")
    elif appliance.kw >= 1.5:
        score += 15
        score_factors.append("This appliance has relatively high power demand.")
    elif appliance.kw >= 0.5:
        score += 5
        score_factors.append("This appliance has moderate power demand.")

    if appliance.priority == "critical":
        score -= 100
        score_factors.append("This appliance is critical and should not be interrupted.")
    elif appliance.priority == "medium":
        score -= 10
        score_factors.append("This appliance has medium priority.")
    else:
        score += 10
        score_factors.append("This appliance has low priority and is easier to shift.")

    if not appliance.interruptible:
        score -= 100
        score_factors.append("This appliance is not interruptible.")
    else:
        score_factors.append("This appliance is marked flexible.")

    if live_grid:
        condition = live_grid.get("condition")
        if condition == "rising":
            score += 10
            score_factors.append("Regional grid demand is rising.")
        elif condition == "falling":
            score -= 5
            score_factors.append("Regional grid demand is falling.")

    if carbon_signal:
        signal = carbon_signal.get("signal")
        if signal == "fossil_heavy_mix":
            score += 8
            score_factors.append("The current generation mix is relatively fossil-heavy.")
        elif signal == "lower_carbon_mix":
            score -= 5
            score_factors.append("The current generation mix is relatively lower-carbon.")

    can_pause = appliance.interruptible and appliance.priority != "critical"

    if not can_pause:
        status = "running"
        decision = "keep_running"
        reason = "Kept running because this appliance is critical or not eligible to be interrupted."
    elif score >= 50:
        status = "paused"
        decision = "pause"
        reason = "Paused because the deterministic optimization score indicates a strong opportunity to reduce cost or grid impact."
    elif score >= 30:
        status = "running"
        decision = "recommend_shift"
        reason = "Kept running for now, but VoltBuddy recommends shifting this appliance to a cheaper or cleaner period if practical."
    else:
        status = "running"
        decision = "keep_running"
        reason = "Kept running because current price, demand, priority, and generation conditions do not justify pausing it."

    optimized_cost_per_hour = 0 if status == "paused" else original_cost_per_hour
    savings_per_hour = original_cost_per_hour if status == "paused" else 0

    return {
        "id": appliance.id,
        "name": appliance.name,
        "kw": appliance.kw,
        "priority": appliance.priority,
        "interruptible": appliance.interruptible,
        "status": status,
        "decision": decision,
        "optimization_score": score,
        "score_factors": score_factors,
        "reason": reason,
        "cost_per_hour": round(optimized_cost_per_hour, 2),
        "original_cost_per_hour": round(original_cost_per_hour, 2),
        "savings_per_hour": round(savings_per_hour, 2),
        "can_pause": can_pause,
    }


def _appliance_text(appliance):
    parts = [
        getattr(appliance, "name", ""),
        getattr(appliance, "category", ""),
        getattr(appliance, "product_type", ""),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def infer_runtime_hours(appliance):
    """
    Temporary deterministic runtime profile until runtime becomes a stored,
    editable appliance field.
    """
    stored = getattr(appliance, "typical_runtime_hours", None)
    if stored is not None:
        try:
            value = float(stored)
            if 0 < value <= 24:
                return value, "catalog"
        except (TypeError, ValueError):
            pass

    text = _appliance_text(appliance)

    if "refrigerator" in text or "fridge" in text:
        return 24.0, "estimated"
    if "ev" in text and ("charger" in text or "charging" in text):
        return 4.0, "estimated"
    if "dishwasher" in text:
        return 1.5, "estimated"
    if "dryer" in text:
        return 1.25, "estimated"
    if "washer" in text or "washing machine" in text:
        return 1.0, "estimated"
    if "air conditioner" in text or "a/c" in text or " ac " in f" {text} ":
        return 8.0, "estimated"
    if "television" in text or " tv" in f" {text}" or text.startswith("tv"):
        return 4.0, "estimated"
    if "gaming" in text and ("pc" in text or "computer" in text):
        return 3.0, "estimated"
    if "heater" in text:
        return 2.0, "estimated"

    return 1.0, "estimated"


def _circular_hour_distance(a, b):
    raw = abs(a - b)
    return min(raw, 24 - raw)


def _hours_forward(start_hour, end_hour):
    """Clock hours moving forward from start to end on a 24-hour cycle."""
    distance = (int(end_hour) - int(start_hour)) % 24
    return 24 if distance == 0 else distance


def _window_candidate_hours(earliest_start, latest_finish, runtime_hours):
    """
    Return clock-hour starts that fit completely inside a possibly overnight
    availability window.

    Example:
      earliest=18, latest_finish=7, runtime=4
      allows 18,19,20,21,22,23,0,1,2,3
    """
    available = _hours_forward(earliest_start, latest_finish)
    latest_start_offset = available - float(runtime_hours)

    if latest_start_offset < -1e-9:
        return []

    candidates = []
    for offset in range(24):
        if offset <= latest_start_offset + 1e-9:
            candidates.append((int(earliest_start) + offset) % 24)

    return candidates


def _candidate_start_hours(appliance, original_hour, runtime_hours):
    if runtime_hours >= 24:
        return [original_hour]

    if not getattr(appliance, "interruptible", False):
        return [original_hour]

    priority = (getattr(appliance, "priority", "medium") or "medium").lower()
    if priority == "critical":
        return [original_hour]

    flexibility = (
        getattr(appliance, "schedule_flexibility", None) or "auto"
    ).lower()

    if flexibility == "fixed":
        return [original_hour]

    if flexibility == "window":
        earliest = getattr(appliance, "earliest_start_hour", None)
        finish = getattr(appliance, "latest_finish_hour", None)

        if earliest is not None and finish is not None:
            candidates = _window_candidate_hours(
                earliest,
                finish,
                runtime_hours,
            )
            # A malformed/too-small window should never make the optimizer crash.
            return candidates or [original_hour]

    if flexibility == "anytime":
        return list(range(24))

    # Backward-compatible "auto" behavior for appliances that have not been
    # given explicit household scheduling preferences yet.
    if priority == "medium":
        return [
            hour
            for hour in range(24)
            if _circular_hour_distance(hour, original_hour) <= 6
        ]

    return list(range(24))


def _window_segments(start_hour, runtime_hours):
    """Return (absolute_hour_offset, fraction_of_hour) pairs."""
    remaining = float(runtime_hours)
    segments = []
    offset = 0

    while remaining > 1e-9:
        portion = min(1.0, remaining)
        segments.append((start_hour + offset, portion))
        remaining -= portion
        offset += 1

    return segments


def _window_cost(appliance, start_hour, runtime_hours, month, weekday, rate_getter):
    total = 0.0
    tiers = []
    rates = []

    for absolute_hour, fraction in _window_segments(start_hour, runtime_hours):
        day_offset, hour = divmod(absolute_hour, 24)
        effective_weekday = (weekday + day_offset) % 7
        grid = rate_getter(hour, month, effective_weekday)
        total += float(appliance.kw) * grid["rate"] * fraction
        tiers.append(grid["tier"])
        rates.append(grid["rate"])

    return total, tiers, rates


def _format_runtime(runtime_hours):
    if float(runtime_hours).is_integer():
        return f"{int(runtime_hours)} hr" if runtime_hours == 1 else f"{int(runtime_hours)} hrs"
    return f"{runtime_hours:g} hrs"


def build_24_hour_plan(appliances, original_hour, month, weekday, rate_getter):
    """
    Evaluate each selected appliance across the day's available start hours.

    - non-interruptible/critical appliances stay put
    - medium-priority appliances can move up to 6 hours in either direction
    - low-priority appliances can move anywhere in the 24-hour cycle
    - multi-hour appliances are optimized as continuous windows
    """
    schedule = []
    original_total = 0.0
    optimized_total = 0.0

    for appliance in appliances:
        runtime_hours, runtime_source = infer_runtime_hours(appliance)

        stored_preferred = getattr(appliance, "preferred_start_hour", None)
        appliance_original_hour = (
            int(stored_preferred)
            if stored_preferred is not None
            else original_hour
        )

        original_cost, original_tiers, _ = _window_cost(
            appliance,
            appliance_original_hour,
            runtime_hours,
            month,
            weekday,
            rate_getter,
        )

        candidate_hours = _candidate_start_hours(
            appliance,
            appliance_original_hour,
            runtime_hours,
        )

        best_hour = appliance_original_hour
        best_cost = original_cost
        best_tiers = original_tiers

        for candidate_hour in candidate_hours:
            candidate_cost, candidate_tiers, _ = _window_cost(
                appliance,
                candidate_hour,
                runtime_hours,
                month,
                weekday,
                rate_getter,
            )

            is_cheaper = candidate_cost < best_cost - 1e-9
            is_equal_but_closer = (
                abs(candidate_cost - best_cost) <= 1e-9
                and _circular_hour_distance(candidate_hour, appliance_original_hour)
                < _circular_hour_distance(best_hour, appliance_original_hour)
            )

            if is_cheaper or is_equal_but_closer:
                best_hour = candidate_hour
                best_cost = candidate_cost
                best_tiers = candidate_tiers

        savings = max(0.0, original_cost - best_cost)
        shifted = best_hour != appliance_original_hour and savings > 0.005

        if runtime_hours >= 24:
            reason = "Continuous-use appliance; VoltBuddy keeps its schedule unchanged."
        elif not getattr(appliance, "interruptible", False):
            reason = "Not marked flexible, so VoltBuddy keeps its original start time."
        elif (getattr(appliance, "priority", "medium") or "medium").lower() == "critical":
            reason = "Critical-priority appliance; VoltBuddy does not shift it."
        elif shifted:
            flexibility = (
                getattr(appliance, "schedule_flexibility", None) or "auto"
            ).lower()
            if flexibility == "window":
                reason = (
                    f"Shifted within your allowed window to a cheaper continuous "
                    f"{_format_runtime(runtime_hours)} slot."
                )
            elif flexibility == "anytime":
                reason = (
                    f"Shifted to the cheapest practical continuous "
                    f"{_format_runtime(runtime_hours)} slot."
                )
            else:
                reason = f"Shifted to a cheaper continuous {_format_runtime(runtime_hours)} window."
        else:
            reason = "The usual start time is already as cheap as the allowed alternatives."

        schedule.append(
            {
                "id": appliance.id,
                "name": appliance.name,
                "kw": appliance.kw,
                "priority": appliance.priority,
                "interruptible": appliance.interruptible,
                "runtime_hours": runtime_hours,
                "runtime_source": runtime_source,
                "schedule_flexibility": (
                    getattr(appliance, "schedule_flexibility", None) or "auto"
                ),
                "earliest_start_hour": getattr(appliance, "earliest_start_hour", None),
                "latest_finish_hour": getattr(appliance, "latest_finish_hour", None),
                "original_start_hour": appliance_original_hour,
                "optimized_start_hour": best_hour,
                "original_cost": round(original_cost, 2),
                "optimized_cost": round(best_cost, 2),
                "savings": round(savings, 2),
                "shifted": shifted,
                "reason": reason,
                "original_tiers": original_tiers,
                "optimized_tiers": best_tiers,
            }
        )

        original_total += original_cost
        optimized_total += best_cost

    savings_total = max(0.0, original_total - optimized_total)
    shifted_count = sum(1 for item in schedule if item["shifted"])

    # Full-day published rate curve for visualization / explanation.
    hourly_rates = []
    for hour in range(24):
        grid = rate_getter(hour, month, weekday)
        hourly_rates.append(
            {
                "hour": hour,
                "tier": grid["tier"],
                "rate": grid["rate"],
            }
        )

    cheapest_rate = min(item["rate"] for item in hourly_rates)
    cheapest_hours = [item["hour"] for item in hourly_rates if item["rate"] == cheapest_rate]
    peak_hours = [item["hour"] for item in hourly_rates if item["tier"] == "on_peak"]

    return {
        "original_daily_cost": round(original_total, 2),
        "optimized_daily_cost": round(optimized_total, 2),
        "estimated_daily_savings": round(savings_total, 2),
        "shifted_appliances": shifted_count,
        "selected_appliances": len(schedule),
        "schedule": schedule,
        "hourly_rates": hourly_rates,
        "cheapest_hours": cheapest_hours,
        "peak_hours": peak_hours,
        "runtime_note": "Runtime is catalog-backed when available; otherwise VoltBuddy uses a clearly labeled deterministic estimate.",
    }
