from __future__ import annotations

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Account, IntegrationConfig, User


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_demo_data()


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            user = User(full_name="Nhu Admin", email="abc@gmail.com", phone="0900000000", is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)

            db.add(
                Account(
                    user_id=user.id,
                    provider="local",
                    email="abc@gmail.com",
                    password_hash=hash_password("123456"),
                    is_active=True,
                )
            )
            db.add(
                IntegrationConfig(
                    user_id=user.id,
                    provider="goclaw",
                    name="Goclaw Demo",
                    api_key="demo_goclaw_key",
                    api_secret="demo_goclaw_secret",
                    base_url="https://api.goclaw.com",
                    project_id="demo-project",
                    config_json={"workspace": "demo"},
                    is_active=True,
                )
            )
            db.add(
                IntegrationConfig(
                    user_id=user.id,
                    provider="cloudinary",
                    name="Cloudinary Demo",
                    api_key="demo_cloudinary_key",
                    api_secret="demo_cloudinary_secret",
                    base_url="https://res.cloudinary.com",
                    project_id="demo-project",
                    config_json={"cloud_name": "demo-cloud"},
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()
