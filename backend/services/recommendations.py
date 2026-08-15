def generate_recommendations(
    appliance_results,
    grid,
    live_grid=None,
    carbon_signal=None,
):
    """
    Convert deterministic appliance decisions into user-facing advice.

    Recommendations are based on known tariff windows and current
    grid/carbon signals. VoltBuddy does not forecast a future cleaner
    grid mix here.
    """
    recommendations = []

    for appliance in appliance_results:
        decision = appliance["decision"]

        if decision == "pause":
            recommendations.append(
                {
                    "type": "pause_now",
                    "priority": "high",
                    "appliance_id": appliance["id"],
                    "appliance_name": appliance["name"],
                    "title": f"Pause {appliance['name']} for now",
                    "message": (
                        f"{appliance['name']} has an optimization score of "
                        f"{appliance['optimization_score']}. Pausing it now "
                        "reduces current energy cost and avoids flexible load "
                        "during less favorable grid conditions."
                    ),
                    "best_time": "After 11 PM",
                    "best_time_reason": (
                        "Georgia Power Overnight Advantage enters its "
                        "super off-peak period at 11 PM."
                    ),
                    "estimated_hourly_savings": appliance["savings_per_hour"],
                }
            )

        elif decision == "recommend_shift":
            recommendations.append(
                {
                    "type": "shift_load",
                    "priority": "medium",
                    "appliance_id": appliance["id"],
                    "appliance_name": appliance["name"],
                    "title": f"Shift {appliance['name']} if practical",
                    "message": (
                        f"{appliance['name']} is flexible enough to move, but "
                        "current conditions do not justify automatically "
                        "pausing it."
                    ),
                    "best_time": "After 11 PM",
                    "best_time_reason": (
                        "The published super off-peak window is the lowest-cost "
                        "period on the Overnight Advantage rate."
                    ),
                    "estimated_hourly_savings": 0,
                }
            )

        else:
            recommendations.append(
                {
                    "type": "good_time_to_run",
                    "priority": "low",
                    "appliance_id": appliance["id"],
                    "appliance_name": appliance["name"],
                    "title": f"Keep {appliance['name']} running",
                    "message": appliance["reason"],
                    "best_time": "Current time is acceptable",
                    "best_time_reason": (
                        "VoltBuddy's deterministic score does not justify "
                        "pausing or shifting this appliance right now."
                    ),
                    "estimated_hourly_savings": 0,
                }
            )

    if live_grid:
        recommendations.append(
            {
                "type": "grid_context",
                "priority": "low",
                "appliance_id": None,
                "appliance_name": None,
                "title": "Regional grid context",
                "message": (
                    f"Southern Company demand is currently "
                    f"{live_grid.get('condition', 'unknown')}."
                ),
                "best_time": None,
                "best_time_reason": None,
                "estimated_hourly_savings": 0,
            }
        )

    if carbon_signal:
        recommendations.append(
            {
                "type": "carbon_context",
                "priority": "low",
                "appliance_id": None,
                "appliance_name": None,
                "title": "Generation mix context",
                "message": carbon_signal.get(
                    "message",
                    "Current generation-mix data is available."
                ),
                "best_time": None,
                "best_time_reason": None,
                "estimated_hourly_savings": 0,
            }
        )

    return recommendations
