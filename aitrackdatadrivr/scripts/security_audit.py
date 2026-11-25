#!/usr/bin/env python3
"""Auditoria reproduzível do working tree; não imprime valores potencialmente secretos."""

from pathlib import Path
import re
import subprocess


EXCLUDED_PARTS = {'node_modules', 'build', '.git'}
PRODUCTION_SECRET_PATTERNS = (
    re.compile(r"(?i)['\"](?:password|passwd|api[_-]?key|secret)['\"]\s*:\s*['\"](?!<REDACTED>|\$\{|os\.)[^'\"]{3,}['\"]"),
    re.compile(r'(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'(?i)mysql\s+[^\n]*\s-p[^\s<][^\s]*'),
)


def tracked_files(root):
    output = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=root,
    )
    return [root / item.decode() for item in output.split(b'\0') if item]


def scan(root):
    findings = []
    for path in tracked_files(root):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if 'tests' in relative.parts or path.suffix in {'.pdf', '.png', '.jpg', '.ico'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if '<REDACTED>' in line:
                continue
            if any(pattern.search(line) for pattern in PRODUCTION_SECRET_PATTERNS):
                findings.append({'file': str(relative), 'line': line_number, 'rule': 'possible-secret'})
    return findings


def main():
    root = Path(__file__).resolve().parents[2]
    findings = scan(root)
    print(f'security_audit tracked_files findings={len(findings)}')
    for finding in findings:
        print(f"{finding['file']}:{finding['line']} {finding['rule']}")
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
