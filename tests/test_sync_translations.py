"""Test translation synchronization tool."""

import json
from pathlib import Path

import pytest

from scripts.sync_translations import (
    get_all_keys,
    main,
    resolve_paths,
    sort_dict,
    sync_dict,
    sync_translation_file,
)


def test_get_all_keys() -> None:
    """Test get_all_keys returns dotted leaf keys and empty dicts."""
    data = {
        "a": "1",
        "b": {
            "c": "2",
            "d": {
                "e": "3",
            },
            "empty": {},
        },
    }
    assert get_all_keys(data) == {"a", "b.c", "b.d.e", "b.empty"}
    assert get_all_keys({}, prefix="empty_root") == {"empty_root"}
    assert get_all_keys("scalar", prefix="leaf") == {"leaf"}


def test_sort_dict() -> None:
    """Test sort_dict recursively sorts keys in alphabetical order."""
    data = {
        "z": 1,
        "a": {
            "d": 2,
            "b": 3,
        },
        "m": 4,
    }
    sorted_data = sort_dict(data)
    assert list(sorted_data.keys()) == ["a", "m", "z"]
    assert list(sorted_data["a"].keys()) == ["b", "d"]


def test_sync_dict_add_missing_keys() -> None:
    """Test missing keys in target are added from strings."""
    strings = {
        "title": "Welcome",
        "nested": {
            "foo": "Bar",
            "baz": "Qux",
        },
    }
    target = {
        "title": "Willkommen",
    }
    synced = sync_dict(strings, target)
    assert synced == {
        "title": "Willkommen",
        "nested": {
            "foo": "Bar",
            "baz": "Qux",
        },
    }


def test_sync_dict_remove_extra_keys() -> None:
    """Test keys not in strings are removed from target."""
    strings = {
        "title": "Welcome",
    }
    target = {
        "title": "Willkommen",
        "old_key": "Delete me",
        "nested": {
            "deprecated": "Also delete",
        },
    }
    synced = sync_dict(strings, target)
    assert synced == {
        "title": "Willkommen",
    }


def test_sync_dict_preserves_order() -> None:
    """Test output dictionary preserves order of strings.json."""
    strings = {
        "z": "Z",
        "a": "A",
        "m": "M",
    }
    target = {
        "m": "Translated M",
        "z": "Translated Z",
        "a": "Translated A",
    }
    synced = sync_dict(strings, target)
    assert list(synced.keys()) == ["z", "a", "m"]
    assert synced == {
        "z": "Translated Z",
        "a": "Translated A",
        "m": "Translated M",
    }


def test_sync_dict_type_mismatch() -> None:
    """Test handling type mismatch between strings and target."""
    strings = {
        "item1": {"sub": "value"},
        "item2": "scalar",
    }
    target = {
        "item1": "was_scalar",
        "item2": {"was": "dict"},
    }
    synced = sync_dict(strings, target)
    assert synced == {
        "item1": {"sub": "value"},
        "item2": "scalar",
    }


def test_sync_translation_file_dry_run(tmp_path: Path) -> None:
    """Test sync_translation_file does not modify files in dry_run mode."""
    strings_data = {"key1": "one", "key2": "two"}
    strings_keys = get_all_keys(strings_data)

    target_file = tmp_path / "de.json"
    initial_content = json.dumps({"key1": "eins", "old": "alt"}, indent=2) + "\n"
    target_file.write_text(initial_content, encoding="utf-8")

    added, removed, changed = sync_translation_file(
        strings_data, strings_keys, target_file, dry_run=True
    )
    assert added == ["key2"]
    assert removed == ["old"]
    assert changed is True

    # File should remain unchanged
    assert target_file.read_text(encoding="utf-8") == initial_content


def test_sync_translation_file_writes(tmp_path: Path) -> None:
    """Test sync_translation_file writes synced content when dry_run is False."""
    strings_data = {"key1": "one", "key2": "two"}
    strings_keys = get_all_keys(strings_data)

    target_file = tmp_path / "de.json"
    target_file.write_text(
        json.dumps({"key1": "eins", "old": "alt"}, indent=2) + "\n",
        encoding="utf-8",
    )

    added, removed, changed = sync_translation_file(
        strings_data, strings_keys, target_file, dry_run=False
    )
    assert added == ["key2"]
    assert removed == ["old"]
    assert changed is True

    saved_data = json.loads(target_file.read_text(encoding="utf-8"))
    assert saved_data == {"key1": "eins", "key2": "two"}


def test_resolve_paths_explicit(tmp_path: Path) -> None:
    """Test resolve_paths respects explicit arguments."""
    strings = tmp_path / "custom_strings.json"
    translations = tmp_path / "custom_translations"
    s, t = resolve_paths(strings, translations)
    assert s == strings
    assert t == translations


def test_resolve_paths_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test resolve_paths detects strings.json and translations in cwd."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "strings.json").write_text("{}", encoding="utf-8")
    (tmp_path / "translations").mkdir()

    s, t = resolve_paths(None, None)
    assert s == tmp_path / "strings.json"
    assert t == tmp_path / "translations"


