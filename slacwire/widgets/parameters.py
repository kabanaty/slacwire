from qtpy.QtWidgets import (
    QGroupBox,
    QTabWidget,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
)
from pydm.widgets import PyDMLineEdit, PyDMCheckbox


class ParametersWidget(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Parameters", parent)

        self.tab_widget = QTabWidget()

        self._build_auto_tab()
        self._build_override_tab()

        self.tab_widget.addTab(self.auto_tab, "Auto")
        self.tab_widget.addTab(self.override_tab, "Override")

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    @property
    def is_auto_mode(self) -> bool:
        return self.tab_widget.currentIndex() == 0

    def _build_auto_tab(self):
        self.auto_tab = QWidget()
        layout = QGridLayout()

        layout.addWidget(QLabel("Start Position"), 0, 1)

        self.use_x_wire_auto = QCheckBox("Use X Wire")
        self.use_y_wire_auto = QCheckBox("Use Y Wire")
        self.use_u_wire_auto = QCheckBox("Use U Wire")

        self.x_start_position = QSpinBox()
        self.y_start_position = QSpinBox()
        self.u_start_position = QSpinBox()

        for spinbox in (self.x_start_position, self.y_start_position, self.u_start_position):
            spinbox.setRange(-50000, 50000)
            spinbox.setSuffix(" µm")

        layout.addWidget(self.use_x_wire_auto, 1, 0)
        layout.addWidget(self.x_start_position, 1, 1)
        layout.addWidget(self.use_y_wire_auto, 2, 0)
        layout.addWidget(self.y_start_position, 2, 1)
        layout.addWidget(self.use_u_wire_auto, 3, 0)
        layout.addWidget(self.u_start_position, 3, 1)

        self.auto_tab.setLayout(layout)

    def _build_override_tab(self):
        self.override_tab = QWidget()
        layout = QGridLayout()

        layout.addWidget(QLabel("Inner"), 0, 1)
        layout.addWidget(QLabel("Outer"), 0, 2)

        self.use_x_wire = PyDMCheckbox()
        self.use_x_wire.setText("Use X Wire")
        self.use_x_wire.setObjectName("use_x_wire")
        self.x_wire_inner = PyDMLineEdit()
        self.x_wire_inner.setObjectName("x_wire_inner")
        self.x_wire_outer = PyDMLineEdit()
        self.x_wire_outer.setObjectName("x_wire_outer")

        self.use_y_wire = PyDMCheckbox()
        self.use_y_wire.setText("Use Y Wire")
        self.use_y_wire.setObjectName("use_y_wire")
        self.y_wire_inner = PyDMLineEdit()
        self.y_wire_inner.setObjectName("y_wire_inner")
        self.y_wire_outer = PyDMLineEdit()
        self.y_wire_outer.setObjectName("y_wire_outer")

        self.use_u_wire = PyDMCheckbox()
        self.use_u_wire.setText("Use U Wire")
        self.use_u_wire.setObjectName("use_u_wire")
        self.u_wire_inner = PyDMLineEdit()
        self.u_wire_inner.setObjectName("u_wire_inner")
        self.u_wire_outer = PyDMLineEdit()
        self.u_wire_outer.setObjectName("u_wire_outer")

        self.scan_pulses = PyDMLineEdit()
        self.scan_pulses.setObjectName("scan_pulses")

        layout.addWidget(self.use_x_wire, 1, 0)
        layout.addWidget(self.x_wire_inner, 1, 1)
        layout.addWidget(self.x_wire_outer, 1, 2)

        layout.addWidget(self.use_y_wire, 2, 0)
        layout.addWidget(self.y_wire_inner, 2, 1)
        layout.addWidget(self.y_wire_outer, 2, 2)

        layout.addWidget(self.use_u_wire, 3, 0)
        layout.addWidget(self.u_wire_inner, 3, 1)
        layout.addWidget(self.u_wire_outer, 3, 2)

        layout.addWidget(QLabel("Scan Pulses"), 4, 1)
        layout.addWidget(self.scan_pulses, 4, 2)

        self.override_tab.setLayout(layout)
