"""Create an independent workspace from the bundled code-only pet template."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import zipfile


def bootstrap(destination, name, nickname, app_id=None):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination must be empty; existing projects are never overwritten')
    app_id = app_id or 'PhotoPet' + hashlib.sha256(str(destination).encode()).hexdigest()[:10]
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,47}', app_id):
        raise ValueError('app-id must be 3-48 ASCII letters/digits/underscores, starting with a letter')
    if app_id.lower() == 'xiaoxuepet':
        raise ValueError('Use a new app-id to keep settings separate from the original pet')
    for value in (name, nickname):
        if not value.strip() or len(value) > 32 or any(c in value for c in '\\/:*?"<>|\r\n\t\''):
            raise ValueError('Use short display names without quotes, control characters or path separators')
    if len(nickname) > 12:
        raise ValueError('Nickname must fit the 12-character settings field')
    template = Path(__file__).resolve().parents[1]/'assets/runtime-template.zip'
    replacements = [('小薛同学桌宠', name), ('小薛同学', nickname),
                    ('Xiao Xue Tong Xue Pet', name), ('XiaoxuePet', app_id),
                    ('xiaoxue-pet-install-v1-403369d4', app_id.lower() + '-install-v1'),
                    ('.xiaoxue-install', '.' + app_id.lower() + '-install')]
    planned = []
    with zipfile.ZipFile(template) as archive:
        for entry in archive.infolist():
            target = (destination/entry.filename).resolve()
            if not target.is_relative_to(destination) or target == destination or entry.is_dir():
                raise ValueError('Unsafe template entry')
            data = archive.read(entry)
            if target.suffix in ('.py', '.md', '.txt', '.json', '.cs', '.spec', '.bat') and 'third-party-licenses' not in target.parts and target.name != 'THIRD_PARTY_NOTICES.md':
                text = data.decode('utf-8')
                for old, new in replacements:
                    text = text.replace(old, new)
                data = text.encode('utf-8')
            planned.append((target, data))
    for target, data in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination/'sprites-anime/unified-source').mkdir(parents=True, exist_ok=True)
    (destination/'character-project.json').write_text(json.dumps({
        'product_name': name, 'nickname': nickname, 'app_id': app_id,
        'template_version': (destination/'VERSION').read_text().strip(), 'artwork_status': 'not_generated',
        'input_photos_bundled': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'project': str(destination), 'app_id': app_id,
                      'next': 'Generate all character sheets, validate and compile before launching.'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--name', default='我的桌宠')
    parser.add_argument('--nickname', default='小伴')
    parser.add_argument('--app-id')
    args = parser.parse_args()
    bootstrap(args.destination, args.name, args.nickname, args.app_id)
