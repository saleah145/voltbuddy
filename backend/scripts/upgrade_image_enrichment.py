from sqlalchemy import inspect, text

from database import engine


COLUMNS = {
    "additional_model_information": "TEXT",
    "image_match_type": "VARCHAR",
    "image_confidence": "DOUBLE PRECISION",
    "image_checked_at": "TIMESTAMP WITH TIME ZONE",
}


def main():
    inspector = inspect(engine)
    existing = {
        column["name"]
        for column in inspector.get_columns("catalog_products")
    }

    with engine.begin() as connection:
        for name, ddl in COLUMNS.items():
            if name in existing:
                print(f"✓ catalog_products.{name} already exists")
                continue

            connection.execute(
                text(
                    f"ALTER TABLE catalog_products "
                    f"ADD COLUMN {name} {ddl}"
                )
            )
            print(f"✓ added catalog_products.{name}")

    print("\nStep 5 enrichment fields are ready.")


if __name__ == "__main__":
    main()
