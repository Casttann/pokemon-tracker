import os
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = BackgroundScheduler()
_updating = False


def is_updating() -> bool:
    return _updating


def _run_price_update(app):
    global _updating
    _updating = True
    try:
        with app.app_context():
            from database import get_all_cards, save_price_snapshot
            from scraper import update_price
            cards = get_all_cards()
            for card in cards:
                if not card.get("cardmarket_url"):
                    continue
                price = update_price(card["cardmarket_url"])
                if price is not None:
                    save_price_snapshot(card["id"], price)
            _write_last_update()
    finally:
        _updating = False


def _write_last_update():
    path = os.path.expanduser("~/.pokemon_tracker/last_update.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def get_last_update() -> str | None:
    path = os.path.expanduser("~/.pokemon_tracker/last_update.txt")
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _needs_update() -> bool:
    last = get_last_update()
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now(timezone.utc) - last_dt > timedelta(hours=24)
    except ValueError:
        return True


def start_scheduler(app):
    _scheduler.add_job(
        _run_price_update, "cron", hour=9, minute=0, args=[app]
    )
    _scheduler.start()
    if _needs_update():
        import threading
        t = threading.Thread(target=_run_price_update, args=[app], daemon=True)
        t.start()


def trigger_refresh(app):
    """Manually trigger a price update. Returns False if already running."""
    global _updating
    if _updating:
        return False
    import threading
    t = threading.Thread(target=_run_price_update, args=[app], daemon=True)
    t.start()
    return True
