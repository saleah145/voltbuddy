import argparse
import csv
import re
from pathlib import Path

from sqlalchemy import func

from database import SessionLocal
import models


def normalize(value):
    return (value or "").strip()


def wildcard_regex(catalog_model: str):
    """
    ENERGY STAR sometimes stores model families such as RF27CG5400**.
    Convert * into a wildcard while keeping all other characters literal.
    """
    escaped = re.escape(catalog_model)
    return "^" + escaped.replace(r"\*", ".*") + "$"


def find_matches(db, brand: str, model_number: str):
    query = db.query(models.CatalogProduct)

    if brand:
        query = query.filter(
            func.lower(models.CatalogProduct.brand) == brand.lower()
        )

    # 1) Exact match
    exact = query.filter(
        func.lower(models.CatalogProduct.model_number)
        == model_number.lower()
    ).all()

    if exact:
        return exact, "exact"

    # 2) ENERGY STAR wildcard / model-family match.
    # Pull same-brand candidates, then compare locally so * means wildcard.
    candidates = query.filter(
        models.CatalogProduct.model_number.isnot(None)
    ).all()

    family_matches = []
    for product in candidates:
        catalog_model = normalize(product.model_number)
        if not catalog_model or "*" not in catalog_model:
            continue

        if re.match(
            wildcard_regex(catalog_model),
            model_number,
            flags=re.IGNORECASE,
        ):
            family_matches.append(product)

    if family_matches:
        return family_matches, "family"

    # 3) Prefix fallback when catalog stripped manufacturer suffixes.
    # Only use a reasonably long prefix to avoid broad accidental matches.
    clean_input = re.sub(r"[^A-Za-z0-9]", "", model_number).lower()

    prefix_matches = []
    for product in candidates:
        clean_catalog = re.sub(
            r"[^A-Za-z0-9]",
            "",
            normalize(product.model_number).replace("*", ""),
        ).lower()

        if (
            len(clean_catalog) >= 8
            and clean_input.startswith(clean_catalog)
        ):
            prefix_matches.append(product)

    if prefix_matches:
        return prefix_matches, "prefix"

    return [], None


def main():
    parser = argparse.ArgumentParser(
        description="Import verified model-specific product image metadata."
    )
    parser.add_argument("csv_path")
    args = parser.parse_args()

    path = Path(args.csv_path)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    db = SessionLocal()
    updated = 0
    skipped = 0

    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                brand = normalize(row.get("brand"))
                model_number = normalize(row.get("model_number"))
                image_url = normalize(row.get("image_url"))
                product_url = normalize(row.get("product_url"))
                image_source = normalize(row.get("image_source"))

                if not model_number:
                    print("skip: missing model_number")
                    skipped += 1
                    continue

                matches, match_type = find_matches(
                    db,
                    brand,
                    model_number,
                )

                if not matches:
                    print(
                        f"skip: no catalog match for "
                        f"{brand} {model_number}"
                    )
                    skipped += 1
                    continue

                for product in matches:
                    product.product_url = (
                        product_url or product.product_url
                    )
                    product.image_source = (
                        image_source or product.image_source
                    )

                    # Only mark a photo verified when a model-specific
                    # image URL was explicitly supplied.
                    if image_url:
                        product.image_url = image_url
                        product.image_verified = True

                    updated += 1

                    print(
                        f"✓ {product.brand} {product.model_number} "
                        f"<- {model_number} ({match_type} match; "
                        f"photo={'yes' if image_url else 'no'}, "
                        f"product page={'yes' if product_url else 'no'})"
                    )

        db.commit()
    finally:
        db.close()

    print(f"\nUpdated: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
