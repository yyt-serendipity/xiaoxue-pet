"""Capture real Qt widgets with temporary, non-personal settings."""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase

app = QApplication([])
QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
spec = importlib.util.spec_from_file_location('capture_pet', ROOT/'桌宠.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.current_avoidance_reason = lambda *args: ''
images = ROOT/'docs/images'
images.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    module.APP_DIR = directory
    module.CONFIG_PATH = str(Path(directory)/'config.json')
    pet = module.PetWindow()
    pet.timer.stop()
    pet.companion.data['name'] = '小薛同学'
    pet.set_mode('still')
    pet.show_companion_panel()
    app.processEvents()
    panel = pet.companion_panel
    panel.tabs.setCurrentIndex(0)
    app.processEvents()
    panel.grab().save(str(images/'companion-panel.png'))
    panel.tabs.setCurrentIndex(1)
    app.processEvents()
    panel.grab().save(str(images/'settings-panel.png'))
    panel.hide()
    pet.quick_panel.popup_at(100, 100)
    app.processEvents()
    pet.quick_panel.grab().save(str(images/'quick-panel.png'))
    pet.quick_panel.hide()
    pet.tray.hide()
    pet.hide()
print('Captured real widgets with temporary settings.')
