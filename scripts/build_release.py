"""Build the Windows app and local distribution files; never publishes online."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION').read_text(encoding='utf-8').strip()


def run(args, **kwargs):
    print('Running:', ' '.join(str(x) for x in args[:4]), flush=True)
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)


def zip_directory(directory, output, prefix=''):
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in sorted(directory.rglob('*')):
            if file.is_file():
                archive.write(file, (Path(prefix)/file.relative_to(directory)).as_posix())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'.release')
    parser.add_argument('--skip-app', action='store_true', help='Reuse the already built app directory')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or output == ROOT.parent or output == Path(output.anchor):
        raise SystemExit('Choose a dedicated output directory')
    output.mkdir(parents=True, exist_ok=True)
    run([sys.executable, ROOT/'packaging/collect_licenses.py'])
    if not args.skip_app:
        build_env = dict(os.environ)
        windir = Path(os.environ.get('WINDIR', 'C:/Windows'))
        build_env['PATH'] = os.pathsep.join(map(str, (Path(sys.executable).parent, Path(sys.base_prefix),
                                                       windir/'System32', windir)))
        run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', output/'app',
             '--workpath', output/'build', ROOT/'packaging/xiaoxue-pet.spec'], env=build_env)
    app = output/'app/XiaoxuePet'
    if not (app/'XiaoxuePet.exe').is_file():
        raise SystemExit('App build missing')
    shutil.copytree(ROOT/'packaging/third-party-licenses', app/'_internal/third-party-licenses', dirs_exist_ok=True)
    csc = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not csc.is_file():
        raise SystemExit('Windows .NET Framework 4.x C# compiler is required for the installer')
    common = [csc, '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
              '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
              '/reference:System.IO.Compression.dll', '/reference:Microsoft.CSharp.dll',
              '/win32icon:'+str(ROOT/'companion-avatar.ico')]
    run(common + ['/define:UNINSTALLER', '/out:'+str(app/'Uninstall.exe'), ROOT/'packaging/Setup.cs'])
    shutil.copy2(ROOT/'LICENSE', app/'LICENSE.txt')
    shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md', app/'THIRD_PARTY_NOTICES.md')
    (app/'使用说明.txt').write_text(
        '小薛同学桌宠 '+VERSION+'\n\n双击 XiaoxuePet.exe 启动，双击人物打开快捷动作。\n'
        '右键人物或托盘图标可设置、隐藏和退出。\n'
        '请保留完整 _internal 目录。普通陪伴不需要 API Key。\n'
        '个人设置：%LOCALAPPDATA%\\XiaoxuePet\\。不要分享配置文件。\n'
        '安装版请使用 Uninstall.exe 卸载；免安装版退出后删除解压目录即可。\n'
        '源码、完整截图与操作文档见配套 Source.zip。\n', encoding='utf-8')
    payload = output/'payload.zip'
    zip_directory(app, payload)
    setup = output/f'XiaoxuePet-{VERSION}-Setup.exe'
    run(common + ['/out:'+str(setup), '/resource:'+str(payload)+',payload.zip',
                  '/resource:'+str(ROOT/'sprites-anime/prepared/238/正面.png')+',avatar.png', ROOT/'packaging/Setup.cs'])
    portable = output/f'XiaoxuePet-{VERSION}-Windows-x64.zip'
    zip_directory(app, portable, 'XiaoxuePet')
    for file in (setup, portable):
        print(file.name, round(file.stat().st_size/2**20, 2), 'MiB', flush=True)
    sums = '\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in (setup, portable))+'\n'
    (output/'SHA256SUMS.txt').write_text(sums, encoding='ascii')


if __name__ == '__main__':
    main()
