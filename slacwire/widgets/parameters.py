from qtpy.QtWidgets import (
    QGroupBox,
    QTabWidget,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

        self._wire = None

    def _on_tab_changed(self, index):
        if index == 0 and self._wire is not None:
            self._refresh_start_positions()

    @property
    def is_auto_mode(self) -> bool:
        return self.tab_widget.currentIndex() == 0

    def _build_auto_tab(self):
        self.auto_tab = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setVerticalSpacing(4)

        layout.addWidget(QLabel("Start Position"), 0, 1)

        self.use_x_wire_auto = PyDMCheckbox()
        self.use_x_wire_auto.setText("Use X Wire")
        self.use_x_wire_auto.setObjectName("use_x_wire_auto")
        self.use_y_wire_auto = PyDMCheckbox()
        self.use_y_wire_auto.setText("Use Y Wire")
        self.use_y_wire_auto.setObjectName("use_y_wire_auto")
        self.use_u_wire_auto = PyDMCheckbox()
        self.use_u_wire_auto.setText("Use U Wire")
        self.use_u_wire_auto.setObjectName("use_u_wire_auto")

        self.x_start_position = QLineEdit()
        self.y_start_position = QLineEdit()
        self.u_start_position = QLineEdit()

        self.x_apply_button = QPushButton("Apply")
        self.y_apply_button = QPushButton("Apply")
        self.u_apply_button = QPushButton("Apply")

        self.x_apply_button.clicked.connect(lambda: self._apply_auto_range("x"))
        self.y_apply_button.clicked.connect(lambda: self._apply_auto_range("y"))
        self.u_apply_button.clicked.connect(lambda: self._apply_auto_range("u"))

        layout.addWidget(self.use_x_wire_auto, 1, 0)
        layout.addWidget(self.x_start_position, 1, 1)
        layout.addWidget(self.x_apply_button, 1, 2)
        layout.addWidget(self.use_y_wire_auto, 2, 0)
        layout.addWidget(self.y_start_position, 2, 1)
        layout.addWidget(self.y_apply_button, 2, 2)
        layout.addWidget(self.use_u_wire_auto, 3, 0)
        layout.addWidget(self.u_start_position, 3, 1)
        layout.addWidget(self.u_apply_button, 3, 2)

        self.center_on_mean_button = QPushButton("Center on Last Mean")
        layout.addWidget(self.center_on_mean_button, 4, 1)

        self.auto_tab.setLayout(layout)

    def update_from_wire(self, wire):
        """Bind auto tab checkboxes to PVs and populate start positions."""
        self._wire = wire
        self._refresh_start_positions()
        for plane in ("x", "y", "u"):
            use_pv = getattr(wire.controls_information.PVs, f"use_{plane}_wire", None)
            if use_pv is not None:
                checkbox = getattr(self, f"use_{plane}_wire_auto")
                checkbox.channel = use_pv.pvname

    def _apply_auto_range(self, plane):
        if self._wire is None:
            return
        text = getattr(self, f"{plane}_start_position").text()
        try:
            start = int(text)
        except ValueError:
            return
        self._wire.set_range_from_start(plane, start)

    def _refresh_start_positions(self):
        if self._wire is None:
            return
        for plane in ("x", "y", "u"):
            pv_obj = getattr(self._wire.controls_information.PVs, f"{plane}_wire_inner", None)
            if pv_obj is not None:
                val = pv_obj.get()
                if val is not None:
                    getattr(self, f"{plane}_start_position").setText(str(int(val)))

    def _build_override_tab(self):
        self.override_tab = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setVerticalSpacing(4)

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
