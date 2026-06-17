"""FastAPI app: REST API, the price-check routine, scheduler and MQTT publish."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from . import config, ha_mqtt, notifier, scraper
from .database import PricePoint, Product, SessionLocal, Watcher, init_db, iso_utc

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("hintavahti")

STATIC_DIR = Path(__file__).parent / "static"
scheduler = BackgroundScheduler(timezone="UTC")

limiter = Limiter(key_func=get_remote_address)


def check_product(session: Session, product: Product) -> dict:
    old_price = product.last_price
    result = {"id": product.id, "ok": False, "price": None, "notified": False, "error": ""}

    try:
        new_price = scraper.get_price(product.url, product.css_selector, product.use_js)
    except scraper.PriceError as exc:
        product.last_error = str(exc)
        product.last_checked = datetime.now(timezone.utc)
        session.commit()
        ha_mqtt.publish_product(product)
        result["error"] = str(exc)
        return result

    product.last_error = ""
    product.last_price = new_price
    product.last_checked = datetime.now(timezone.utc)
    if product.lowest_price is None or new_price < product.lowest_price:
        product.lowest_price = new_price
    session.add(PricePoint(product_id=product.id, price=new_price))

    notify = False
    if product.target_price is not None:
        crossed = old_price is None or old_price > product.target_price
        if new_price <= product.target_price and crossed:
            notify = True
    elif old_price is not None and new_price < old_price:
        notify = True

    if notify:
        notifier.send_drop_email(
            to_email=product.watcher.email,
            product_name=product.name,
            product_url=product.url,
            new_price=new_price,
            old_price=old_price,
        )
        result["notified"] = True

    session.commit()
    ha_mqtt.publish_product(product)
    result.update(ok=True, price=new_price)
    return result


def run_all_checks() -> None:
    log.info("Aloitetaan ajastettu hintatarkistus.")
    session = SessionLocal()
    try:
        for product in session.query(Product).all():
            try:
                check_product(session, product)
            except Exception:  # noqa: BLE001
                log.exception("Tuotteen %s tarkistus kaatui", product.id)
            time.sleep(config.REQUEST_DELAY_SECONDS)
    finally:
        session.close()
    log.info("Hintatarkistus valmis.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Re-announce existing products to Home Assistant on startup.
    session = SessionLocal()
    try:
        ha_mqtt.publish_all(session.query(Product).all())
    except Exception:  # noqa: BLE001
        log.exception("MQTT-alkujulkaisu epäonnistui")
    finally:
        session.close()

    interval = max(int(config.CHECK_INTERVAL_HOURS * 3600), 300)
    scheduler.add_job(run_all_checks, "interval", seconds=interval,
                      id="price_checks", replace_existing=True)
    scheduler.start()
    log.info("Ajastin käynnissä, väli %.1f h. JS-renderöinti: %s. MQTT: %s.",
             config.CHECK_INTERVAL_HOURS,
             "kyllä" if scraper.playwright_available() else "ei",
             "kyllä" if config.MQTT_ENABLED else "ei")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Hintavahti", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def watcher_dict(w: Watcher) -> dict:
    return {"id": w.id, "name": w.name, "email": w.email}


def product_dict(p: Product, include_history: bool = False) -> dict:
    data = {
        "id": p.id, "watcher_id": p.watcher_id, "name": p.name, "url": p.url,
        "css_selector": p.css_selector, "use_js": p.use_js,
        "target_price": p.target_price, "last_price": p.last_price,
        "lowest_price": p.lowest_price,
        "last_checked": iso_utc(p.last_checked),
        "last_error": p.last_error,
    }
    if include_history:
        data["history"] = [
            {"price": pt.price, "checked_at": iso_utc(pt.checked_at)}
            for pt in p.history
        ]
    return data


class WatcherIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=255)


class ProductIn(BaseModel):
    watcher_id: int
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    css_selector: str = Field(default="", max_length=255)
    use_js: bool = False
    target_price: float | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    css_selector: str | None = Field(default=None, max_length=255)
    use_js: bool | None = None
    target_price: float | None = None


class TestEmailIn(BaseModel):
    email: str = Field(min_length=1, max_length=255)


# --- Watchers ---
@app.get("/api/watchers")
def list_watchers(db: Session = Depends(get_db)):
    return [watcher_dict(w) for w in db.query(Watcher).order_by(Watcher.id).all()]


@app.post("/api/watchers", status_code=201)
def create_watcher(body: WatcherIn, db: Session = Depends(get_db)):
    w = Watcher(name=body.name.strip(), email=body.email.strip())
    db.add(w)
    db.commit()
    return watcher_dict(w)


@app.put("/api/watchers/{watcher_id}")
def update_watcher(watcher_id: int, body: WatcherIn, db: Session = Depends(get_db)):
    w = db.get(Watcher, watcher_id)
    if not w:
        raise HTTPException(404, "Välilehteä ei löytynyt")
    w.name, w.email = body.name.strip(), body.email.strip()
    db.commit()
    return watcher_dict(w)


@app.delete("/api/watchers/{watcher_id}", status_code=204)
def delete_watcher(watcher_id: int, db: Session = Depends(get_db)):
    w = db.get(Watcher, watcher_id)
    if not w:
        raise HTTPException(404, "Välilehteä ei löytynyt")
    for product in list(w.products):
        ha_mqtt.remove_product(product.id)
    db.delete(w)
    db.commit()


# --- Products ---
@app.get("/api/watchers/{watcher_id}/products")
def list_products(watcher_id: int, db: Session = Depends(get_db)):
    w = db.get(Watcher, watcher_id)
    if not w:
        raise HTTPException(404, "Välilehteä ei löytynyt")
    return [product_dict(p, include_history=True) for p in w.products]


@app.post("/api/products", status_code=201)
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    if not db.get(Watcher, body.watcher_id):
        raise HTTPException(404, "Välilehteä ei löytynyt")
    p = Product(
        watcher_id=body.watcher_id, name=body.name.strip(), url=body.url.strip(),
        css_selector=body.css_selector.strip(), use_js=body.use_js,
        target_price=body.target_price,
    )
    db.add(p)
    db.commit()
    try:
        check_product(db, p)
    except Exception:  # noqa: BLE001
        log.exception("Ensitarkistus epäonnistui tuotteelle %s", p.id)
    db.refresh(p)
    return product_dict(p, include_history=True)


@app.put("/api/products/{product_id}")
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Tuotetta ei löytynyt")
    if body.name is not None:
        p.name = body.name.strip()
    if body.url is not None:
        p.url = body.url.strip()
    if body.css_selector is not None:
        p.css_selector = body.css_selector.strip()
    if body.use_js is not None:
        p.use_js = body.use_js
    # Edit form always sends target_price (null clears it).
    p.target_price = body.target_price
    db.commit()
    ha_mqtt.publish_product(p)
    return product_dict(p, include_history=True)


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Tuotetta ei löytynyt")
    ha_mqtt.remove_product(p.id)
    db.delete(p)
    db.commit()


@app.post("/api/products/{product_id}/check")
@limiter.limit("1/30seconds")
def check_now(request: Request, product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Tuotetta ei löytynyt")
    result = check_product(db, p)
    db.refresh(p)
    return {"result": result, "product": product_dict(p, include_history=True)}


# --- Sensors (for REST-sensor users without MQTT) ---
@app.get("/api/sensors")
def sensors(db: Session = Depends(get_db)):
    """Flat list of all tracked products and their prices."""
    out = []
    for p in db.query(Product).all():
        out.append({
            "id": p.id, "name": p.name, "price": p.last_price,
            "lowest_price": p.lowest_price, "target_price": p.target_price,
            "url": p.url,
            "last_checked": iso_utc(p.last_checked),
            "error": p.last_error,
        })
    return out


# --- App config + email test ---
@app.get("/api/config")
def get_app_config():
    return {
        "timezone": config.DISPLAY_TIMEZONE,
        "smtp_configured": bool(config.SMTP_HOST),
    }


@app.post("/api/test-email")
def test_email(body: TestEmailIn):
    if not config.SMTP_HOST:
        raise HTTPException(400, "SMTP-palvelinta ei ole määritetty add-onin asetuksissa.")
    ok, message = notifier.send_test_email(body.email.strip())
    if not ok:
        raise HTTPException(502, f"Lähetys epäonnistui: {message}")
    return {"ok": True, "message": f"Testiviesti lähetetty osoitteeseen {body.email.strip()}."}


# --- Frontend ---
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
