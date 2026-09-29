"""CLI entrypoint: ingest datasets and train all models.

Usage:
    python train.py            # ingest + train + persist artifacts
    python train.py --no-ingest # retrain from already-loaded DB
"""
from __future__ import annotations

import argparse
import time

from app.ingest import ingest_all
from app.ml.data import clear_cache
from app.ml.pipeline import train_all


def main() -> None:
    ap = argparse.ArgumentParser(description="VIZHI training pipeline")
    ap.add_argument("--no-ingest", action="store_true", help="skip CSV ingestion")
    ap.add_argument("--k", type=int, default=5, help="K for Precision@K")
    args = ap.parse_args()

    t0 = time.time()
    if not args.no_ingest:
        print("[1/2] Ingesting datasets ...")
        ingest_all()
        clear_cache()
    print("[2/2] Training models ...")
    metrics = train_all(k=args.k)
    print(f"\nDone in {time.time() - t0:.1f}s")
    print(f"macro_f1={metrics['macro_f1']}  precision_at_{args.k}={metrics.get(f'precision_at_{args.k}')}")


if __name__ == "__main__":
    main()
