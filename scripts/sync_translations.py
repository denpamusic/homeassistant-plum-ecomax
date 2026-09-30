"""Synchronize translation files with strings.json."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any

type TranslationDict = dict[str, Any]


def get_all_keys(data: Any, prefix: str = "") -> set[str]:
    """Return all dotted key paths for all leaf nodes and empty dictionaries."""
    keys: set[str] = set()
    if isinstance(data, dict):
        if not data and prefix:
            keys.add(prefix)
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict) and value:
                keys.update(get_all_keys(value, full_key))
            else:
                keys.add(full_key)
    elif prefix:
        keys.add(prefix)
    return keys


def sort_dict(data: TranslationDict) -> TranslationDict:
    """Recursively sort dictionary keys in alphabetical order."""
    sorted_dict: TranslationDict = {}
    for key in sorted(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            sorted_dict[key] = sort_dict(val)
        else:
            sorted_dict[key] = val
    return sorted_dict


def sync_dict(strings: TranslationDict, target: TranslationDict) -> TranslationDict:
    """Recursively synchronize target dictionary to match the structure of strings."""
    result: TranslationDict = {}
    for key, s_val in strings.items():
        if key in target:
            t_val = target[key]
            if isinstance(s_val, dict) and isinstance(t_val, dict):
                result[key] = sync_dict(s_val, t_val)
            elif isinstance(s_val, dict):
                result[key] = copy.deepcopy(s_val)
            elif isinstance(t_val, dict):
                result[key] = copy.deepcopy(s_val)
            else:
                # Preserve existing translation for leaf node
                result[key] = t_val
        else:
            # Key is missing in target, add from strings
            result[key] = copy.deepcopy(s_val)
    return result


def sync_translation_file(
    strings_data: TranslationDict,
    strings_keys: set[str],
    target_path: Path,
    check_only: bool = False,
    sort_keys: bool = False,
) -> tuple[list[str], list[str], bool]:
    """Synchronize a single translation file with strings data."""
    with target_path.open("r", encoding="utf-8") as f:
        target_data: TranslationDict = json.load(f)

    target_keys = get_all_keys(target_data)
    added_keys = sorted(strings_keys - target_keys)
    removed_keys = sorted(target_keys - strings_keys)

    synced_data = sync_dict(strings_data, target_data)
    if sort_keys:
        synced_data = sort_dict(synced_data)

    current_dump = json.dumps(target_data, indent=2, ensure_ascii=False) + "\n"
    new_dump = json.dumps(synced_data, indent=2, ensure_ascii=False) + "\n"
    content_changed = current_dump != new_dump

    if not check_only and content_changed:
        with target_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(new_dump)

    return added_keys, removed_keys, content_changed


def resolve_paths(
    strings_arg: Path | None,
    translations_arg: Path | None,
) -> tuple[Path, Path]:
    """Resolve paths to strings.json and translations directory."""
    strings_path: Path | None = strings_arg
    translations_path: Path | None = translations_arg

    if strings_path is None or translations_path is None:
        cwd = Path.cwd()
        candidate_strings = cwd / "strings.json"
        candidate_translations = cwd / "translations"
        if candidate_strings.is_file() and candidate_translations.is_dir():
            strings_path = strings_path or candidate_strings
            translations_path = translations_path or candidate_translations

    if strings_path is None or translations_path is None:
        candidate_strings = (
            Path.cwd() / "custom_components" / "plum_ecomax" / "strings.json"
        )
        candidate_translations = (
            Path.cwd() / "custom_components" / "plum_ecomax" / "translations"
        )
        if candidate_strings.is_file() and candidate_translations.is_dir():
            strings_path = strings_path or candidate_strings
            translations_path = translations_path or candidate_translations

    if strings_path is None or translations_path is None:
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent
        candidate_strings = (
            repo_root / "custom_components" / "plum_ecomax" / "strings.json"
        )
        candidate_translations = (
            repo_root / "custom_components" / "plum_ecomax" / "translations"
        )
        if candidate_strings.is_file() and candidate_translations.is_dir():
            strings_path = strings_path or candidate_strings
            translations_path = translations_path or candidate_translations

    strings_path = strings_path or Path("strings.json")
    translations_path = translations_path or Path("translations")

    return strings_path, translations_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Synchronize translations directory with strings.json."
    )
    parser.add_argument(
        "-s",
        "--strings",
        type=Path,
        default=None,
        help="Path to strings.json (default: auto-detected)",
    )
    parser.add_argument(
        "-t",
        "--translations",
        type=Path,
        default=None,
        help="Path to translations directory (default: auto-detected)",
    )
    parser.add_argument(
        "-c",
        "--check",
        action="store_true",
        help="Check if translation files are in sync without modifying files",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort keys in source and translation files in alphabetical order",
    )
    return parser.parse_args(argv)


def report_file_sync(
    file_name: str,
    added: list[str],
    removed: list[str],
    content_changed: bool,
    check_only: bool,
    sort_keys: bool,
) -> None:
    """Print synchronization details for a single translation file."""
    sys.stdout.write(f"{file_name}:\n")
    order_only_changed = content_changed and not added and not removed
    if not added and not removed and not order_only_changed:
        sys.stdout.write("  In sync (no changes).\n\n")
        return

    action_add = "Would add" if check_only else "Added"
    action_rem = "Would remove" if check_only else "Removed"
    action_sort = "Would sort" if check_only else "Sorted"

    if added:
        sys.stdout.write(f"  {action_add} ({len(added)} keys):\n")
        for key in added:
            sys.stdout.write(f"    + {key}\n")
    if removed:
        sys.stdout.write(f"  {action_rem} ({len(removed)} keys):\n")
        for key in removed:
            sys.stdout.write(f"    - {key}\n")
    if sort_keys and content_changed:
        sys.stdout.write(f"  {action_sort} keys in alphabetical order.\n")
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    """Run translation synchronization tool."""
    args = parse_args(argv)
    strings_path, translations_path = resolve_paths(args.strings, args.translations)

    if not strings_path.is_file():
        sys.stderr.write(f"Error: strings file not found at '{strings_path}'\n")
        return 1

    if not translations_path.is_dir():
        sys.stderr.write(
            f"Error: translations directory not found at '{translations_path}'\n"
        )
        return 1

    try:
        with strings_path.open("r", encoding="utf-8") as f:
            strings_data: TranslationDict = json.load(f)
    except json.JSONDecodeError as err:
        sys.stderr.write(f"Error: Failed to parse '{strings_path}': {err}\n")
        return 1

    strings_changed = False
    if args.sort:
        sorted_strings = sort_dict(strings_data)
        current_strings_dump = (
            json.dumps(strings_data, indent=2, ensure_ascii=False) + "\n"
        )
        new_strings_dump = (
            json.dumps(sorted_strings, indent=2, ensure_ascii=False) + "\n"
        )
        if current_strings_dump != new_strings_dump:
            strings_changed = True
            strings_data = sorted_strings
            if not args.check:
                with strings_path.open("w", encoding="utf-8", newline="\n") as f:
                    f.write(new_strings_dump)

    strings_keys = get_all_keys(strings_data)
    translation_files = sorted(translations_path.glob("*.json"))

    if not translation_files:
        sys.stdout.write(f"No translation files found in '{translations_path}'.\n")
        return 0

    mode_prefix = "[CHECK] " if args.check else ""
    sys.stdout.write(
        f"{mode_prefix}Synchronizing translations with '{strings_path.as_posix()}'...\n\n"
    )

    if args.sort:
        sys.stdout.write(f"{strings_path.name}:\n")
        if strings_changed:
            action = "Would sort" if args.check else "Sorted"
            sys.stdout.write(f"  {action} keys in alphabetical order.\n\n")
        else:
            sys.stdout.write("  In sync (keys already sorted).\n\n")

    total_added = 0
    total_removed = 0
    file_stats: list[tuple[str, int, int, bool]] = []

    for file_path in translation_files:
        try:
            added, removed, content_changed = sync_translation_file(
                strings_data=strings_data,
                strings_keys=strings_keys,
                target_path=file_path,
                check_only=args.check,
                sort_keys=args.sort,
            )
        except json.JSONDecodeError as err:
            sys.stderr.write(f"Error: Failed to parse '{file_path}': {err}\n")
            continue

        file_stats.append((file_path.name, len(added), len(removed), content_changed))
        total_added += len(added)
        total_removed += len(removed)
        report_file_sync(
            file_name=file_path.name,
            added=added,
            removed=removed,
            content_changed=content_changed,
            check_only=args.check,
            sort_keys=args.sort,
        )

    summary_title = (
        "[CHECK] Summary of changes:" if args.check else "Summary:"
    )
    sys.stdout.write(f"{summary_title}\n")
    if args.sort:
        if strings_changed:
            status = "to sort" if args.check else "sorted"
            sys.stdout.write(f"  {strings_path.name}: {status}\n")
        else:
            sys.stdout.write(f"  {strings_path.name}: in sync\n")

    for name, add_count, rem_count, changed in file_stats:
        if add_count == 0 and rem_count == 0:
            if changed and args.sort:
                status = "in sync (to sort)" if args.check else "in sync (sorted)"
                sys.stdout.write(f"  {name}: {status}\n")
            else:
                sys.stdout.write(f"  {name}: in sync\n")
        else:
            sort_suffix = ""
            if changed and args.sort:
                sort_suffix = " (to sort)" if args.check else " (sorted)"
            sys.stdout.write(f"  {name}: +{add_count}, -{rem_count}{sort_suffix}\n")

    sys.stdout.write(
        f"\nTotal: {total_added} added, {total_removed} removed across "
        f"{len(file_stats)} file(s).\n"
    )

    has_changes = (
        strings_changed
        or total_added > 0
        or total_removed > 0
        or any(changed for _, _, _, changed in file_stats)
    )

    if args.check:
        if has_changes:
            sys.stdout.write("Check failed: translation files are out of sync.\n")
            return 1
        sys.stdout.write("Check passed: translation files are in sync.\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
