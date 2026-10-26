"""Export a GitHub-ready, allowlisted source tree with no .git or personal config."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = ('main.py', '桌宠.py', 'animation.py', 'app_paths.py', 'companion.py', 'companion_lines.py',
       'desktop_geometry.py', 'game_guard.py', 'pet_theme.py', 'sprite_store.py',
       'prepare_assets.py', 'body_motion.py', 'test_body_motion.py',
       'prepare_unified_art.py', 'build_heart_motion.py', 'build_action_motion.py', 'probe_unified_art.py',
       'test_animation.py', 'test_app_paths.py', 'test_companion.py', 'test_desktop_geometry.py',
       'test_guard.py', 'test_playroom.py', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
       'VERSION', 'CHANGELOG.md', '.gitignore', 'requirements.txt', 'requirements-build.txt',
       'requirements-lock.txt', 'asset-build-requirements.txt', 'config.example.json',
       'companion-avatar.ico', '启动桌宠.bat')
RAW = ('turnaround.png', 'walk-cycle.png', 'wave-cycle.png', 'blink-cycle.png')


def candidates():
    files = [ROOT/name for name in TOP]
    files += [ROOT/'sprites-anime'/name for name in RAW]
    for folder in ('docs', 'scripts', 'skills/xiaoxue-pet', 'packaging', '.github'):
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for p in (ROOT/'sprites-anime/prepared').rglob('*'):
        if p.is_file() and not {'rig', '306'}.intersection(p.parts) and p.suffix in ('.png', '.json'):
            files.append(p)
    for name in ('style-reference.png', 'heart-finger.png', 'heart-chest.png', 'heart-overhead.png',
                 'care.png', 'expressions.png', 'drink.png', 'prompts.txt', 'care-prompts.txt'):
        files.append(ROOT/'sprites-anime/unified-source'/name)
    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination == ROOT or destination in ROOT.parents:
        raise SystemExit('Destination must be a separate publication directory')
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise SystemExit('Use an empty destination; existing release files will not be deleted')
    config = ROOT/'config.json'
    private_key = ''
    if config.exists():
        private_key = str(json.loads(config.read_text(encoding='utf-8')).get('ds_api_key', ''))
    copied = []
    for source in candidates():
        if not source.is_file():
            raise RuntimeError(f'Missing release input: {source.relative_to(ROOT)}')
        data = source.read_bytes()
        if len(private_key) >= 8 and private_key.encode() in data:
            raise RuntimeError(f'Private credential found in {source.relative_to(ROOT)}; contents not printed')
        relative = source.relative_to(ROOT)
        if any(part in ('backups', '.venv', '.git', '.asset-build-tools') for part in relative.parts):
            raise RuntimeError('Disallowed private directory')
        if source.suffix.lower() in ('.py', '.md', '.json', '.yaml', '.txt', '.spec'):
            text = data.decode('utf-8', errors='replace')
            if re.search(r'(?i)sk-[a-z0-9]{24,}', text):
                raise RuntimeError(f'Possible credential in {relative}; inspect locally')
        out = destination/relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, out)
        copied.append(relative.as_posix())
    (destination/'PUBLICATION_MANIFEST.json').write_text(json.dumps({
        'files': copied, 'personal_config_included': False, 'original_photos_included': False,
        'git_history_included': False, 'local_credential_scan': 'passed'}, ensure_ascii=False, indent=2), encoding='utf-8')
    version = (ROOT/'VERSION').read_text().strip()
    archive_path = destination.parent/f'XiaoxuePet-{version}-Source.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in sorted(destination.rglob('*')):
            if file.is_file():
                archive.write(file, (Path('xiaoxue-pet')/file.relative_to(destination)).as_posix())
    skill = destination/'skills/xiaoxue-pet'
    with zipfile.ZipFile(destination.parent/'xiaoxue-pet-skill.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(skill.rglob('*')):
            if file.is_file():
                archive.write(file, (Path('xiaoxue-pet')/file.relative_to(skill)).as_posix())
    print(f'Exported {len(copied)} allowlisted files; private config and history excluded.')


if __name__ == '__main__':
    main()
