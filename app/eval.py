"""
Evaluation pipeline — Ingredient presence & RAG vs Baseline overlap.

For each test case, calls retrieve() + generate() from app.rag, then checks
whether each user-facing ingredient term appears in the generated text.
Additionally generates a baseline (no RAG context) and compares how many
complementary ingredients from the reference recipes appear in each version.

Usage:
    python -m app.eval
"""

import json
from pathlib import Path

from app.rag import load_recipes, retrieve, generate, generate_without_context, INGREDIENTS_MAP_PATH, INGREDIENTS_DISPLAY_PATH

# ---------------------------------------------------------------------------
# Test cases: list of display terms (what the user clicked in the UI).
# Canonical terms for retrieval are derived automatically from ingredients_display.json.
# ---------------------------------------------------------------------------

TEST_CASES = [
    ["fregola", "vodka", "saucisse", "tomate confite"],
    ["butternut", "tortilla", "brousse", "poivre de Timut"],
    ["noisette", "figues", "miel d'acacia", "vinaigre balsamique", "pois chiche"],
    ["framboise", "cream cheese", "citron vert", "praliné noisette"],
    ["crevette", "lait de coco", "coriandre", "piment rouge"],
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_display_to_canonical(path: Path = INGREDIENTS_DISPLAY_PATH) -> dict[str, str]:
    """Build a reverse map: display term → canonical, from ingredients_display.json."""
    with open(path, encoding="utf-8") as f:
        display_map = json.load(f)
    reverse: dict[str, str] = {}
    for canonical, variants in display_map.items():
        reverse[canonical] = canonical
        for v in variants:
            reverse[v] = canonical
    return reverse


def load_variants_map(path: Path = INGREDIENTS_MAP_PATH) -> dict[str, list[str]]:
    """Load ingredients_map.json: canonical -> list of variant strings."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pluralize(term: str) -> str:
    """Return the French plural of a (possibly multi-word) ingredient term.

    Rules applied per word:
      - already ends in s/x/z → unchanged
      - ends in eau           → + x  (poireau → poireaux)
      - otherwise             → + s  (tomate confite → tomates confites)
    """
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


def check_ingredient(term: str, text: str, variants_map: dict[str, list[str]]) -> str | None:
    """Check if *term* (or one of its known variants, including plurals) appears in *text*.

    Returns the matched form if found, None otherwise.
    """
    text_lower = text.lower()

    # 1. Direct match on the user-facing term, then plural fallback
    if term.lower() in text_lower or _pluralize(term.lower()) in text_lower:
        return term

    # 2. Check all variants from the map (term may be a canonical key)
    for variant in variants_map.get(term, []):
        if variant.lower() in text_lower or _pluralize(variant.lower()) in text_lower:
            return variant

    return None


def extract_complementary(matched_recipes: list[dict], canonical_terms: list[str]) -> set[str]:
    """Collect all normalized ingredients from matched recipes, minus the stars."""
    stars = {s.lower() for s in canonical_terms}
    complementary: set[str] = set()
    for r in matched_recipes:
        for ing in r["extracted"].get("ingredients_normalises", []):
            if ing.lower() not in stars:
                complementary.add(ing)
    return complementary


def compute_overlap(text: str, complementary: set[str], variants_map: dict[str, list[str]]) -> tuple[int, int]:
    """Count how many complementary ingredients appear in text. Returns (found, total)."""
    found = 0
    for ing in complementary:
        if check_ingredient(ing, text, variants_map) is not None:
            found += 1
    return found, len(complementary)


# ---------------------------------------------------------------------------
# Eval runner
# ---------------------------------------------------------------------------

def run_eval() -> None:
    recipes = load_recipes()
    variants_map = load_variants_map()
    display_to_canonical = load_display_to_canonical()

    total_ingredients = 0
    total_found = 0
    cases_perfect = 0

    rag_overlap_sum = 0.0
    baseline_overlap_sum = 0.0
    overlap_cases = 0

    for idx, display_terms in enumerate(TEST_CASES, 1):
        canonical_terms = list(dict.fromkeys(
            display_to_canonical.get(t, t) for t in display_terms
        ))
        print(f"\n=== Cas {idx} : {', '.join(display_terms)} ===")
        print(f"  Canoniques : {', '.join(canonical_terms)}")

        matched = retrieve(recipes, canonical_terms)
        print(f"  Recettes récupérées : {len(matched)}")

        if not matched:
            print("  ⚠ Aucune recette trouvée — génération ignorée")
            total_ingredients += len(display_terms)
            continue

        generated = generate(display_terms, matched)

        case_found = 0
        for term in display_terms:
            match = check_ingredient(term, generated, variants_map)
            total_ingredients += 1
            if match:
                total_found += 1
                case_found += 1
                if match == term:
                    print(f"  ✓ {term}")
                else:
                    print(f"  ✓ {term}  (trouvé : \"{match}\")")
            else:
                print(f"  ✗ {term}  (non trouvé)")

        print(f"  Score : {case_found}/{len(display_terms)}")
        if case_found == len(display_terms):
            cases_perfect += 1

        # --- RAG vs Baseline ---
        complementary = extract_complementary(matched, canonical_terms)
        if complementary:
            baseline = generate_without_context(display_terms)

            rag_found, comp_total = compute_overlap(generated, complementary, variants_map)
            base_found, _ = compute_overlap(baseline, complementary, variants_map)

            rag_pct = rag_found / comp_total * 100
            base_pct = base_found / comp_total * 100
            delta = rag_pct - base_pct

            rag_overlap_sum += rag_pct
            baseline_overlap_sum += base_pct
            overlap_cases += 1

            print(f"  --- RAG vs Baseline ---")
            print(f"  Ingrédients complémentaires disponibles : {comp_total}")
            print(f"  RAG : {rag_found}/{comp_total} ({rag_pct:.1f}%)"
                  f"    Baseline : {base_found}/{comp_total} ({base_pct:.1f}%)"
                  f"    Delta : {delta:+.1f}%")

    # --- Global report ---
    pct_ingredients = (total_found / total_ingredients * 100) if total_ingredients else 0

    print(f"\n{'=' * 40}")
    print("=== RÉSULTAT GLOBAL ===")
    print(f"  Cas réussis (100%) : {cases_perfect}/{len(TEST_CASES)}")
    print(f"  Ingrédients trouvés : {total_found}/{total_ingredients} ({pct_ingredients:.1f}%)")

    if overlap_cases:
        avg_rag = rag_overlap_sum / overlap_cases
        avg_base = baseline_overlap_sum / overlap_cases
        print(f"  RAG overlap moyen : {avg_rag:.1f}%"
              f"    Baseline moyen : {avg_base:.1f}%"
              f"    Delta : {avg_rag - avg_base:+.1f}%")

    print(f"{'=' * 40}")


def main():
    run_eval()


if __name__ == "__main__":
    main()
