#!/usr/bin/env python3
"""
dedup_velociraptor.py

 • Removes duplicate `name:` items inside `parameters:` and `CommandTable:` lists.
 • Also deduplicates the inline CSV used to build CommandTable in VQL queries.

Usage:
    python dedup_velociraptor.py <artifact.yaml> [<out.yaml>]
"""

import csv
import re
import sys
from pathlib import Path

try:
    from ruamel.yaml import YAML           # preserves comments/ordering
except ImportError:
    import yaml
    YAML = None

# --------------------------------------------------------------------
def load_yaml(path):
    if YAML:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.explicit_start = True
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.load(fh), yaml
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh), yaml

def dedup_list(items):
    seen, out = set(), []
    for obj in items or []:
        key = obj.get("name")
        if key not in seen:
            seen.add(key)
            out.append(obj)
    return out

# --------------------------------------------------------------------
CSV_BLOCK_RE = re.compile(
    r"(LET\s+CommandTable\s*=.*?filename\s*=\s*'''[\r\n]+)"   # group 1 = prefix
    r"(.*?)"                                                  # group 2 = CSV
    r"([\r\n]+\s*'''[\r\n]*)",                                # group 3 = suffix
    re.DOTALL | re.IGNORECASE,
)

def dedup_csv_block(prefix: str, csv_text: str, suffix: str) -> str:
    """Return the three parts re-assembled with duplicate Flag rows removed."""
    # Figure out indentation (spaces before first data row, if any)
    indent_match = re.match(r"(\s*)", csv_text.splitlines()[0])
    indent = indent_match.group(1) if indent_match else ""

    reader = csv.reader(line.lstrip() for line in csv_text.splitlines())
    rows = list(reader)
    if not rows:
        return prefix + csv_text + suffix

    header, data_rows = rows[0], rows[1:]
    seen, deduped = set(), []
    for r in data_rows:
        if r and r[0] not in seen:
            seen.add(r[0])
            deduped.append(r)

    out_lines = [",".join(header)] + [",".join(r) for r in deduped]
    out_csv = "\n".join(indent + ln for ln in out_lines)
    return prefix + out_csv + suffix

def dedup_query_csv(query: str) -> str:
    """Return query string with any CommandTable CSV blocks deduplicated."""
    def repl(m):
        return dedup_csv_block(*m.groups())
    return CSV_BLOCK_RE.sub(repl, query)

# --------------------------------------------------------------------
def main(in_file: Path, out_file: Path):
    data, yaml_lib = load_yaml(in_file)

    # 1️⃣  dedup top-level YAML lists
    for section in ("parameters", "CommandTable"):
        if section in data:
            data[section] = dedup_list(data[section])

    # 2️⃣  dedup inline CSV inside each sources[].query
    if "sources" in data:
        for src in data["sources"]:
            if isinstance(src, dict) and "query" in src:
                src["query"] = dedup_query_csv(src["query"])

    # 3️⃣  write result
    if YAML:
        yaml = yaml_lib
        with open(out_file, "w", encoding="utf-8") as fh:
            yaml.dump(data, fh)
    else:
        with open(out_file, "w", encoding="utf-8") as fh:
            yaml_lib.safe_dump(data, fh, sort_keys=False)

    print(f"✔  Deduplicated artifact written to {out_file}")

# --------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python dedup_velociraptor.py <artifact.yaml> [<out.yaml>]")
    in_path = Path(sys.argv[1]).expanduser().resolve()
    if not in_path.exists():
        sys.exit(f"ERROR: {in_path} not found.")
    out_path = (Path(sys.argv[2]) if len(sys.argv) > 2
                else in_path.with_suffix(".dedup.yaml"))
    main(in_path, out_path)