"""Exercise installer extraction/upgrade/uninstall and frozen app with isolated settings."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT/'.release'
VERSION = (ROOT/'VERSION').read_text(encoding='utf-8').strip()
setup = OUT/f'XiaoxuePet-{VERSION}-Setup.exe'
env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
with tempfile.TemporaryDirectory(prefix='verify-', dir=OUT) as temp:
    test = Path(temp).resolve()
    if not test.is_relative_to(OUT.resolve()):
        raise RuntimeError('Test path escaped output directory')
    target = test/'自定义位置 with spaces'/'桌宠'
    env['LOCALAPPDATA'] = str(test/'settings')
    def run(args):
        result = subprocess.run([str(x) for x in args], env=env, cwd=test, timeout=90)
        if result.returncode:
            error = test/'settings/XiaoxuePet/startup-error.log'
            if error.exists():
                print(error.read_text(encoding='utf-8'), flush=True)
            result.check_returncode()
    def rejects(args):
        result = subprocess.run([str(x) for x in args], env=env, cwd=test, timeout=90)
        assert result.returncode == 1, 'Unsafe or conflicting destination accepted'
    rejects([setup, '--validate-path-test', '.\\relative'])
    rejects([setup, '--validate-path-test', target.anchor])
    run([setup, '--validate-path-test', target])
    run([setup, '--upgrade-path-test', target, target])
    rejects([setup, '--upgrade-path-test', target, test/'existing-install'])
    occupied = test/'other-files'
    occupied.mkdir()
    sentinel = occupied/'untouched.txt'
    sentinel.write_text('keep', encoding='utf-8')
    rejects([setup, '--extract-test', occupied])
    assert sentinel.read_text() == 'keep' and len(list(occupied.iterdir())) == 1
    run([setup, '--extract-test', target])
    assert (target/'XiaoxuePet.exe').is_file()
    assert (target/'Uninstall.exe').is_file()
    assert (target/'_internal/sprites-anime/prepared/238/heart-motion/heart_chest/40.png').is_file()
    for height in (119, 187, 238):
        for action, count in (('walk', 72), ('wave', 54), ('drink', 27)):
            directory = target/f'_internal/sprites-anime/prepared/{height}/action-motion/{action}'
            manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
            assert manifest['count'] == count
            assert all((directory/f'{index}.png').is_file() for index in range(count))
    assert not (target/'_internal/sprites-anime/prepared/306').exists()
    assert not list(target.rglob('cv2*.pyd'))
    assert not list(target.rglob('pynvml*'))
    run([target/'XiaoxuePet.exe', '--smoke-test'])
    assert (test/'settings/XiaoxuePet/config.json').is_file()
    assert not (target/'config.json').exists()
    note = target/'keep-my-note.txt'
    note.write_text('user-added file must survive upgrade and uninstall', encoding='utf-8')
    run([setup, '--extract-test', target])
    assert note.read_text(encoding='utf-8').startswith('user-added')
    run([target/'XiaoxuePet.exe', '--smoke-test'])
    run([setup, '--uninstall-test', target])
    assert note.is_file()
    assert not (target/'XiaoxuePet.exe').exists()
    assert (test/'settings/XiaoxuePet/config.json').is_file()
result = {'frozen_app_smoke_test': 'passed', 'installer_extract': 'passed',
          'custom_path_unicode_and_spaces': 'passed', 'relative_and_drive_root_rejected': 'passed',
          'upgrade_location_conflict_rejected': 'passed', 'nonempty_foreign_folder_preserved': 'passed',
          'installer_upgrade': 'passed', 'uninstall_preserves_unknown_files_and_settings': 'passed',
          'registry_and_shortcuts': 'not mutated by automated test',
          'network_calls': 'not exercised', 'platform': 'local Windows x64'}
(OUT/'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result), flush=True)
