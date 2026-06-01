import os
from flask import Flask, jsonify, request, render_template
from database import db, init_db, get_all_cards, get_card_by_id, add_card, \
    update_card_status, delete_card, get_price_history, get_pokemon_list

MAX_PRICE = 100.0


def create_app(testing=False):
    app = Flask(__name__)
    db_path = os.environ.get("POKEMON_DB_PATH",
                             os.path.expanduser("~/.pokemon_tracker/tracker.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing
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

    @app.route("/api/status")
    def api_status():
        from scheduler import get_last_update, is_updating
        from seeder import is_seeding
        return jsonify({
            "last_update": get_last_update(),
            "updating": is_updating(),
            "seeding": is_seeding(),
        })

    return app


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    application = create_app()
    if not application.config.get("TESTING"):
        from scheduler import start_scheduler
        start_scheduler(application)
    application.run(port=port, debug=False)
