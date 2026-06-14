"""Database layer: SQLAlchemy models and session handling.

  Watcher    -> one "tab" in the UI: a name and a notification email.
  Product    -> a tracked product link belonging to a Watcher.
  PricePoint -> a single recorded price for a Product (history).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from . import config


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Watcher(Base):
    __tablename__ = "watchers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    products: Mapped[list["Product"]] = relationship(
        back_populates="watcher",
        cascade="all, delete-orphan",
        order_by="Product.created_at",
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    watcher_id: Mapped[int] = mapped_column(
        ForeignKey("watchers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    css_selector: Mapped[str] = mapped_column(String(255), default="")
    use_js: Mapped[bool] = mapped_column(Boolean, default=False)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    lowest_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    watcher: Mapped["Watcher"] = relationship(back_populates="products")
    history: Mapped[list["PricePoint"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="PricePoint.checked_at",
    )


class PricePoint(Base):
    __tablename__ = "price_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    product: Mapped["Product"] = relationship(back_populates="history")


engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if config.DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _migrate() -> None:
    """Add columns introduced after the first release (SQLite ADD COLUMN)."""
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("products")}
    if "use_js" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE products ADD COLUMN use_js BOOLEAN DEFAULT 0")
            )


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrate()


def iso_utc(dt: datetime | None) -> str | None:
    """Serialize a stored timestamp as a UTC-aware ISO string.

    Timestamps are written as UTC but SQLite returns them naive, which makes
    clients treat them as local time. Tagging them with the UTC offset lets the
    UI convert to the user's timezone correctly.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
