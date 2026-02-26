"""
Build/update ingredients_map.json from all extracted recipes.

Scans data/extracted/ for all ingredients_normalises values, merges them
into the existing map (preserving manually curated variant mappings),
and adds any new ingredients as new canonical entries.

Usage:
  python -m processing.build_ingredients_map
"""

import json
from pathlib import Path

EXTRACTED_DIR = Path(__file__).resolve().parent.parent / "data" / "extracted"
INGREDIENTS_MAP_PATH = Path(__file__).resolve().parent / "ingredients_map.json"


def load_existing_map(path: Path) -> dict[str, list[str]]:
    """Load the current ingredients map, or return empty dict if missing."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_ingredients(extracted_dir: Path) -> set[str]:
    """Collect all unique normalized ingredient names from extracted recipes."""
    all_ingredients: set[str] = set()
    for filepath in sorted(extracted_dir.glob("*.json")):
        with open(filepath, encoding="utf-8") as f:
            recipe = json.load(f)
        extracted = recipe.get("extracted", {})
        if not extracted.get("est_une_recette", False):
            continue
        for ing in extracted.get("ingredients_normalises", []):
            clean = ing.strip().lower()
            if clean:
                all_ingredients.add(clean)
    return all_ingredients


def build_known_set(ingredients_map: dict[str, list[str]]) -> set[str]:
    """Return the set of all known names (canonical + variants)."""
    known: set[str] = set()
    for canonical, variants in ingredients_map.items():
        known.add(canonical)
        for v in variants:
            known.add(v)
    return known


def main():
    existing_map = load_existing_map(INGREDIENTS_MAP_PATH)
    print(f"Existing map: {len(existing_map)} canonical ingredients")

    all_ingredients = collect_ingredients(EXTRACTED_DIR)
    print(f"Found {len(all_ingredients)} unique ingredients in extracted recipes")

    known = build_known_set(existing_map)
    new_ingredients = sorted(all_ingredients - known)

    if not new_ingredients:
        print("No new ingredients to add.")
        return

    print(f"\n{len(new_ingredients)} new ingredients to add:")
    for ing in new_ingredients:
        print(f"  + {ing}")
        existing_map[ing] = []

    # Sort the map alphabetically
    sorted_map = dict(sorted(existing_map.items()))

    with open(INGREDIENTS_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_map, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\nUpdated {INGREDIENTS_MAP_PATH}: {len(sorted_map)} canonical ingredients")


if __name__ == "__main__":
    main()
