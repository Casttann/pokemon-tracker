"""Asistente de IA con function-calling para el Pokédex Tracker.

Usa un endpoint compatible con OpenAI (ChatLLM / Abacus.AI RouteLLM) para que
el usuario pueda pedir cosas en lenguaje natural ("añade un Charizard barato",
"quita esa carta del álbum", "¿cuánto vale mi colección?") y el modelo las
ejecute llamando a herramientas reales sobre la base de datos.

Todas las herramientas operan dentro del contexto de la petición Flask
(`db.session` ya está disponible porque /api/chat corre dentro de una
request), así que no hace falta abrir manualmente app_context aquí.
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("CHATLLM_MODEL", "route-llm")
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """Eres el asistente integrado en una app de seguimiento de \
colección de cartas Pokémon (estilo inversión: precios, wishlist vs colección, \
álbum visual). Hablas siempre en español, de forma breve, concreta y amistosa.

Puedes, usando las herramientas disponibles:
- Buscar Pokémon por nombre y listar cartas que ya tiene el usuario.
- Buscar cartas reales en el mercado (con precio y URL) para añadir.
- Añadir una carta a la wishlist, marcarla como comprada/owned, o borrarla.
- Ver y editar el álbum (qué cartas están colocadas y en qué orden).
- Consultar estadísticas de la colección (valor total, por generación, etc.).

Reglas importantes:
- NUNCA inventes precios, IDs, URLs ni números de carta/set: si necesitas datos \
  de una carta nueva, llama primero a search_cards_to_add para obtener \
  candidatos reales. Esa herramienta SOLO busca por nombre de Pokémon, no \
  acepta ni usa números de carta (p.ej. "070/094") ni códigos de set: NUNCA \
  le pidas esos datos al usuario, preséntale directamente la lista de \
  candidatos que te devuelva (nombre de set + rareza + precio) para que elija.
- Si search_cards_to_add devuelve más de una carta, SIEMPRE muestra la lista \
  al usuario (formato: "1. <nombre> – <set> – <rareza> – €X.XX", una por \
  línea) y pregunta cuál quiere ANTES de añadir nada. NUNCA elijas tú por el \
  usuario cuando haya varias opciones. La única excepción es que el usuario \
  ya haya indicado el set Y la rareza exactos (p.ej. "el Radiant Rare de \
  Astral Radiance") y solo encaje una carta de la lista.
- Para añadir una carta nueva necesitas el pokemon_id: usa search_pokemon si \
  no lo tienes.
- search_pokemon y search_cards_to_add son independientes: search_pokemon \
  busca en la Pokédex (nombres base, sin variantes como "Radiant", "Shiny", \
  "ex", "GX", "V", "BREAK"...), mientras que search_cards_to_add busca en el \
  mercado real y SÍ encuentra esas variantes. Si search_pokemon no encuentra \
  nada con el nombre completo que dio el usuario (p.ej. "Radiant Greninja"), \
  NO concluyas que la carta no existe: quita el calificativo y reintenta con \
  el nombre base (p.ej. "Greninja") en ambas herramientas. Solo dile al \
  usuario que no la encuentras si después de ese reintento sigue sin \
  aparecer en los resultados de search_cards_to_add.
- Sé proactivo: si el usuario pregunta algo abierto ("¿qué me conviene \
  comprar?"), consulta primero get_collection_stats y/o list_cards antes de \
  responder.
- Responde siempre en texto plano breve (no markdown salvo listas simples).
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_pokemon",
            "description": "Busca Pokémon por nombre (parcial, insensible a mayúsculas) "
                            "y devuelve su id, generación y tipos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre o parte del nombre del Pokémon"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_cards",
            "description": "Lista las cartas que el usuario ya tiene registradas (wishlist u owned), "
                            "opcionalmente filtradas por Pokémon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["wishlist", "owned"],
                               "description": "Filtra por estado; omite para ambos"},
                    "pokemon_name": {"type": "string", "description": "Filtra por nombre de Pokémon (parcial)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_cards_to_add",
            "description": "Busca cartas reales en el mercado (PokemonTCG/CardMarket) para un Pokémon, "
                            "con precio actual y URL. Úsalo SIEMPRE antes de añadir una carta nueva.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pokemon_name": {"type": "string", "description": "Nombre del Pokémon a buscar"},
                },
                "required": ["pokemon_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_card",
            "description": "Añade una carta nueva a la wishlist del usuario. Usa siempre datos reales "
                            "obtenidos antes con search_cards_to_add (card_name, set_name, rarity, "
                            "price, cardmarket_url, image_url) y el pokemon_id de search_pokemon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pokemon_id": {"type": "integer"},
                    "card_name": {"type": "string"},
                    "set_name": {"type": "string"},
                    "rarity": {"type": "string"},
                    "price": {"type": "number"},
                    "cardmarket_url": {"type": "string"},
                    "image_url": {"type": "string"},
                },
                "required": ["pokemon_id", "card_name", "set_name", "rarity", "price", "cardmarket_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_card_status",
            "description": "Cambia el estado de una carta entre 'wishlist' y 'owned' (marcarla como comprada o no).",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_id": {"type": "integer"},
                    "new_status": {"type": "string", "enum": ["wishlist", "owned"]},
                },
                "required": ["card_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_card",
            "description": "Elimina definitivamente una carta de la colección del usuario (wishlist u owned). "
                            "Si estaba en el álbum, también se quita de ahí.",
            "parameters": {
                "type": "object",
                "properties": {"card_id": {"type": "integer"}},
                "required": ["card_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_collection_stats",
            "description": "Devuelve estadísticas de inversión: valor total, por generación, por rareza, "
                            "y las cartas que más han subido/bajado de precio.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "album_get",
            "description": "Devuelve la secuencia actual de cartas colocadas en el álbum, en orden.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "album_set_order",
            "description": "Reescribe el álbum completo con la lista de IDs de carta dada, en ese orden "
                            "exacto. Las cartas no incluidas salen del álbum. Útil para insertar, quitar "
                            "o reordenar cartas del álbum: primero llama a album_get, modifica la lista en "
                            "tu razonamiento, y luego llama a esto con la lista final completa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["card_ids"],
            },
        },
    },
]


