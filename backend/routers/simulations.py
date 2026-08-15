from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas import SimulationRequest
from services.grid import get_live_carbon_signal, get_live_grid_data
from services.optimization import build_24_hour_plan, evaluate_appliance
from services.rates import get_grid_rate
from services.recommendations import generate_recommendations

router = APIRouter()


@router.post("/simulate")
def simulate(
    request: SimulationRequest,
    db: Session = Depends(get_db),
):
    requested_ids = request.appliances

    db_appliances = (
        db.query(models.Appliance)
        .filter(models.Appliance.id.in_(requested_ids))
        .all()
    )

    appliance_by_id = {
        appliance.id: appliance
        for appliance in db_appliances
    }

    missing_ids = [
        appliance_id
        for appliance_id in requested_ids
        if appliance_id not in appliance_by_id
    ]

    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "One or more selected appliances do not exist.",
                "unknown_appliance_ids": missing_ids,
            },
        )

    grid = get_grid_rate(
        request.hour,
        request.month,
        request.weekday,
    )

    live_grid = get_live_grid_data()
    carbon_signal = get_live_carbon_signal()

    results = []

    for appliance_id in requested_ids:
        appliance = appliance_by_id[appliance_id]

        results.append(
            evaluate_appliance(
                appliance,
                grid,
                live_grid,
                carbon_signal,
            )
        )

    original_total = sum(
        appliance["original_cost_per_hour"]
        for appliance in results
    )

    optimized_total = sum(
        appliance["cost_per_hour"]
        for appliance in results
    )

    total_savings = sum(
        appliance["savings_per_hour"]
        for appliance in results
    )

    paused_count = sum(
        1
        for appliance in results
        if appliance.get("decision") == "pause"
    )

    shift_count = sum(
        1
        for appliance in results
        if appliance.get("decision") == "recommend_shift"
    )

    optimization_summary = {
        "paused_appliances": paused_count,
        "shift_recommendations": shift_count,
        "decision_model": "deterministic_weighted_score",
        "score_thresholds": {
            "pause": 50,
            "recommend_shift": 30,
        },
    }

    recommendations = generate_recommendations(
        results,
        grid,
        live_grid,
        carbon_signal,
    )

    daily_plan = build_24_hour_plan(
        [appliance_by_id[appliance_id] for appliance_id in requested_ids],
        request.hour,
        request.month,
        request.weekday,
        get_grid_rate,
    )

    simulation_record = models.Simulation(
        hour=request.hour,
        electricity_rate=grid["rate"],
        tier=grid["tier"],
        normal_cost=round(original_total, 2),
        optimized_cost=round(optimized_total, 2),
        savings=round(total_savings, 2),
    )

    db.add(simulation_record)
    db.commit()
    db.refresh(simulation_record)

    return {
        "id": simulation_record.id,
        "hour": request.hour,
        "grid": grid,
        "live_grid": live_grid,
        "carbon_signal": carbon_signal,
        "optimization_summary": optimization_summary,
        "recommendations": recommendations,
        "appliances": results,
        "without_voltbuddy": round(original_total, 2),
        "with_voltbuddy": round(optimized_total, 2),
        "total_savings_per_hour": round(total_savings, 2),
        "daily_plan": daily_plan,
        "created_at": simulation_record.created_at,
    }


@router.get("/simulations")
def get_simulations(db: Session = Depends(get_db)):
    simulations = (
        db.query(models.Simulation)
        .order_by(models.Simulation.created_at.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "id": simulation.id,
            "hour": simulation.hour,
            "electricity_rate": simulation.electricity_rate,
            "tier": simulation.tier,
            "normal_cost": simulation.normal_cost,
            "optimized_cost": simulation.optimized_cost,
            "savings": simulation.savings,
            "created_at": simulation.created_at,
        }
        for simulation in simulations
    ]


@router.delete("/simulations")
def clear_simulations(db: Session = Depends(get_db)):
    deleted_count = db.query(models.Simulation).delete(
        synchronize_session=False
    )
    db.commit()

    return {
        "deleted": True,
        "deleted_count": deleted_count,
    }
