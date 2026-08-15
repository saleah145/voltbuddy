from sqlalchemy import inspect, text
from database import engine

COLUMNS = {
    "preferred_start_hour": "INTEGER",
    "earliest_start_hour": "INTEGER",
    "latest_finish_hour": "INTEGER",
    "schedule_flexibility": "VARCHAR",
}

def main():
    existing = {column["name"] for column in inspect(engine).get_columns("appliances")}
    with engine.begin() as connection:
        for column, sql_type in COLUMNS.items():
            if column in existing:
                print(f"✓ appliances.{column} already exists")
            else:
                connection.execute(text(f'ALTER TABLE appliances ADD COLUMN "{column}" {sql_type}'))
                print(f"✓ added appliances.{column}")
    print("Manual appliance fields are ready.")

if __name__ == "__main__":
    main()
