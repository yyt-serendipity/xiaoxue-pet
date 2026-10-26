"""Prepare checked GitHub runner artifacts; publication remains a separate step."""
from pathlib import Path
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = (ROOT/'VERSION').read_text().strip()
    output = ROOT/'.release'
    for name in (f'XiaoxuePet-{version}-Source.zip', 'xiaoxue-pet-skill.zip'):
        shutil.copy2(ROOT/'.publication'/name, output/name)
    repository = os.environ['GITHUB_REPOSITORY']
    (output/'START_HERE.md').write_text(
        f'# 小薛同学桌宠 v{version}\n\n'
        f'[产品介绍](https://github.com/{repository}#readme) · '
        f'[版本下载](https://github.com/{repository}/releases/tag/v{version})\n\n'
        'Windows x64。Setup.exe 可自定义安装目录；免安装版必须完整解压后运行。\n\n'
        '升级前退出旧程序；在设置中选择「舒缓 · 0.75×」。安装包未签名，可核对 SHA256SUMS.txt。\n\n'
        '照片制作桌宠使用 xiaoxue-pet-skill.zip；普通陪伴不需要 API Key。\n', encoding='utf-8')
    (output/'RELEASE_NOTES.md').write_text((ROOT/'CHANGELOG.md').read_text(encoding='utf-8'), encoding='utf-8')
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
