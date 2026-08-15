import pytest
from fastapi import HTTPException

from services.rates import (
    OFF_PEAK_RATE,
    ON_PEAK_RATE,
    SUPER_OFF_PEAK_RATE,
    get_grid_rate,
)


def test_super_off_peak_midnight():
    result = get_grid_rate(0, 8, 2)
    assert result["tier"] == "super_off_peak"
    assert result["rate"] == SUPER_OFF_PEAK_RATE


def test_super_off_peak_11pm():
    result = get_grid_rate(23, 8, 2)
    assert result["tier"] == "super_off_peak"
    assert result["rate"] == SUPER_OFF_PEAK_RATE


def test_summer_weekday_on_peak():
    result = get_grid_rate(16, 8, 2)
    assert result["tier"] == "on_peak"
    assert result["rate"] == ON_PEAK_RATE


def test_weekend_is_off_peak():
    result = get_grid_rate(16, 8, 6)
    assert result["tier"] == "off_peak"
    assert result["rate"] == OFF_PEAK_RATE


def test_winter_is_off_peak():
    result = get_grid_rate(16, 1, 2)
    assert result["tier"] == "off_peak"
    assert result["rate"] == OFF_PEAK_RATE


@pytest.mark.parametrize(
    "hour,month,weekday",
    [
        (-1, 8, 2),
        (24, 8, 2),
        (12, 0, 2),
        (12, 13, 2),
        (12, 8, -1),
        (12, 8, 7),
    ],
)
def test_invalid_rate_inputs(hour, month, weekday):
    with pytest.raises(HTTPException):
        get_grid_rate(hour, month, weekday)