def _tool_search_pokemon(args):
    from database import get_pokemon_list
    name = (args.get("name") or "").lower()
    matches = [p for p in get_pokemon_list() if name in p["name"].lower()]
    return matches[:15]


def _tool_list_cards(args):
    from database import get_all_cards
    status = args.get("status")
    cards = get_all_cards(status=status if status in ("owned", "wishlist") else None)
    pokemon_name = args.get("pokemon_name")
    if pokemon_name:
        pn = pokemon_name.lower()
        cards = [c for c in cards if pn in c["pokemon_name"].lower()]
    return cards[:40]


def _tool_search_cards_to_add(args):
    from scraper import search_cardmarket
    results = search_cardmarket(args["pokemon_name"], max_price=100.0)
    return results[:10]


def _tool_add_card(args):
    from database import add_card
    price = float(args["price"])
    if price <= 0 or price > 100.0:
        return {"error": "price must be a positive number <= 100"}
    card_id = add_card(
        pokemon_id=int(args["pokemon_id"]),
        card_name=args["card_name"],
        set_name=args.get("set_name", ""),
        rarity=args.get("rarity", ""),
        image_url=args.get("image_url"),
        price=price,
        cardmarket_url=args["cardmarket_url"],
    )
    return {"id": card_id, "status": "added_to_wishlist"}


def _tool_update_card_status(args):
    from database import update_card_status, get_card_by_id
    card_id = int(args["card_id"])
    if not get_card_by_id(card_id):
        return {"error": "card not found"}
    update_card_status(card_id, args["new_status"])
    return get_card_by_id(card_id)


def _tool_remove_card(args):
    from database import delete_card, get_card_by_id
    card_id = int(args["card_id"])
    if not get_card_by_id(card_id):
        return {"error": "card not found"}
    delete_card(card_id)
    return {"status": "deleted", "id": card_id}


def _tool_get_collection_stats(_args):
    from stats import get_dashboard_stats
    return get_dashboard_stats()


def _tool_album_get(_args):
    from database import get_album_cards
    return get_album_cards()


def _tool_album_set_order(args):
    from database import set_album_order
    ids = [int(i) for i in args.get("card_ids", [])]
    return set_album_order(ids)


TOOL_IMPL = {
    "search_pokemon": _tool_search_pokemon,
    "list_cards": _tool_list_cards,
    "search_cards_to_add": _tool_search_cards_to_add,
    "add_card": _tool_add_card,
    "update_card_status": _tool_update_card_status,
    "remove_card": _tool_remove_card,
    "get_collection_stats": _tool_get_collection_stats,
    "album_get": _tool_album_get,
    "album_set_order": _tool_album_set_order,
}

# Herramientas que modifican datos: si alguna de éstas se ejecuta, el
# frontend debe refrescar cartas/álbum tras la respuesta.
MUTATING_TOOLS = {"add_card", "update_card_status", "remove_card", "album_set_order"}


class AssistantError(Exception):
    pass


def _get_client():
    from openai import OpenAI
    api_key = os.environ.get("CHATLLM_API_KEY")
    if not api_key:
        raise AssistantError("CHATLLM_API_KEY no está configurada (.env)")
    base_url = os.environ.get("CHATLLM_BASE_URL", "https://routellm.abacus.ai/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def chat(history):
    """history: lista de {role: 'user'|'assistant', content: str} (sin system).
    Devuelve (texto_respuesta, lista_de_herramientas_mutadoras_ejecutadas)."""
    client = _get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    mutated = []

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return msg.content or "", mutated

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = TOOL_IMPL.get(name)
            if impl is None:
                result = {"error": f"unknown tool '{name}'"}
            else:
                try:
                    result = impl(args)
                    if name in MUTATING_TOOLS and "error" not in (result or {}):
                        mutated.append(name)
                except Exception as exc:  # noqa: BLE001 - report back to the model
                    result = {"error": str(exc)}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str)[:6000],
            })

    return ("Se me han acumulado demasiados pasos seguidos; "
            "¿puedes reformular la petición más concreta?"), mutated
