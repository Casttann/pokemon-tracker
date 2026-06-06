from database import Card, PriceHistory


def get_dashboard_stats():
    """Aggregate portfolio statistics for the investment dashboard."""
    cards = Card.query.all()

    owned = [c for c in cards if c.status == "owned"]
    wishlist = [c for c in cards if c.status == "wishlist"]

    owned_value = sum(c.price_current or 0 for c in owned)
    wishlist_value = sum(c.price_current or 0 for c in wishlist)

    return {
        "totals": {
            "owned_count": len(owned),
            "wishlist_count": len(wishlist),
            "owned_value": round(owned_value, 2),
            "wishlist_value": round(wishlist_value, 2),
        },
        "value_over_time": _value_over_time(owned),
        "by_generation": _by_generation(owned),
        "by_rarity": _by_rarity(owned),
        "top_movers": _top_movers(owned),
    }


def _value_over_time(owned):
    """Portfolio value of owned cards per date, carrying forward last known price."""
    if not owned:
        return []
    owned_ids = {c.id for c in owned}
    rows = PriceHistory.query.filter(PriceHistory.card_id.in_(owned_ids))\
        .order_by(PriceHistory.recorded.asc()).all()
    if not rows:
        return []

    # All distinct dates (day granularity)
    dates = sorted({r.recorded[:10] for r in rows})
    # history per card sorted asc
    per_card = {}
    for r in rows:
        per_card.setdefault(r.card_id, []).append((r.recorded[:10], r.price))

    series = []
    for d in dates:
        total = 0.0
        for cid, hist in per_card.items():
            last_price = None
            for hd, price in hist:
                if hd <= d:
                    last_price = price
                else:
                    break
            if last_price is not None:
                total += last_price
        series.append({"date": d, "value": round(total, 2)})
    return series


def _by_generation(owned):
    gens = {}
    for c in owned:
        gen = c.pokemon.generation
        gens.setdefault(gen, 0.0)
        gens[gen] += c.price_current or 0
    return [{"generation": g, "value": round(v, 2)}
            for g, v in sorted(gens.items())]


def _by_rarity(owned):
    rarities = {}
    for c in owned:
        rarities.setdefault(c.rarity, 0)
        rarities[c.rarity] += 1
    return [{"rarity": r, "count": n}
            for r, n in sorted(rarities.items(), key=lambda x: -x[1])]


def _top_movers(owned):
    """Biggest % change between first and latest recorded price per owned card."""
    movers = []
    for c in owned:
        hist = sorted(c.history, key=lambda h: h.recorded)
        if len(hist) < 2:
            continue
        first = hist[0].price
        latest = hist[-1].price
        if first <= 0:
            continue
        pct = (latest - first) / first * 100
        movers.append({
            "card_name": c.card_name,
            "pokemon_name": c.pokemon.name,
            "set_name": c.set_name,
            "first_price": round(first, 2),
            "latest_price": round(latest, 2),
            "change_pct": round(pct, 1),
        })
    movers.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
    return movers[:10]
