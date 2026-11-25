#!/usr/bin/env python3
"""Checa runbook por instruções destrutivas amplas, credenciais e comandos sem alvo."""

from pathlib import Path
import re
import sys


FORBIDDEN = [
    (re.compile(r'\b(?:pkill|killall)\b', re.I), 'process-wide kill command'),
    (re.compile(r'\b(?:DROP|TRUNCATE)\s+(?:TABLE|DATABASE)\b', re.I), 'destructive SQL'),
    (re.compile(r'\bDELETE\s+FROM\s+\S+\s*;', re.I), 'unbounded SQL delete'),
    (re.compile(r'(?i)(?:password|passwd|token|secret)\s*[=:]\s*[^\s<]+'), 'possible secret'),
    (re.compile(r'\bkill\s+(?:-\d+\s+)?(?:\$\(|\$[A-Za-z_]|\*|[A-Za-z])'), 'kill without numeric PID'),
]


def validate(path):
    contents = path.read_text(encoding='utf-8')
    findings = []
    for line_number, line in enumerate(contents.splitlines(), 1):
        if line.lstrip().startswith('>') or line.lstrip().startswith('<!--'):
            continue
        if line.lstrip().startswith('```') or line.strip() == 'kill PID' or 'não use kill por nome' in line.casefold():
            continue
        for pattern, label in FORBIDDEN:
            if pattern.search(line):
                findings.append(f'{line_number}: {label}')
    required = ('health/live', 'health/ready', 'reconcil', 'rollback', 'takeover', 'Runbook')
    for term in required:
        if term.casefold() not in contents.casefold():
            findings.append(f'missing required topic: {term}')
    return findings


def main():
    path = Path(__file__).resolve().parents[2] / 'docs' / 'RUNBOOK_OPERACAO_CONTINGENCIA.md'
    findings = validate(path)
    print(f'runbook_validation findings={len(findings)}')
    for item in findings:
        print(item)
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
