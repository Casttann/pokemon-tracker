from pokemon_data import POKEMON_LIST

def test_total_count():
    assert len(POKEMON_LIST) == 92

def test_required_fields():
    for p in POKEMON_LIST:
        assert "name" in p
        assert "generation" in p
        assert "type_1" in p

def test_special_group_generation():
    special_names = {"Pikachu", "Raichu", "Eevee", "Vaporeon", "Jolteon",
                     "Flareon", "Espeon", "Umbreon", "Leafeon", "Glaceon", "Sylveon"}
    specials = [p for p in POKEMON_LIST if p["name"] in special_names]
    assert len(specials) == 11
    for p in specials:
        assert p["generation"] == 0

def test_gen1_starters_present():
    names = [p["name"] for p in POKEMON_LIST]
    for name in ["Bulbasaur", "Ivysaur", "Venusaur",
                 "Charmander", "Charmeleon", "Charizard",
                 "Squirtle", "Wartortle", "Blastoise"]:
        assert name in names

def test_eevee_evolutions_present():
    names = [p["name"] for p in POKEMON_LIST]
    for name in ["Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon",
                 "Leafeon", "Glaceon", "Sylveon"]:
        assert name in names
