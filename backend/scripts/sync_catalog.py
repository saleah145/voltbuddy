from database import SessionLocal
from services.catalog_sync import DATASETS, sync_category

db = SessionLocal()

try:
    print("Syncing ENERGY STAR catalog...")

    for category in DATASETS:
        print(f"\nSyncing {category}...")
        result = sync_category(db, category)
        print(result)

    print("\nCatalog sync complete.")
finally:
    db.close()
