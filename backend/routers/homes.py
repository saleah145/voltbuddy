from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas import HomeCreate

router = APIRouter()


def _serialize_appliance(appliance):
    return {
        "id": appliance.id,
        "name": appliance.name,
        "kw": appliance.kw,
        "interruptible": appliance.interruptible,
        "priority": appliance.priority,
        "category": getattr(appliance, "category", None),
        "brand": getattr(appliance, "brand", None),
        "model_number": getattr(appliance, "model_number", None),
        "annual_kwh": getattr(appliance, "annual_kwh", None),
        "source": getattr(appliance, "source", None),
        "is_catalog": getattr(appliance, "is_catalog", False),
        "is_estimate": getattr(appliance, "is_estimate", False),
        "catalog_product_id": getattr(appliance, "catalog_product_id", None),
    }


@router.post("/homes")
def create_home(
    home: HomeCreate,
    db: Session = Depends(get_db),
):
    valid_appliances = (
        db.query(models.Appliance)
        .filter(models.Appliance.id.in_(home.appliances))
        .all()
    )

    valid_ids = {appliance.id for appliance in valid_appliances}

    missing_ids = [
        appliance_id
        for appliance_id in home.appliances
        if appliance_id not in valid_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown appliance IDs: {missing_ids}",
        )

    new_home = models.Home(name=home.name)

    db.add(new_home)
    db.commit()
    db.refresh(new_home)

    for appliance_id in home.appliances:
        db.add(
            models.HomeAppliance(
                home_id=new_home.id,
                appliance_id=appliance_id,
            )
        )

    db.commit()

    return {
        "id": new_home.id,
        "name": new_home.name,
        "appliances": home.appliances,
        "created_at": new_home.created_at,
    }


@router.get("/homes")
def get_homes(db: Session = Depends(get_db)):
    homes = (
        db.query(models.Home)
        .order_by(models.Home.created_at.desc())
        .all()
    )

    results = []

    for home in homes:
        links = (
            db.query(models.HomeAppliance)
            .filter(models.HomeAppliance.home_id == home.id)
            .all()
        )

        results.append(
            {
                "id": home.id,
                "name": home.name,
                "appliances": [link.appliance_id for link in links],
                "created_at": home.created_at,
            }
        )

    return results


@router.get("/homes/{home_id}")
def get_home(
    home_id: int,
    db: Session = Depends(get_db),
):
    home = (
        db.query(models.Home)
        .filter(models.Home.id == home_id)
        .first()
    )

    if not home:
        raise HTTPException(
            status_code=404,
            detail="Home not found.",
        )

    links = (
        db.query(models.HomeAppliance)
        .filter(models.HomeAppliance.home_id == home.id)
        .all()
    )

    appliance_ids = [link.appliance_id for link in links]

    appliances = []
    if appliance_ids:
        appliances = (
            db.query(models.Appliance)
            .filter(models.Appliance.id.in_(appliance_ids))
            .all()
        )

    appliance_by_id = {appliance.id: appliance for appliance in appliances}

    return {
        "id": home.id,
        "name": home.name,
        "created_at": home.created_at,
        "appliances": [
            _serialize_appliance(appliance_by_id[appliance_id])
            for appliance_id in appliance_ids
            if appliance_id in appliance_by_id
        ],
    }


@router.delete("/homes/{home_id}")
def delete_home(
    home_id: int,
    db: Session = Depends(get_db),
):
    home = (
        db.query(models.Home)
        .filter(models.Home.id == home_id)
        .first()
    )

    if not home:
        raise HTTPException(
            status_code=404,
            detail="Home not found.",
        )

    db.query(models.HomeAppliance).filter(
        models.HomeAppliance.home_id == home_id
    ).delete(synchronize_session=False)

    db.delete(home)
    db.commit()

    return {
        "deleted": True,
        "home_id": home_id,
    }
