#!/usr/bin/env python3
"""
Generate Velociraptor-ready YAML stanzas (parameters + CommandTable rows)
for every Linux Atomic Red Team test that already exists.

USAGE
  $ python3 make_art_yaml.py ./linux_atomic_tests.md

The script prints two blocks:

  1.  parameters:  – copy-and-paste into the parameters section
  2.  CommandTable – copy-and-paste into the LET CommandTable = parse_csv(...)
"""
import re
import sys
from pathlib import Path
from textwrap import indent

TECH_RE   = re.compile(r'- \[?(T\d{4,5}(?:\.\d{3})?)')
ATOMIC_RE = re.compile(r'\s+- Atomic Test #(\d+):\s*(.+?)\s*\[(.*?)\]', re.I)

def main(src: Path):
    current_t = None
    params, commands = [], []

    for line in src.read_text().splitlines():
        t_match = TECH_RE.match(line)
        if t_match:
            current_t = t_match.group(1)
            continue

        a_match = ATOMIC_RE.match(line)
        if a_match and current_t:
            test_no, descr, os_tags = a_match.groups()
            if 'linux' not in os_tags.lower():
                continue                       # skip non-Linux tests

            flag = f'{current_t} - {test_no}'
            params.append(
                f"""- name: {flag}
  description: {descr.strip()}
  type: bool"""
            )
            commands.append(
                f'{flag},"Invoke-AtomicTest {current_t} -TestNumbers {test_no}"'
            )

    print('PARAMETERS SECTION:\n')
    print(indent('\n'.join(params), '    '))
    print('\n\n---\n\nCOMMANDTABLE CSV ROWS:\n')
    for row in commands:
        print(row)

if __name__ == "__main__":
    main(Path(sys.argv[1]))