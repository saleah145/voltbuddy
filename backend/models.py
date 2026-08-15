from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class CatalogProduct(Base):
    __tablename__ = "catalog_products"

    id = Column(Integer, primary_key=True, index=True)
    source_key = Column(String, unique=True, nullable=False, index=True)
    energy_star_id = Column(String, nullable=True, index=True)
    category = Column(String, nullable=False, index=True)
    brand = Column(String, nullable=True, index=True)
    model_name = Column(String, nullable=True)
    model_number = Column(String, nullable=False, index=True)
    product_type = Column(String, nullable=True, index=True)
    annual_kwh = Column(Float, nullable=True, index=True)
    rated_power_kw = Column(Float, nullable=True)
    capacity = Column(Float, nullable=True)
    capacity_unit = Column(String, nullable=True)
    upc = Column(String, nullable=True, index=True)
    additional_model_information = Column(Text, nullable=True)
    features = Column(Text, nullable=True)
    source_dataset = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    product_url = Column(String, nullable=True)
    image_source = Column(String, nullable=True)
    image_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    image_match_type = Column(String, nullable=True)
    image_confidence = Column(Float, nullable=True)
    image_checked_at = Column(DateTime(timezone=True), nullable=True)
    energy_star_certified = Column(Boolean, nullable=False, default=True, server_default="true")
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Appliance(Base):
    __tablename__ = "appliances"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    kw = Column(Float, nullable=False)
    interruptible = Column(Boolean, nullable=False)
    priority = Column(String, nullable=False)

    category = Column(String, nullable=True, index=True)
    brand = Column(String, nullable=True, index=True)
    model_number = Column(String, nullable=True, index=True)
    annual_kwh = Column(Float, nullable=True)
    typical_runtime_hours = Column(Float, nullable=True)
    preferred_start_hour = Column(Integer, nullable=True)
    earliest_start_hour = Column(Integer, nullable=True)
    latest_finish_hour = Column(Integer, nullable=True)
    schedule_flexibility = Column(String, nullable=True)
    source = Column(String, nullable=True)
    is_catalog = Column(Boolean, nullable=False, default=False, server_default="false")
    is_estimate = Column(Boolean, nullable=False, default=False, server_default="false")
    catalog_product_id = Column(Integer, ForeignKey("catalog_products.id", ondelete="SET NULL"), nullable=True, index=True)


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    hour = Column(Integer, nullable=False)
    electricity_rate = Column(Float, nullable=False)
    tier = Column(String, nullable=False)
    normal_cost = Column(Float, nullable=False)
    optimized_cost = Column(Float, nullable=False)
    savings = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Home(Base):
    __tablename__ = "homes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HomeAppliance(Base):
    __tablename__ = "home_appliances"

    id = Column(Integer, primary_key=True, index=True)
    home_id = Column(Integer, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False)
    appliance_id = Column(String, ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False)
