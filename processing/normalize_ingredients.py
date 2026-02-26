"""
Post-process extracted recipes: normalize ingredient names using ingredients_map.json,
and save the result to data/recipes_normalized.json.

Reads individual recipe files from data/extracted/.

Usage:
  python -m processing.normalize_ingredients
"""

import json
from pathlib import Path

INGREDIENTS_MAP_PATH = Path(__file__).resolve().parent / "ingredients_map.json"
EXTRACTED_DIR = Path(__file__).resolve().parent.parent / "data" / "extracted"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes_normalized.json"


def load_ingredients_map(path: Path = INGREDIENTS_MAP_PATH) -> dict[str, str]:
    """Load the grouped map and flatten it to variant -> canonical."""
    with open(path, encoding="utf-8") as f:
        grouped = json.load(f)

    variant_to_canonical: dict[str, str] = {}
    for canonical, variants in grouped.items():
        variant_to_canonical[canonical] = canonical
        for v in variants:
            variant_to_canonical[v] = canonical
    return variant_to_canonical


def load_extracted_recipes(extracted_dir: Path = EXTRACTED_DIR) -> list[dict]:
    """Load all individual recipe JSON files from the extracted directory."""
    recipes = []
    for filepath in sorted(extracted_dir.glob("*.json")):
        with open(filepath, encoding="utf-8") as f:
            recipes.append(json.load(f))
    return recipes


def normalize_recipe(recipe: dict, variant_to_canonical: dict[str, str]) -> dict:
    """Normalize ingredients_normalises in a recipe's extracted data."""
    extracted = recipe.get("extracted", {})
    raw_ingredients = extracted.get("ingredients_normalises", [])

    normalized = []
    for ing in raw_ingredients:
        clean = ing.strip().lower()
        canonical = variant_to_canonical.get(clean, clean)
        if canonical not in normalized:
            normalized.append(canonical)

    recipe = {**recipe}
    recipe["extracted"] = {**extracted, "ingredients_normalises": normalized}
    return recipe


def main():
    variant_to_canonical = load_ingredients_map()
    print(f"Loaded {len(variant_to_canonical)} ingredient mappings")

    recipes = load_extracted_recipes()
    print(f"Loaded {len(recipes)} extracted recipes")

    normalized = [normalize_recipe(r, variant_to_canonical) for r in recipes]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print(f"Normalized {len(normalized)} recipes -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
