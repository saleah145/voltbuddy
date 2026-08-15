from sqlalchemy import inspect, text

from database import engine


def add_column_if_missing(table_name: str, column_name: str, ddl: str):
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns(table_name)}

    if column_name in existing:
        print(f"✓ {table_name}.{column_name} already exists")
        return

    with engine.begin() as connection:
        connection.execute(
            text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}')
        )

    print(f"✓ added {table_name}.{column_name}")


def main():
    add_column_if_missing("catalog_products", "image_url", "VARCHAR")
    add_column_if_missing("catalog_products", "product_url", "VARCHAR")
    add_column_if_missing("catalog_products", "image_source", "VARCHAR")
    add_column_if_missing(
        "catalog_products",
        "image_verified",
        "BOOLEAN NOT NULL DEFAULT FALSE",
    )

    print("\nCatalog image fields are ready.")


if __name__ == "__main__":
    main()
