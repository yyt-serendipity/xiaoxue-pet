"""Bundle only reusable code and licenses; never embeds an existing person's artwork."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('main.py', '桌宠.py', 'animation.py', 'app_paths.py', 'companion.py',
         'companion_lines.py', 'desktop_geometry.py', 'game_guard.py', 'pet_theme.py', 'body_motion.py', 'test_body_motion.py',
         'sprite_store.py', 'prepare_assets.py', 'prepare_unified_art.py', 'build_heart_motion.py', 'build_action_motion.py',
         'test_animation.py', 'test_app_paths.py', 'test_companion.py', 'test_desktop_geometry.py',
         'test_guard.py', 'test_playroom.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'VERSION',
         'requirements.txt', 'requirements-build.txt', 'requirements-lock.txt',
         'asset-build-requirements.txt', 'config.example.json', '启动桌宠.bat', '.gitignore',
         'scripts/build_release.py', 'scripts/verify_release.py', 'scripts/compare_motion.py', 'scripts/compare_body_motion.py', 'scripts/preview_tempo.py',
         'packaging/xiaoxue-pet.spec', 'packaging/Setup.cs', 'packaging/collect_licenses.py')
README = '''# 人物照片桌宠项目

此目录由小薛同学桌宠 skill 初始化。人物原画尚未生成，必须按 skill 的素材契约制作、检查和编译后再启动。

1. 使用 skill 的照片流程生成完整角色、三视图及动作图集；不要把输入真人照片放入公开仓库。
2. 安装 requirements.txt；离线构建工具按 asset-build-requirements.txt 安装到 .asset-build-tools。
3. 运行 skill 的 validate_art.py --stage raw，再运行 prepare_assets.py。
4. 运行 validate_art.py --stage prepared --make-icon 生成当前人物图标，再用 render_preview.py 查看动作。
5. 运行 python -m unittest discover -p "test_*.py" -q；python main.py 启动。
6. Windows 下安装 requirements-build.txt，运行 scripts/build_release.py 和 scripts/verify_release.py。

包含轻量完整人物动画、简单陪伴操作、30 分钟看书专注、提醒和自动避让。图像生成只在制作时进行；普通桌宠不需要 Key，DeepSeek Key 只用于可选文字聊天。

本项目使用独立应用 ID XiaoxuePet，安装版数据在 %LOCALAPPDATA%\\XiaoxuePet。源码版数据在本目录；不要公开 config.json 和 companion-state.json。不含预置人物、Key、个人配置或输入照片。

bootstrap 后显示名与应用 ID 已按新项目替换，源代码中的固定 skill/spec 文件名不影响独立运行。打包产物仍未签名，构建测试不代替其他电脑的兼容性测试。许可证见 LICENSE 和 THIRD_PARTY_NOTICES.md。
'''


def main():
    paths = [ROOT/name for name in FILES]
    paths += sorted(p for p in (ROOT/'packaging/third-party-licenses').rglob('*') if p.is_file())
    target = ROOT/'skills/xiaoxue-pet/assets/runtime-template.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    secret = ''
    if (ROOT/'config.json').exists():
        secret = str(json.loads((ROOT/'config.json').read_text(encoding='utf-8')).get('ds_api_key', ''))
    manifest = {}
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            data = path.read_bytes()
            if (len(secret) >= 8 and secret.encode() in data) or re.search(rb'(?i)sk-[a-z0-9]{24,}', data):
                raise RuntimeError(f'Credential-like content in {path.name}; contents not printed')
            name = path.relative_to(ROOT).as_posix()
            archive.writestr(name, data)
            manifest[name] = hashlib.sha256(data).hexdigest()
        archive.writestr('README.md', README.encode())
        manifest['README.md'] = hashlib.sha256(README.encode()).hexdigest()
        archive.writestr('TEMPLATE_MANIFEST.json', json.dumps({'files':manifest, 'includes_character_art':False,
                            'includes_personal_settings':False, 'version':(ROOT/'VERSION').read_text().strip()}, indent=2))
    print(f'Code-only template: {len(manifest)} files, {target.stat().st_size / 1024:.1f} KiB')


if __name__ == '__main__':
    main()
