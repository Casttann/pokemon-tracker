import io
import os
from flask import Flask, jsonify, request, render_template, send_file
from database import db, init_db, get_all_cards, get_card_by_id, add_card, \
    update_card_status, delete_card, get_price_history, get_pokemon_list, \
    get_monthly_plans, upsert_monthly_plan, get_album_cards, set_album_order

MAX_PRICE = 100.0


def create_app(testing=False):
    app = Flask(__name__)
    db_path = os.environ.get("POKEMON_DB_PATH",
                             os.path.expanduser("~/.pokemon_tracker/tracker.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing
    # Evita que el navegador cachee JS/CSS estáticos: en desarrollo local
    # queremos ver los cambios siempre, sin tener que limpiar caché.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    db.init_app(app)

    with app.app_context():
        init_db()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/pokemon")
    def api_pokemon():
        return jsonify(get_pokemon_list())

    @app.route("/api/cards", methods=["GET"])
    def api_get_cards():
        status = request.args.get("status")
        return jsonify(get_all_cards(status=status))

    @app.route("/api/cards", methods=["POST"])
    def api_add_card():
        data = request.get_json()
        url = data.get("cardmarket_url", "")
        allowed_prefixes = ("https://www.cardmarket.com/",
                            "https://prices.pokemontcg.io/")
        if not url.startswith(allowed_prefixes):
            return jsonify({"error": "URL must be a CardMarket or PokemonTCG price URL"}), 400
        price = data.get("price")
        if not isinstance(price, (int, float)) or price <= 0 or price > MAX_PRICE:
            return jsonify({"error": f"Price must be a positive number <= {MAX_PRICE}"}), 400
        card_id = add_card(
            pokemon_id=data["pokemon_id"],
            card_name=data["card_name"],
            set_name=data["set_name"],
            rarity=data["rarity"],
            image_url=data.get("image_url"),
            price=float(price),
            cardmarket_url=url,
        )
        return jsonify({"id": card_id}), 201

    @app.route("/api/cards/<int:card_id>", methods=["PATCH"])
    def api_update_card(card_id):
        data = request.get_json()
        new_status = data.get("status")
        if new_status not in ("wishlist", "owned"):
            return jsonify({"error": "status must be 'wishlist' or 'owned'"}), 400
        card = get_card_by_id(card_id)
        if not card:
            return jsonify({"error": "Card not found"}), 404
        update_card_status(card_id, new_status)
        return jsonify(get_card_by_id(card_id))

    @app.route("/api/cards/<int:card_id>", methods=["DELETE"])
    def api_delete_card(card_id):
        delete_card(card_id)
        return "", 204

    @app.route("/api/cards/<int:card_id>/history")
    def api_card_history(card_id):
        return jsonify(get_price_history(card_id))

    @app.route("/api/search", methods=["POST"])
    def api_search():
        from scraper import search_cardmarket
        data = request.get_json()
        pokemon_name = data.get("pokemon_name", "")
        results = search_cardmarket(pokemon_name, max_price=MAX_PRICE)
        return jsonify(results)

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        from scheduler import trigger_refresh, is_updating
        if is_updating():
            return jsonify({"status": "already_running"})
        trigger_refresh(app)
        return jsonify({"status": "started"})

    @app.route("/api/seed", methods=["POST"])
    def api_seed():
        from seeder import start_seed, is_seeding
        if is_seeding():
            return jsonify({"status": "already_running"})
        start_seed(app)
        return jsonify({"status": "started"})

    @app.route("/api/plan", methods=["GET"])
    def api_get_plan():
        try:
            year = int(request.args.get("year", 2026))
        except (TypeError, ValueError):
            return jsonify({"error": "year must be an integer"}), 400
        return jsonify(get_monthly_plans(year))

    @app.route("/api/plan", methods=["POST"])
    def api_save_plan():
        data = request.get_json()
        try:
            year = int(data["year"])
            month = int(data["month"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "year and month are required integers"}), 400
        if month < 1 or month > 12:
            return jsonify({"error": "month must be 1-12"}), 400
        budget = data.get("budget", 80.0)
        spent = data.get("spent", 0.0)
        if not isinstance(budget, (int, float)) or budget < 0:
            return jsonify({"error": "budget must be a non-negative number"}), 400
        if not isinstance(spent, (int, float)) or spent < 0:
            return jsonify({"error": "spent must be a non-negative number"}), 400
        plan_note = data.get("plan_note", "")
        upsert_monthly_plan(year, month, float(budget), plan_note, float(spent))
        return jsonify(get_monthly_plans(year))

    @app.route("/api/album", methods=["GET"])
    def api_get_album():
        return jsonify(get_album_cards())

    @app.route("/api/album", methods=["PUT"])
    def api_set_album():
        data = request.get_json()
        order = data.get("order")
        if not isinstance(order, list) or not all(isinstance(i, int) for i in order):
            return jsonify({"error": "order must be a list of card ids"}), 400
        return jsonify(set_album_order(order))

    @app.route("/api/stats")
    def api_stats():
        from stats import get_dashboard_stats
        return jsonify(get_dashboard_stats())

    @app.route("/api/export/xlsx")
    def api_export_xlsx():
        from exporters import build_xlsx
        data = build_xlsx(get_all_cards())
        return send_file(
            io.BytesIO(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="pokedex_tracker.xlsx",
        )

    @app.route("/api/export/pdf")
    def api_export_pdf():
        from exporters import build_pdf
        data = build_pdf(get_all_cards())
        return send_file(
            io.BytesIO(data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="pokedex_tracker.pdf",
        )

    @app.route("/api/status")
    def api_status():
        from scheduler import get_last_update, is_updating
        from seeder import is_seeding
        return jsonify({
            "last_update": get_last_update(),
            "updating": is_updating(),
            "seeding": is_seeding(),
        })

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        from ai_assistant import chat, AssistantError
        data = request.get_json() or {}
        history = data.get("history")
        if not isinstance(history, list) or not history:
            return jsonify({"error": "history must be a non-empty list"}), 400
        for m in history:
            if not isinstance(m, dict) or m.get("role") not in ("user", "assistant") \
               or not isinstance(m.get("content"), str):
                return jsonify({"error": "each message needs role (user/assistant) and content (string)"}), 400
        try:
            reply, mutated = chat(history)
        except AssistantError as exc:
            return jsonify({"error": str(exc)}), 500
        except Exception as exc:  # noqa: BLE001 - surface upstream API errors to the UI
            return jsonify({"error": f"Error del asistente: {exc}"}), 502
        return jsonify({"reply": reply, "mutated": mutated})

    return app


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    application = create_app()
    if not application.config.get("TESTING"):
        from scheduler import start_scheduler
        start_scheduler(application)
    # host=0.0.0.0 para poder acceder desde el móvil en la misma red WiFi
    # (p.ej. http://192.168.1.38:5000) e instalarla como PWA.
    application.run(host="0.0.0.0", port=port, debug=False)
