"""Data loader for Reno Rennsport Porsche MCP Server.

Handles finding the data/ directory, loading JSON files, caching,
and full-text search across all loaded datasets.
"""

import json
import os
import re
from pathlib import Path
from functools import lru_cache
from typing import Any, Optional


def _find_data_dir() -> Path:
    """Locate the data/ directory.

    Search order:
    1. DATA_DIR environment variable
    2. ./data/ relative to the project root (parent of src/)
    3. ~/reno-rennsport-mcp/data/
    """
    # 1. Environment variable override
    env_dir = os.environ.get("RENO_PORSCHE_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return p

    # 2. Bundled inside the package: src/reno_porsche_mcp/data/
    pkg_data = Path(__file__).resolve().parent / "data"
    if pkg_data.is_dir():
        return pkg_data

    # 3. Relative to project root: src/reno_porsche_mcp/data_loader.py -> ../../data
    project_root = Path(__file__).resolve().parent.parent.parent
    candidate = project_root / "data"
    if candidate.is_dir():
        return candidate

    # 4. Home directory fallback
    home_candidate = Path.home() / "reno-rennsport-mcp" / "data"
    if home_candidate.is_dir():
        return home_candidate

    # Return the package-relative path even if it doesn't exist yet
    return pkg_data


DATA_DIR = _find_data_dir()

# In-memory cache: filename -> parsed JSON
_cache: dict[str, Any] = {}


def get_data_dir() -> Path:
    """Return the resolved data directory path."""
    global DATA_DIR
    DATA_DIR = _find_data_dir()
    return DATA_DIR


def load_json(filename: str, subdirectory: str | None = None) -> Any | None:
    """Load a JSON file from the data directory, with caching.

    Args:
        filename: Name of the JSON file (e.g., 'models.json')
        subdirectory: Optional subdirectory within data/ (e.g., 'specs')

    Returns:
        Parsed JSON data, or None if the file doesn't exist.
    """
    cache_key = f"{subdirectory}/{filename}" if subdirectory else filename

    if cache_key in _cache:
        return _cache[cache_key]

    data_dir = get_data_dir()
    if subdirectory:
        filepath = data_dir / subdirectory / filename
    else:
        filepath = data_dir / filename

    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache[cache_key] = data
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[data_loader] Error loading {filepath}: {e}")
        return None


def clear_cache():
    """Clear the in-memory data cache."""
    _cache.clear()


def list_available_data() -> dict[str, list[str]]:
    """List all available JSON data files organized by subdirectory.

    Returns:
        Dict mapping subdirectory names (or '.' for root) to lists of filenames.
    """
    data_dir = get_data_dir()
    result: dict[str, list[str]] = {}

    if not data_dir.exists():
        return result

    for path in sorted(data_dir.rglob("*.json")):
        rel = path.relative_to(data_dir)
        if len(rel.parts) > 1:
            subdir = str(rel.parent)
        else:
            subdir = "."
        result.setdefault(subdir, []).append(rel.name)

    return result


def _extract_strings(obj: Any, depth: int = 0) -> list[str]:
    """Recursively extract all string values from a nested JSON structure."""
    if depth > 20:
        return []
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            strings.append(str(k))
            strings.extend(_extract_strings(v, depth + 1))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            strings.extend(_extract_strings(item, depth + 1))
    return strings


def _match_score(query_lower: str, text_lower: str) -> float:
    """Score how well a query matches a text string. Higher is better."""
    if query_lower == text_lower:
        return 10.0
    if query_lower in text_lower:
        return 5.0 + (len(query_lower) / len(text_lower))
    # Check if all query words appear in text
    words = query_lower.split()
    if all(w in text_lower for w in words):
        return 3.0
    # Partial word matches
    matched = sum(1 for w in words if w in text_lower)
    if matched > 0:
        return matched / len(words)
    return 0.0


def search_all(query: str, max_results: int = 20) -> list[dict[str, Any]]:
    """Full-text search across all loaded data files.

    Searches through every string value in every JSON file in the data directory.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with 'source', 'path', 'match', and 'score' keys.
    """
    data_dir = get_data_dir()
    if not data_dir.exists():
        return []

    query_lower = query.lower().strip()
    if not query_lower:
        return []

    results: list[dict[str, Any]] = []

    for json_path in data_dir.rglob("*.json"):
        rel = str(json_path.relative_to(data_dir))
        data = load_json(json_path.name, subdirectory=str(json_path.relative_to(data_dir).parent) if len(json_path.relative_to(data_dir).parts) > 1 else None)
        if data is None:
            continue

        _search_recursive(data, query_lower, rel, [], results)

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def _search_recursive(
    obj: Any,
    query_lower: str,
    source: str,
    path: list[str],
    results: list[dict[str, Any]],
    depth: int = 0,
):
    """Recursively search through a JSON structure for matching strings."""
    if depth > 15:
        return

    if isinstance(obj, str):
        score = _match_score(query_lower, obj.lower())
        if score > 0:
            results.append({
                "source": source,
                "path": ".".join(path) if path else source,
                "match": obj[:200],
                "score": score,
            })
    elif isinstance(obj, dict):
        for k, v in obj.items():
            # Check the key too
            key_score = _match_score(query_lower, str(k).lower())
            if key_score > 0:
                results.append({
                    "source": source,
                    "path": ".".join(path + [str(k)]),
                    "match": f"{k}: {str(v)[:150]}",
                    "score": key_score * 0.5,
                })
            _search_recursive(v, query_lower, source, path + [str(k)], results, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _search_recursive(item, query_lower, source, path + [f"[{i}]"], results, depth + 1)


def find_in_data(
    filename: str,
    key_field: str,
    search_value: str,
    subdirectory: str | None = None,
    year: int | None = None,
) -> list[dict]:
    """Search for records in a JSON data file by a key field value.

    Handles both list-of-dicts and dict-of-dicts structures.
    Uses fuzzy/normalized matching on the search value.

    Args:
        filename: JSON filename to search in.
        key_field: The field name to match against (e.g., 'model', 'code').
        search_value: The value to search for.
        subdirectory: Optional subdirectory within data/.
        year: Optional year filter.

    Returns:
        List of matching records.
    """
    data = load_json(filename, subdirectory)
    if data is None:
        return []

    search_norm = search_value.lower().strip()
    matches = []

    records: list[dict] = []
    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        # Could be keyed by model name or code
        for k, v in data.items():
            if isinstance(v, dict):
                rec = {**v}
                if key_field not in rec:
                    rec[key_field] = k
                records.append(rec)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        rec = {**item}
                        if key_field not in rec:
                            rec[key_field] = k
                        records.append(rec)

    for record in records:
        field_val = str(record.get(key_field, "")).lower().strip()
        if search_norm in field_val or field_val in search_norm:
            if year is not None:
                rec_year = record.get("year") or record.get("model_year")
                if rec_year is not None:
                    # Handle year ranges like "1998-2004"
                    year_str = str(rec_year)
                    if "-" in year_str:
                        try:
                            y_start, y_end = year_str.split("-")
                            if not (int(y_start) <= year <= int(y_end)):
                                continue
                        except ValueError:
                            pass
                    else:
                        try:
                            if int(year_str) != year:
                                continue
                        except ValueError:
                            pass
            matches.append(record)

    return matches


def format_record(record: dict, title: str | None = None) -> str:
    """Format a dict record into a readable text block.

    Args:
        record: Dictionary to format.
        title: Optional title header.

    Returns:
        Formatted string representation.
    """
    lines = []
    if title:
        lines.append(f"═══ {title} ═══")
        lines.append("")

    max_key_len = max((len(str(k)) for k in record.keys()), default=0)

    for key, value in record.items():
        label = str(key).replace("_", " ").title()
        if isinstance(value, dict):
            lines.append(f"  {label}:")
            for sk, sv in value.items():
                sub_label = str(sk).replace("_", " ").title()
                lines.append(f"    {sub_label}: {sv}")
        elif isinstance(value, list):
            lines.append(f"  {label}:")
            for item in value:
                if isinstance(item, dict):
                    summary = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:4])
                    lines.append(f"    • {summary}")
                else:
                    lines.append(f"    • {item}")
        else:
            lines.append(f"  {label}: {value}")

    return "\n".join(lines)


def format_records(records: list[dict], title: str | None = None) -> str:
    """Format a list of records into readable text."""
    if not records:
        return "No records found."

    parts = []
    if title:
        parts.append(f"═══ {title} ({len(records)} results) ═══\n")

    for i, record in enumerate(records, 1):
        rec_title = record.get("name") or record.get("model") or record.get("title") or f"Record {i}"
        parts.append(format_record(record, title=str(rec_title)))
        parts.append("")

    return "\n".join(parts)
