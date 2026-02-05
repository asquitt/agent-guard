#!/usr/bin/env python3
"""Check that all models are properly imported in models/__init__.py.

This script prevents schema drift by ensuring Alembic can see all models.
Run this before creating migrations.

Usage:
    python scripts/check_model_imports.py
"""

import ast
import os
import sys
from pathlib import Path


def find_models_with_tablename(models_dir: Path) -> set[str]:
    """Find all classes with __tablename__ in the models directory."""
    model_classes = set()

    for py_file in models_dir.glob("**/*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            with open(py_file, "r") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "__tablename__":
                                    model_classes.add(node.name)
        except SyntaxError as e:
            print(f"Syntax error in {py_file}: {e}")

    return model_classes


def find_imported_models(init_file: Path) -> set[str]:
    """Find all models imported in __init__.py."""
    imported = set()

    if not init_file.exists():
        return imported

    try:
        with open(init_file, "r") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.name if alias.asname is None else alias.asname)
    except SyntaxError as e:
        print(f"Syntax error in {init_file}: {e}")

    return imported


def main():
    """Main function to check model imports."""
    # Find the models directory
    script_dir = Path(__file__).parent
    models_dir = script_dir.parent / "app" / "models"

    if not models_dir.exists():
        print(f"Models directory not found: {models_dir}")
        sys.exit(1)

    init_file = models_dir / "__init__.py"

    # Find all models with __tablename__
    defined_models = find_models_with_tablename(models_dir)

    # Find all imported models
    imported_models = find_imported_models(init_file)

    # Check for missing imports
    missing = defined_models - imported_models

    if missing:
        print("ERROR: The following models are NOT imported in models/__init__.py:")
        for model in sorted(missing):
            print(f"  - {model}")
        print("\nThis will cause Alembic to generate DROP TABLE migrations!")
        print("Add the missing imports to app/models/__init__.py")
        sys.exit(1)

    # Check for extra imports (models that don't exist)
    extra = imported_models - defined_models
    if extra:
        print("WARNING: The following imports don't match any model with __tablename__:")
        for model in sorted(extra):
            print(f"  - {model}")
        print("\nThese may be enums, mixins, or deleted models.")

    print(f"OK: {len(defined_models)} models defined, {len(imported_models)} imported")
    sys.exit(0)


if __name__ == "__main__":
    main()
