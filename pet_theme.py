"""Shared warm-paper / muted-blue native widget styling."""
STYLE = '''
QWidget {font-family:"Microsoft YaHei UI";font-size:13px;color:#293d4b;}
QDialog,QWidget#foodSurface,QWidget#tabPage {background:#faf8f4;}
QFrame#intro {background:#ecefe9;border:0;border-radius:16px;}
QLabel {background:transparent;}
QLabel#title {font-size:22px;font-weight:600;color:#263d4a;}
QLabel#secondary {font-size:12px;color:#60707a;}
QPushButton,QToolButton {background:#ffffff;border:1px solid #d9dfdf;
 border-radius:9px;padding:8px 12px;}
QPushButton:hover,QToolButton:hover {background:#edf3f6;border-color:#90a8b6;}
QPushButton:pressed,QToolButton:pressed {background:#dce8ef;}
QPushButton:focus,QToolButton:focus,QComboBox:focus,QLineEdit:focus {border:2px solid #537c94;}
QPushButton:disabled {background:#efeeeb;color:#828b90;border-color:#e1e0dc;}
QPushButton:checked {background:#dce8ef;border-color:#6c8a9b;}
QPushButton#primary {background:#456c82;color:#ffffff;border:1px solid #456c82;}
QPushButton#primary:hover {background:#36596d;}
QToolButton#pose {background:transparent;border:1px solid transparent;border-radius:12px;padding:6px;}
QToolButton#pose:hover {background:#eef2ef;border-color:#d5dfdc;}
QToolButton#pose:checked {background:#e0ebf1;border-color:#9ab2bf;}
QToolButton#pose:focus {border:2px solid #537c94;}
QTabWidget::pane {border:0;margin-top:10px;}
QTabBar {background:#ebece7;border-radius:10px;}
QTabBar::tab {background:transparent;color:#586975;padding:10px 22px;margin:3px;border-radius:7px;}
QTabBar::tab:selected {background:#ffffff;color:#2f566d;font-weight:600;}
QTabBar::tab:hover {color:#25475c;background:#f2f4f1;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {width:6px;background:transparent;margin:4px 0;}
QScrollBar::handle:vertical {background:#c4cecd;border-radius:3px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QProgressBar {border:0;background:#e3e7e2;border-radius:3px;}
QProgressBar::chunk {background:#7b9ca8;border-radius:3px;}
QLineEdit,QSpinBox,QComboBox {background:#ffffff;border:1px solid #ccd6d8;border-radius:7px;
 padding:7px 10px;selection-background-color:#456c82;selection-color:white;}
QComboBox QAbstractItemView {background:white;color:#293d4b;selection-background-color:#dce8ef;}
QCheckBox {spacing:8px;}
'''
