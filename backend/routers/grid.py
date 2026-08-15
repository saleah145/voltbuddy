import os

from fastapi import APIRouter

from services.grid import (
    EIA_BALANCING_AUTHORITY,
    get_live_carbon_signal,
    get_live_grid_data,
)

router = APIRouter()


@router.get("/grid/live")
def get_live_grid():
    api_key = os.getenv("EIA_API_KEY")

    if not api_key:
        return {
            "available": False,
            "reason": "EIA_API_KEY is not configured.",
            "source": "U.S. Energy Information Administration",
            "balancing_authority": EIA_BALANCING_AUTHORITY,
        }

    grid_data = get_live_grid_data()

    if not grid_data:
        return {
            "available": False,
            "reason": "Live EIA grid data is temporarily unavailable.",
            "source": "U.S. Energy Information Administration",
            "balancing_authority": EIA_BALANCING_AUTHORITY,
        }

    return {
        "available": True,
        **grid_data,
    }


@router.get("/grid/carbon")
def get_grid_carbon():
    api_key = os.getenv("EIA_API_KEY")

    if not api_key:
        return {
            "available": False,
            "reason": "EIA_API_KEY is not configured.",
            "source": "U.S. Energy Information Administration",
            "balancing_authority": EIA_BALANCING_AUTHORITY,
        }

    carbon_data = get_live_carbon_signal()

    if not carbon_data:
        return {
            "available": False,
            "reason": "Live generation-mix data is temporarily unavailable.",
            "source": "U.S. Energy Information Administration",
            "balancing_authority": EIA_BALANCING_AUTHORITY,
        }

    return {
        "available": True,
        **carbon_data,
    }
