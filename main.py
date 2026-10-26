"""Entry point with a local startup-error log, including frozen smoke tests."""
import os
from pathlib import Path
import sys
import traceback

if __name__ == '__main__':
    try:
        from 桌宠 import main
        main()
    except Exception:
        directory = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'XiaoxuePet'
        directory.mkdir(parents=True, exist_ok=True)
        log = directory/'startup-error.log'
        log.write_text(traceback.format_exc(), encoding='utf-8')
        if '--smoke-test' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, '启动未完成，错误详情已保存到：\n'+str(log), '小薛同学桌宠', 16)
        raise SystemExit(1)
