"""Prepare checked GitHub runner artifacts; publication remains a separate step."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = (ROOT/'VERSION').read_text().strip()
    output = ROOT/'.release'
    for name in (f'XiaoxuePet-{version}-Source.zip', 'xiaoxue-pet-skill.zip'):
        shutil.copy2(ROOT/'.publication'/name, output/name)
    subprocess.run(['gh', 'release', 'download', 'v'+version,
                    '--pattern', 'START_HERE.md', '--pattern', 'RELEASE_NOTES.md',
                    '--dir', str(output)], cwd=ROOT, check=True)
    report = json.loads((ROOT/'docs/release-validation.json').read_text(encoding='utf-8'))
    report['installer'] = json.loads((output/'verification.json').read_text())
    report['build_environment'] = 'GitHub Actions windows-2022, Python 3.12'
    report['commit'] = os.environ['GITHUB_SHA']
    report['build_run'] = 'https://github.com/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID']
    (output/'release-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    names = [f'XiaoxuePet-{version}-Setup.exe', f'XiaoxuePet-{version}-Windows-x64.zip',
             f'XiaoxuePet-{version}-Source.zip', 'xiaoxue-pet-skill.zip',
             'release-validation.json', 'verification.json', 'START_HERE.md', 'RELEASE_NOTES.md']
    sums = ''.join(hashlib.sha256((output/name).read_bytes()).hexdigest()+'  '+name+'\n'
                   for name in sorted(names))
    (output/'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    print('Prepared nine draft release assets with source commit and SHA-256.')


if __name__ == '__main__':
    main()