def test_resolve_paths_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test resolve_paths fallback when run in a directory without files."""
    monkeypatch.chdir(tmp_path)
    s, t = resolve_paths(None, None)
    assert s.name == "strings.json"
    assert t.name == "translations"


def test_main_cli_dry_run(tmp_path: Path) -> None:
    """Test main CLI execution with dry-run."""
    strings_file = tmp_path / "strings.json"
    strings_file.write_text(json.dumps({"msg": "Hello"}), encoding="utf-8")

    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    de_file = trans_dir / "de.json"
    de_file.write_text(json.dumps({"old": "Hallo"}), encoding="utf-8")

    ret = main(
        [
            "--strings",
            str(strings_file),
            "--translations",
            str(trans_dir),
            "--dry-run",
        ]
    )
    assert ret == 0
    # Dry run must not touch de.json
    assert json.loads(de_file.read_text(encoding="utf-8")) == {"old": "Hallo"}


def test_main_cli_sync(tmp_path: Path) -> None:
    """Test main CLI execution synchronizing files."""
    strings_file = tmp_path / "strings.json"
    strings_file.write_text(json.dumps({"msg": "Hello"}), encoding="utf-8")

    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    de_file = trans_dir / "de.json"
    de_file.write_text(json.dumps({"old": "Hallo"}), encoding="utf-8")

    ret = main(
        [
            "--strings",
            str(strings_file),
            "--translations",
            str(trans_dir),
        ]
    )
    assert ret == 0
    assert json.loads(de_file.read_text(encoding="utf-8")) == {"msg": "Hello"}


def test_main_cli_sort(tmp_path: Path) -> None:
    """Test main CLI execution with --sort flag."""
    strings_file = tmp_path / "strings.json"
    strings_file.write_text(
        json.dumps({"z": "Z", "a": "A"}),
        encoding="utf-8",
    )

    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    de_file = trans_dir / "de.json"
    de_file.write_text(
        json.dumps({"z": "Translated Z", "a": "Translated A"}),
        encoding="utf-8",
    )

    ret = main(
        [
            "--strings",
            str(strings_file),
            "--translations",
            str(trans_dir),
            "--sort",
        ]
    )
    assert ret == 0

    sorted_strings_keys = list(
        json.loads(strings_file.read_text(encoding="utf-8")).keys()
    )
    sorted_de_keys = list(json.loads(de_file.read_text(encoding="utf-8")).keys())

    assert sorted_strings_keys == ["a", "z"]
    assert sorted_de_keys == ["a", "z"]


def test_main_cli_sort_dry_run(tmp_path: Path) -> None:
    """Test main CLI execution with --sort and --dry-run flags."""
    strings_file = tmp_path / "strings.json"
    strings_content = json.dumps({"z": "Z", "a": "A"})
    strings_file.write_text(strings_content, encoding="utf-8")

    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    de_file = trans_dir / "de.json"
    de_content = json.dumps({"z": "Translated Z", "a": "Translated A"})
    de_file.write_text(de_content, encoding="utf-8")

    ret = main(
        [
            "--strings",
            str(strings_file),
            "--translations",
            str(trans_dir),
            "--sort",
            "--dry-run",
        ]
    )
    assert ret == 0

    # Neither file should be modified
    assert strings_file.read_text(encoding="utf-8") == strings_content
    assert de_file.read_text(encoding="utf-8") == de_content


def test_main_sort_already_sorted(tmp_path: Path) -> None:
    """Test running --sort when keys are already sorted."""
    strings_file = tmp_path / "strings.json"
    strings_file.write_text(json.dumps({"a": "A", "b": "B"}), encoding="utf-8")

    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    de_file = trans_dir / "de.json"
    de_file.write_text(json.dumps({"a": "A", "b": "B"}), encoding="utf-8")

    ret = main(
        [
            "--strings",
            str(strings_file),
            "--translations",
            str(trans_dir),
            "--sort",
        ]
    )
    assert ret == 0


def test_main_missing_strings(tmp_path: Path) -> None:
    """Test main returns error on missing strings.json."""
    missing = tmp_path / "nonexistent.json"
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    ret = main(["--strings", str(missing), "--translations", str(trans_dir)])
    assert ret == 1


def test_main_missing_translations(tmp_path: Path) -> None:
    """Test main returns error on missing translations dir."""
    strings = tmp_path / "strings.json"
    strings.write_text("{}", encoding="utf-8")
    missing_dir = tmp_path / "nonexistent_dir"
    ret = main(["--strings", str(strings), "--translations", str(missing_dir)])
    assert ret == 1


def test_main_invalid_json_strings(tmp_path: Path) -> None:
    """Test main returns error on corrupted strings.json."""
    strings = tmp_path / "strings.json"
    strings.write_text("{bad json", encoding="utf-8")
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    ret = main(["--strings", str(strings), "--translations", str(trans_dir)])
    assert ret == 1


def test_main_invalid_json_translation(tmp_path: Path) -> None:
    """Test main skips corrupted translation files gracefully."""
    strings = tmp_path / "strings.json"
    strings.write_text(json.dumps({"a": "1"}), encoding="utf-8")
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    bad_file = trans_dir / "bad.json"
    bad_file.write_text("{corrupt", encoding="utf-8")
    good_file = trans_dir / "good.json"
    good_file.write_text("{}", encoding="utf-8")

    ret = main(["--strings", str(strings), "--translations", str(trans_dir)])
    assert ret == 0
    assert json.loads(good_file.read_text(encoding="utf-8")) == {"a": "1"}


def test_main_no_translation_files(tmp_path: Path) -> None:
    """Test main when translations directory has no json files."""
    strings = tmp_path / "strings.json"
    strings.write_text("{}", encoding="utf-8")
    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    ret = main(["--strings", str(strings), "--translations", str(trans_dir)])
    assert ret == 0
