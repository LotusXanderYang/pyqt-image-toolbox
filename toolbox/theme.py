"""Native workbench visual tokens: quiet panels, neutral canvas, teal actions."""
STYLE = """
QWidget { color: #263334; font-size: 14px; }
QMainWindow, #root { background: #eff2f1; }
QFrame#header { background: #fcfdfc; border-bottom: 1px solid #d3dcda; }
QFrame#panel { background: #fcfdfc; border: 1px solid #d3dcda; border-radius: 8px; }
QLabel#brand { font-size: 20px; font-weight: 600; }
QLabel#section { font-size: 16px; font-weight: 600; }
QLabel#muted { color: #586966; font-size: 13px; }
QLabel#badge { color: #12665c; background: #e1f1ed; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
QLabel#notice { background: #e4f2ed; color: #245d51; border: 1px solid #b9d9cf; border-radius: 6px; padding: 10px 12px; }
QLabel#notice[error="true"] { background: #fbeceb; color: #92302b; border-color: #e9bdb9; }
QPushButton { background: #fcfdfc; border: 1px solid #b9c6c2; border-radius: 6px; padding: 8px 14px; min-height: 24px; }
QPushButton:hover { background: #eaf1ee; border-color: #657f76; }
QPushButton:pressed { background: #d8e8e1; }
QPushButton:focus { border: 2px solid #13776b; padding: 7px 13px; }
QPushButton#primary { background: #176d62; border-color: #176d62; color: #ffffff; font-weight: 600; }
QPushButton#primary:hover { background: #1d7d70; border-color: #1d7d70; }
QPushButton#primary:pressed { background: #11564e; }
QPushButton#primary:focus { border: 2px solid #093e37; }
QPushButton:disabled, QPushButton#primary:disabled { background: #edf0ee; color: #87948e; border-color: #d7dedb; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #ffffff; border: 1px solid #b4c2bc; border-radius: 5px; padding: 7px; min-height: 24px; selection-background-color: #176d62; }
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #6c827a; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #13776b; padding: 6px; }
QComboBox { padding-right: 24px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #ffffff; color: #263334; selection-background-color: #e0f0e9; selection-color: #145d51; border: 1px solid #b4c2bc; padding: 4px; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 10px 12px; margin: 2px 0; border-radius: 5px; border: 1px solid transparent; }
QListWidget::item:hover { background: #edf4f0; }
QListWidget::item:selected { background: #dceee7; color: #124f45; border: 1px solid #aacdbd; font-weight: 600; }
QListWidget:focus { border: 1px solid #13776b; border-radius: 5px; }
QCheckBox { spacing: 8px; padding: 8px 0; }
QCheckBox::indicator { width: 18px; height: 18px; }
QCheckBox:focus { outline: 1px solid #13776b; }
QScrollArea { background: transparent; border: none; }
QWidget#parameterPage { background: #fcfdfc; }
QScrollBar:vertical { background: #eef2ef; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #b7c4bd; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #eef2ef; height: 10px; }
QScrollBar::handle:horizontal { background: #b7c4bd; border-radius: 4px; min-width: 24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: transparent; width: 8px; height: 8px; }
QGraphicsView { border: none; background: #282c2c; }
QStatusBar { background: #fcfdfc; color: #586966; border-top: 1px solid #d3dcda; }
QStatusBar::item { border: none; }
QProgressBar { background: #dfe8e3; border: none; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #176d62; border-radius: 3px; }
QMenuBar, QMenu { background: #fcfdfc; }
QMenuBar::item:selected, QMenu::item:selected { background: #dceee7; color: #124f45; }
QMenu::item { padding: 8px 24px; }
QToolTip { background: #263334; color: #ffffff; padding: 6px; border: none; }
"""
