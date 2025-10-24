#!/usr/bin/env python3

"""
compare_responses.py
Usage:
  python scripts/compare_responses.py responses/previous/response_previous.json responses/latest/response_latest.json
Generates:
  diff_output/diff_report.json
  diff_output/diff_report.txt
  diff_output/diff_report.html
"""

import sys
import json
import xmltodict
from pathlib import Path
from difflib import unified_diff, HtmlDiff

# ---------- Utility functions ----------

def try_parse_json(text):
    try:
        return json.loads(text)
    except:
        return None

def try_parse_xml(text):
    try:
        return xmltodict.parse(text)
    except:
        return None

def normalize_to_object(text):
    """Converts response to a Python object if it's JSON or XML."""
    json_obj = try_parse_json(text)
    if json_obj is not None:
        return json_obj, "json"
    xml_obj = try_parse_xml(text)
    if xml_obj is not None:
        return xml_obj, "xml"
    return None, "text"

def pretty_text_from_obj(obj, fmt):
    if fmt in ("json", "xml"):
        return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    return str(obj)

# ---------- Comparison logic ----------

def compare_dicts(old, new, path=""):
    changes = []

    def full_path(sub):
        return f"{path}.{sub}" if path else str(sub)

    if isinstance(old, dict) and isinstance(new, dict):
        for k in old:
            if k not in new:
                changes.append({"type": "removed", "path": full_path(k), "old": old[k]})
            else:
                changes.extend(compare_dicts(old[k], new[k], full_path(k)))
        for k in new:
            if k not in old:
                changes.append({"type": "added", "path": full_path(k), "new": new[k]})
        return changes

    if isinstance(old, list) and isinstance(new, list):
        minlen = min(len(old), len(new))
        for i in range(minlen):
            changes.extend(compare_dicts(old[i], new[i], full_path(f"[{i}]")))
        if len(old) > len(new):
            for i in range(minlen, len(old)):
                changes.append({"type": "removed", "path": full_path(f"[{i}]"), "old": old[i]})
        elif len(new) > len(old):
            for i in range(minlen, len(new)):
                changes.append({"type": "added", "path": full_path(f"[{i}]"), "new": new[i]})
        return changes

    if old != new:
        changes.append({"type": "modified", "path": path or "/", "old": old, "new": new})
    return changes

# ---------- Main function ----------

def compare_files(old_file, new_file):
    raw_old = old_file.read_text(encoding="utf-8")
    raw_new = new_file.read_text(encoding="utf-8")

    obj_old, fmt_old = normalize_to_object(raw_old)
    obj_new, fmt_new = normalize_to_object(raw_new)

    structured_diff = None
    pretty_old = raw_old
    pretty_new = raw_new

    if obj_old is not None and obj_new is not None and fmt_old == fmt_new:
        pretty_old = pretty_text_from_obj(obj_old, fmt_old)
        pretty_new = pretty_text_from_obj(obj_new, fmt_new)
        structured_diff = compare_dicts(obj_old, obj_new)
    else:
        if obj_old is not None:
            pretty_old = pretty_text_from_obj(obj_old, fmt_old)
        if obj_new is not None:
            pretty_new = pretty_text_from_obj(obj_new, fmt_new)

    # Create output folder if not exists
    output_dir = Path("diff_output")
    output_dir.mkdir(exist_ok=True)

    # Write unified diff (text)
    old_lines = pretty_old.splitlines(keepends=True)
    new_lines = pretty_new.splitlines(keepends=True)
    udiff = list(unified_diff(old_lines, new_lines, fromfile=old_file.name, tofile=new_file.name))
    (output_dir / "diff_report.txt").write_text("".join(udiff), encoding="utf-8")

    # Write HTML diff
    html_diff = HtmlDiff().make_file(old_lines, new_lines, fromdesc=old_file.name, todesc=new_file.name)
    (output_dir / "diff_report.html").write_text(html_diff, encoding="utf-8")

    # Write structured JSON diff
    if structured_diff is not None:
        (output_dir / "diff_report.json").write_text(json.dumps(structured_diff, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        (output_dir / "diff_report.json").write_text(
            json.dumps({"info": "Structured diff unavailable; see diff_report.txt or diff_report.html."}, indent=2),
            encoding="utf-8"
        )

    print("✅ Comparison complete!")
    print("Reports generated in diff_output/ folder")

# ---------- Entry point ----------

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/compare_responses.py <old_file> <new_file>")
        sys.exit(1)

    old_path = Path(sys.argv[1])
    new_path = Path(sys.argv[2])

    if not old_path.exists() or not new_path.exists():
        print("❌ Error: One or both files not found.")
        sys.exit(1)

    compare_files(old_path, new_path)
