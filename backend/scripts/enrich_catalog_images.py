from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from database import SessionLocal
import models
from services.image_enrichment import (
    can_auto_verify,
    search_best_candidate,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Batch-enrich ENERGY STAR catalog products with conservatively "
            "verified model/family images."
        )
    )
    parser.add_argument("--category")
    parser.add_argument("--brand")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--search-count", type=int, default=15)
    parser.add_argument("--min-confidence", type=float, default=0.83)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument(
        "--retry-checked",
        action="store_true",
        help="Include records already checked by Step 5.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help=(
            "Persist verified enrichment results. Without --commit, "
            "the command is a dry run."
        ),
    )
    args = parser.parse_args()

    db = SessionLocal()

    try:
        query = db.query(models.CatalogProduct)

        if args.category:
            query = query.filter(
                models.CatalogProduct.category == args.category.strip().lower()
            )

        if args.brand:
            query = query.filter(
                models.CatalogProduct.brand.ilike(args.brand.strip())
            )

        # Preserve already-verified manual mappings.
        query = query.filter(
            models.CatalogProduct.image_verified.is_(False)
        )

        if not args.retry_checked:
            query = query.filter(
                models.CatalogProduct.image_checked_at.is_(None)
            )

        products = (
            query
            .order_by(
                models.CatalogProduct.brand,
                models.CatalogProduct.model_number,
            )
            .limit(max(1, args.limit))
            .all()
        )

        if not products:
            print("No matching products need enrichment.")
            return

        verified = 0
        rejected = 0
        errors = 0

        print(
            f"Mode: {'COMMIT' if args.commit else 'DRY RUN'} | "
            f"Products: {len(products)} | "
            f"Threshold: {args.min_confidence:.2f}\n"
        )

        for index, product in enumerate(products, start=1):
            label = (
                f"{product.brand or 'Unknown'} "
                f"{product.model_number}"
            ).strip()

            try:
                candidate, search_pass = search_best_candidate(
                    product,
                    count=args.search_count,
                )

                now = datetime.now(timezone.utc)

                if candidate is None:
                    print(f"[{index}/{len(products)}] — {label}: no image candidate")
                    rejected += 1
                    if args.commit:
                        product.image_checked_at = now
                        product.image_match_type = "none"
                        product.image_confidence = 0.0
                        db.commit()
                    continue

                accepted = can_auto_verify(
                    product,
                    candidate,
                    threshold=args.min_confidence,
                )

                status = "✓ VERIFY" if accepted else "— reject"
                print(
                    f"[{index}/{len(products)}] {status} {label}\n"
                    f"    score={candidate.score:.2f} "
                    f"type={candidate.match_type} "
                    f"source={candidate.source_domain or 'unknown'} "
                    f"pass={search_pass}\n"
                    f"    reasons={', '.join(candidate.reasons) or 'none'}\n"
                    f"    page={candidate.page_url or 'n/a'}\n"
                    f"    image={candidate.image_url}\n"
                )

                if accepted:
                    verified += 1
                    if args.commit:
                        product.image_url = candidate.image_url
                        product.product_url = (
                            candidate.page_url or product.product_url
                        )
                        product.image_source = (
                            candidate.source_domain
                            or product.image_source
                        )
                        product.image_verified = True
                        product.image_match_type = candidate.match_type
                        product.image_confidence = candidate.score
                        product.image_checked_at = now
                        db.commit()
                else:
                    rejected += 1
                    if args.commit:
                        # Record that it was checked, but DO NOT store an
                        # unverified candidate as the product photo.
                        product.image_match_type = candidate.match_type
                        product.image_confidence = candidate.score
                        product.image_checked_at = now
                        db.commit()

            except Exception as exc:
                db.rollback()
                errors += 1
                print(
                    f"[{index}/{len(products)}] ! {label}: "
                    f"{type(exc).__name__}: {exc}"
                )

            if args.sleep > 0 and index < len(products):
                time.sleep(args.sleep)

        print("\nSummary")
        print(f"Verified: {verified}")
        print(f"Rejected/no match: {rejected}")
        print(f"Errors: {errors}")

        if not args.commit:
            print(
                "\nDry run only — nothing was written to PostgreSQL. "
                "Add --commit when the results look good."
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
