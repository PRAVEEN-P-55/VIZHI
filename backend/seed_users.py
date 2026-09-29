"""Seed demo users for each RBAC role.

Idempotent — only creates users that don't already exist. Demo credentials are
printed for the hackathon walkthrough (prototype only; change for any real use).
"""
from __future__ import annotations

from app.auth.security import hash_password
from app.db import SessionLocal, init_db
from app.models import User

DEMO_USERS = [
    # username, password, full_name, role, scope_value
    ("admin", "admin123", "VIZHI National Admin", "i4c_admin", ""),
    ("tn_lea", "lea123", "Tamil Nadu State LEA", "state_lea", "Tamil Nadu"),
    ("hdfc_officer", "bank123", "HDFC Bank Officer", "bank_officer", "HDFC"),
    ("sbi_officer", "bank123", "SBI Bank Officer", "bank_officer", "SBI"),
]


def seed(verbose: bool = True) -> None:
    init_db()
    db = SessionLocal()
    try:
        created = 0
        for username, pw, full_name, role, scope in DEMO_USERS:
            if db.query(User).filter(User.username == username).first():
                continue
            db.add(User(
                username=username,
                full_name=full_name,
                hashed_password=hash_password(pw),
                role=role,
                scope_value=scope,
            ))
            created += 1
        db.commit()
        if verbose:
            print(f"Seeded {created} new user(s). Demo credentials:")
            for username, pw, _, role, scope in DEMO_USERS:
                print(f"  {username} / {pw}   ({role}{' -> ' + scope if scope else ''})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
