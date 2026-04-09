"""
Evaluation — two tests for the RAG pipeline.

1. Ingredient presence  : do all chosen ingredients appear in the generated recipe?
2. Context usage        : complementary ingredient overlap across 4 generation conditions
                          (Rec + Ing / recipes only / ingredients map only / neither)

Usage:
    python -m app.eval
"""

from app.rag import load_recipes, load_ingredients_data, retrieve, generate

# ---------------------------------------------------------------------------
# Test cases — normalized keys from ingredients_map.json
# ---------------------------------------------------------------------------

TEST_CASES = [
    ["navet", "carotte", "poireau"],
    ["butternut", "ricotta", "poivre"],
    ["tomate", "nectarine"]
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pluralize(term: str) -> str:
    words = term.split()
    pluralized = []
    for w in words:
        if w[-1] in "sxz":
            pluralized.append(w)
        elif w.endswith("eau"):
            pluralized.append(w + "x")
        else:
            pluralized.append(w + "s")
    return " ".join(pluralized)


def check_ingredient(term: str, text: str) -> bool:
    """Return True if term (including French plural) appears in text."""
    text_lower = text.lower()
    return term.lower() in text_lower or _pluralize(term.lower()) in text_lower


def extract_complementary(matched_recipes: list[dict], chosen: list[str]) -> set[str]:
    """All normalized ingredients in matched recipes, excluding the chosen ones."""
    stars = set(chosen)
    return {
        ing
        for r in matched_recipes
        for ing in r.get("ingredients_normalises", [])
        if ing not in stars
    }


def complementary_overlap(text: str, complementary: set[str]) -> float:
    """Fraction of complementary ingredients that appear in text."""
    if not complementary:
        return 0.0
    found = sum(1 for ing in complementary if check_ingredient(ing, text))
    return found / len(complementary)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ingredient_presence(recipes: list[dict], ingredients_data: dict) -> None:
    """Check that all chosen ingredients appear in the generated recipe."""
    print("\n=== TEST 1 : Présence des ingrédients choisis ===")
    total, found_total, perfect = 0, 0, 0

    for chosen in TEST_CASES:
        matched = retrieve(recipes, chosen, ingredients_data)
        if not matched:
            print(f"  ⚠ Pas de recettes pour {chosen} — ignoré")
            continue

        generated = generate(chosen, matched, ingredients_data)
        case_found = sum(1 for t in chosen if check_ingredient(t, generated))
        total += len(chosen)
        found_total += case_found
        ok = case_found == len(chosen)
        perfect += int(ok)
        print(f"  {'✓' if ok else '✗'} {', '.join(chosen)}  →  {case_found}/{len(chosen)}")

    print(f"\n  Total : {found_total}/{total} — cas parfaits : {perfect}/{len(TEST_CASES)}")


def test_context_usage(recipes: list[dict], ingredients_data: dict) -> None:
    """Compare complementary ingredient overlap across 4 generation conditions."""
    print("\n=== TEST 2 : Utilisation du contexte ===")
    header = f"  {'Cas':<38} {'Rec+Ing':>8} {'Rec':>6} {'Ing':>6} {'Aucun':>7}"
    print(header)
    print(f"  {'-' * (len(header) - 2)}")

    for chosen in TEST_CASES:
        matched = retrieve(recipes, chosen, ingredients_data)
        if not matched:
            print(f"  ⚠ Pas de recettes pour {chosen} — ignoré")
            continue

        complementary = extract_complementary(matched, chosen)
        if not complementary:
            continue

        full         = generate(chosen, matched, ingredients_data)
        recipes_only = generate(chosen, matched, {})
        map_only     = generate(chosen, [], ingredients_data)
        neither      = generate(chosen, [], {})

        label = ", ".join(chosen[:2]) + ("…" if len(chosen) > 2 else "")
        print(
            f"  {label:<38}"
            f" {complementary_overlap(full, complementary):>8.1%}"
            f" {complementary_overlap(recipes_only, complementary):>6.1%}"
            f" {complementary_overlap(map_only, complementary):>6.1%}"
            f" {complementary_overlap(neither, complementary):>7.1%}"
        )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Chargement des données...")
    recipes = load_recipes()
    ingredients_data = load_ingredients_data()

    test_ingredient_presence(recipes, ingredients_data)
    test_context_usage(recipes, ingredients_data)

    print("\nTerminé.")


if __name__ == "__main__":
    main()
