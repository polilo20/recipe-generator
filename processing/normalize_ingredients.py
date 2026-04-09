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
    """Load the grouped map and flatten it to variant -> normalized."""
    with open(path, encoding="utf-8") as f:
        grouped = json.load(f)

    variant_to_normalized: dict[str, str] = {}
    for normalized_name, data in grouped.items():
        variant_to_normalized[normalized_name] = normalized_name
        for v in data.get("normalizing", []):
            variant_to_normalized[v] = normalized_name
    return variant_to_normalized


def load_extracted_recipes(extracted_dir: Path = EXTRACTED_DIR) -> list[dict]:
    """Load all individual recipe JSON files from the extracted directory."""
    recipes = []
    for filepath in sorted(extracted_dir.glob("*.json")):
        with open(filepath, encoding="utf-8") as f:
            recipes.append(json.load(f))
    return recipes


def normalize_recipe(recipe: dict, variant_to_normalized: dict[str, str]) -> dict:
    """Normalize ingredients_normalises and store it at the top level of the recipe."""
    extracted = recipe.get("extracted", {})
    raw_ingredients = extracted.get("ingredients_normalises", [])

    normalized = []
    for ing in raw_ingredients:
        clean = ing.strip().lower()
        normalized_name = variant_to_normalized.get(clean, clean)
        if normalized_name not in normalized:
            normalized.append(normalized_name)

    recipe = {**recipe, "ingredients_normalises": normalized}
    return recipe


def main():
    variant_to_normalized = load_ingredients_map()
    print(f"Loaded {len(variant_to_normalized)} ingredient mappings")

    recipes = load_extracted_recipes()
    print(f"Loaded {len(recipes)} extracted recipes")

    normalized = [normalize_recipe(r, variant_to_normalized) for r in recipes]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print(f"Normalized {len(normalized)} recipes -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
