"""
Preprocess scraped recipes to remove noise (comments, navigation, social buttons).
"""

import json
import re
from pathlib import Path


def clean_aufilduthym(content: str) -> str:
    """Remove noise from Au Fil du Thym recipes."""
    # Remove navigation header
    content = re.sub(r'^Accueil\n»\nBlog Archive\n»\n[^\n]+\n[^\n]+\n', '', content)

    # Remove comments section (starts with username + date pattern or "X Commentaires")
    # Comments typically start after recipe content with a commenter name and date
    content = re.sub(
        r'\n\d+\s+Commentaires?\n.*$',
        '',
        content,
        flags=re.DOTALL
    )
    # Alternative pattern: direct commenter names
    content = re.sub(
        r'\n[A-Z][a-zé\-]+\n\d{1,2}\s+\w+\s+\d{4}\s+à\s+\d{1,2}h\d{2}\n.*$',
        '',
        content,
        flags=re.DOTALL
    )
    # Remove "Joindre la conversation" and everything after
    content = re.sub(r'\nJoindre la conversation.*$', '', content, flags=re.DOTALL)

    # Remove social/print buttons
    content = re.sub(r'\nExport en PDF\nImprimer\n?', '\n', content)
    content = re.sub(r'\nÉtiquettes:.*?(?=\n[A-Z]|\n#|\Z)', '', content, flags=re.DOTALL)

    # Remove "précédent/suivant" navigation
    content = re.sub(r'\nprécédent\n.*?\nsuivant\n.*?(?=\n|$)', '', content, flags=re.DOTALL)

    return content.strip()


def clean_cestmafournee(content: str) -> str:
    """Remove noise from C'est ma fournée recipes."""
    # Remove sharing header
    content = re.sub(r'^Partager\nObtenir le lien\nFacebook\nX\nPinterest\nE-mail\nAutres applications\n', '', content)
    content = re.sub(r'\nLibellés\n[^\n]+\nPublié par\n[^\n]+\n[^\n]+\n', '\n', content)

    # Remove comments section - starts with "Commentaires" or first commenter
    content = re.sub(r'\nCommentaires\n.*$', '', content, flags=re.DOTALL)

    # Alternative: cut at first comment (name + date pattern from blogger)
    content = re.sub(
        r'\n[A-Za-zéèêëàâäùûüôöîïç\-\s]+\n\d{2}\s+\w+,\s+\d{4}\s+\d{2}:\d{2}\n.*$',
        '',
        content,
        flags=re.DOTALL
    )

    # Remove "Ajouter un commentaire" section
    content = re.sub(r'\nAjouter un commentaire.*$', '', content, flags=re.DOTALL)

    # Remove trailing share buttons
    content = re.sub(r'\nPartager\nObtenir le lien\nFacebook.*$', '', content, flags=re.DOTALL)
    content = re.sub(r"\nEnvoyer l'article par e-mail\n.*$", '', content, flags=re.DOTALL)

    return content.strip()


def clean_clemfoodie(content: str) -> str:
    """Remove noise from Clem Foodie recipes."""
    # Remove sharing section at end (note: "Partager :" with space before colon)
    content = re.sub(r'\nPartager\s*:\s*\n.*$', '', content, flags=re.DOTALL)

    # Remove "J'aime ça" section
    content = re.sub(r"\nJ'aime ça\s*:\s*\n.*$", '', content, flags=re.DOTALL)

    # Remove English version if present (keep French only)
    content = re.sub(r'\nCaramelized .*$', '', content, flags=re.DOTALL)
    content = re.sub(r'\n\{English version below\}', '', content)

    return content.strip()


def clean_generic(content: str) -> str:
    """Generic cleaning for unknown sources."""
    # Remove common social sharing patterns
    content = re.sub(r'\nPartager\s*:?\n.*$', '', content, flags=re.DOTALL)
    content = re.sub(r"\nJ'aime ça\s*:?\n.*$", '', content, flags=re.DOTALL)
    content = re.sub(r'\nCommentaires?\n.*$', '', content, flags=re.DOTALL)
    content = re.sub(r'\nJoindre la conversation.*$', '', content, flags=re.DOTALL)

    return content.strip()


def clean_recipe(recipe: dict) -> dict:
    """Clean a recipe based on its source."""
    source = recipe.get("source", "").lower()
    content = recipe.get("raw_content", "")

    if "fil du thym" in source:
        cleaned = clean_aufilduthym(content)
    elif "fournee" in source or "fournée" in source:
        cleaned = clean_cestmafournee(content)
    elif "clem" in source:
        cleaned = clean_clemfoodie(content)
    else:
        cleaned = clean_generic(content)

    return {
        **recipe,
        "cleaned_content": cleaned,
        "original_length": len(content),
        "cleaned_length": len(cleaned),
    }


def process_all_recipes(input_dir: Path, output_dir: Path):
    """Process all recipes in the input directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"total": 0, "processed": 0, "bytes_saved": 0}

    for recipe_file in input_dir.glob("*.json"):
        stats["total"] += 1

        with open(recipe_file, "r", encoding="utf-8") as f:
            recipe = json.load(f)

        cleaned = clean_recipe(recipe)
        stats["bytes_saved"] += cleaned["original_length"] - cleaned["cleaned_length"]
        stats["processed"] += 1

        output_file = output_dir / recipe_file.name
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

    return stats


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / "data" / "raw"
    output_dir = base_dir / "data" / "processed"

    print(f"Processing recipes from {input_dir}")
    stats = process_all_recipes(input_dir, output_dir)

    print(f"\nResults:")
    print(f"  Total files: {stats['total']}")
    print(f"  Processed: {stats['processed']}")
    print(f"  Bytes saved: {stats['bytes_saved']:,} ({stats['bytes_saved'] / 1024:.1f} KB)")
    print(f"  Average reduction: {stats['bytes_saved'] / stats['processed']:.0f} bytes/recipe")
