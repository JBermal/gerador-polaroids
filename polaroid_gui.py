#!/usr/bin/env python3
"""
Interface gráfica para gerar fotos Polaroid, 3x4 ou formatos personalizados.
Dependências: PyQt6 + Pillow (via photo_engine).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from photo_engine import (
    PRESETS,
    PhotoFrameConfig,
    default_output_folder,
    process_files,
)

MAX_FILES = 50
IMAGE_FILTER = "Imagens (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


class ProcessWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int, list)

    def __init__(self, files: list[Path], output_folder: Path, config: PhotoFrameConfig):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
        self.config = config

    def run(self):
        def on_progress(current, total, name):
            self.progress.emit(current, total, name)

        result = process_files(
            self.files,
            self.output_folder,
            self.config,
            progress_callback=on_progress,
        )
        self.finished.emit(*result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerador de Polaroids & 3x4")
        self.setMinimumSize(720, 560)
        self.resize(820, 640)
        self._files: list[Path] = []
        self._worker: ProcessWorker | None = None
        self._syncing_fields = False
        self._apply_window_icon()
        self._build_ui()

    def _apply_window_icon(self):
        logo_path = resource_path("assets", "logo.png")
        if logo_path.exists():
            icon = QIcon(str(logo_path))
            self.setWindowIcon(icon)

    def _build_ui(self):
        outer = QWidget()
        self.setCentralWidget(outer)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(10, 10, 10, 6)

        content = QHBoxLayout()
        outer_layout.addLayout(content, 1)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        header_title = QLabel("Gerador de Polaroids & 3x4")
        header_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_subtitle = QLabel("Configure o tamanho de saída e as margens")
        header_subtitle.setStyleSheet("color: #666;")
        left_panel.addWidget(header_title)
        left_panel.addWidget(header_subtitle)

        settings_box = QGroupBox("Configurações")
        settings_box.setMinimumWidth(340)
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setSpacing(10)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Modelo:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()) + ["Personalizado"])
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.preset_combo, 1)
        settings_layout.addLayout(preset_row)

        size_box = QGroupBox("Tamanho de saída")
        size_form = QFormLayout(size_box)
        size_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.frame_width = self._cm_spin(6.5)
        self.frame_height = self._cm_spin(8.5)
        size_form.addRow("Largura:", self.frame_width)
        size_form.addRow("Altura:", self.frame_height)
        settings_layout.addWidget(size_box)

        margins_box = QGroupBox("Margens (bordas)")
        margins_form = QFormLayout(margins_box)
        margins_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.margin_top = self._cm_spin(0.5)
        self.margin_left = self._cm_spin(0.5)
        self.margin_bottom = self._cm_spin(2.5)
        self.margin_right = self._cm_spin(0.5)
        margins_form.addRow("Superior:", self.margin_top)
        margins_form.addRow("Esquerda:", self.margin_left)
        margins_form.addRow("Inferior:", self.margin_bottom)
        margins_form.addRow("Direita:", self.margin_right)
        settings_layout.addWidget(margins_box)

        photo_box = QGroupBox("Área da foto (calculada)")
        photo_form = QFormLayout(photo_box)
        photo_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.photo_width = self._cm_spin(5.5)
        self.photo_height = self._cm_spin(5.5)
        self.photo_width.setReadOnly(True)
        self.photo_height.setReadOnly(True)
        self.photo_width.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.photo_height.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        photo_form.addRow("Largura:", self.photo_width)
        photo_form.addRow("Altura:", self.photo_height)
        settings_layout.addWidget(photo_box)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setMinimumWidth(120)
        self.dpi_spin.valueChanged.connect(self._update_font_size_preview)
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel("Resolução:"))
        dpi_row.addWidget(self.dpi_spin)
        dpi_row.addStretch()
        settings_layout.addLayout(dpi_row)

        self.shadow_check = QCheckBox("Adicionar sombra (descontada do tamanho de saída)")
        self.shadow_check.toggled.connect(self._on_shadow_toggled)
        settings_layout.addWidget(self.shadow_check)

        self.size_hint_label = QLabel()
        self.size_hint_label.setWordWrap(True)
        self.size_hint_label.setStyleSheet("color: #666; font-size: 11px;")
        settings_layout.addWidget(self.size_hint_label)

        caption_box = QGroupBox("Legenda")
        caption_layout = QVBoxLayout(caption_box)
        self.caption_check = QCheckBox("Usar nome do arquivo na legenda")
        #self.caption_check.setChecked(False)
        self.caption_check.toggled.connect(self._on_caption_mode_changed)
        self.custom_caption_edit = QLineEdit()
        self.custom_caption_edit.setPlaceholderText("Digite a legenda personalizada...")
        self.custom_caption_edit.setEnabled(False)
        caption_layout.addWidget(self.caption_check)
        caption_layout.addWidget(self.custom_caption_edit)

        font_row = QHBoxLayout()
        self.font_auto_check = QCheckBox("Tamanho automático da fonte")
        self.font_auto_check.setChecked(True)
        self.font_auto_check.toggled.connect(self._on_font_auto_changed)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 300)
        self.font_size_spin.setValue(50)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setMinimumWidth(100)
        self.font_size_spin.setEnabled(False)
        font_row.addWidget(self.font_auto_check)
        font_row.addStretch()
        font_row.addWidget(self.font_size_spin)
        caption_layout.addLayout(font_row)

        settings_layout.addWidget(caption_box)

        output_box = QGroupBox("Pasta de saída")
        output_layout = QHBoxLayout(output_box)
        self.output_edit = QLineEdit(str(default_output_folder()))
        browse_output_btn = QPushButton("Selecionar pasta")
        browse_output_btn.clicked.connect(self._browse_output_folder)
        output_layout.addWidget(self.output_edit, 1)
        output_layout.addWidget(browse_output_btn)

        self.generate_btn = QPushButton("Converter Fotos")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.clicked.connect(self._generate)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Pronto.")
        self.status_label.setWordWrap(True)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(settings_box)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        left_panel.addWidget(scroll_area, 1)
        left_panel.addWidget(output_box)
        left_panel.addWidget(self.generate_btn)
        left_panel.addWidget(self.progress_bar)
        left_panel.addWidget(self.status_label)

        files_box = QGroupBox("Arquivos de entrada (máx. 50)")
        files_layout = QVBoxLayout(files_box)
        self.files_list = QListWidget()
        files_layout.addWidget(self.files_list, 1)

        files_buttons = QHBoxLayout()
        load_btn = QPushButton("Carregar arquivos")
        load_btn.clicked.connect(self._load_files)
        clear_btn = QPushButton("Limpar lista")
        clear_btn.clicked.connect(self._clear_files)
        files_buttons.addWidget(load_btn)
        files_buttons.addWidget(clear_btn)
        files_layout.addLayout(files_buttons)

        self.files_count_label = QLabel("0 arquivo(s) selecionado(s)")
        files_layout.addWidget(self.files_count_label)

        content.addLayout(left_panel, 1)
        content.addWidget(files_box, 1)

        footer = QLabel("Desenvolvido por Plugintech!")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; padding: 2px;")
        outer_layout.addWidget(footer)

        site_link = QLabel('<a href="https://plugintech.com.br">Acesse: plugintech.com.br</a>')
        site_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        site_link.setOpenExternalLinks(True)
        site_link.setStyleSheet("font-size: 11px; padding-bottom: 2px;")
        outer_layout.addWidget(site_link)

        for spin in (
            self.frame_width,
            self.frame_height,
            self.margin_top,
            self.margin_left,
            self.margin_bottom,
            self.margin_right,
        ):
            spin.valueChanged.connect(self._on_dimensions_changed)

        self._on_shadow_toggled(self.shadow_check.isChecked())
        self._sync_photo_fields()
        self._on_font_auto_changed(self.font_auto_check.isChecked())

    def _cm_spin(self, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 50.0)
        spin.setDecimals(2)
        #spin.setSingleStep(0.1)
        spin.setSuffix(" cm")
        spin.setValue(value)
        spin.setMinimumWidth(120)
        spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return spin

    def _build_temp_config(self) -> PhotoFrameConfig:
        return PhotoFrameConfig(
            frame_width_cm=self.frame_width.value(),
            frame_height_cm=self.frame_height.value(),
            margin_top_cm=self.margin_top.value(),
            margin_left_cm=self.margin_left.value(),
            margin_bottom_cm=self.margin_bottom.value(),
            margin_right_cm=self.margin_right.value(),
            dpi=self.dpi_spin.value(),
            with_shadow=self.shadow_check.isChecked(),
        )

    def _sync_photo_fields(self):
        config = self._build_temp_config()
        photo_w, photo_h = config.photo_size_from_margins_cm()
        self._syncing_fields = True
        self.photo_width.setValue(round(photo_w, 2))
        self.photo_height.setValue(round(photo_h, 2))
        self._syncing_fields = False
        self._update_size_hint(config)
        self._update_font_size_preview()

    def _update_size_hint(self, config: PhotoFrameConfig):
        inner_w, inner_h = config.inner_frame_size_cm()
        if config.with_shadow:
            discount = config.shadow_extra_cm()
            self.size_hint_label.setText(
                f"Moldura interna: {inner_w:.2f} x {inner_h:.2f} cm.\n"
                #f"(sombra descontada: {discount:.2f} cm por lado). "
                f"Saída final: {config.frame_width_cm:.2f} x {config.frame_height_cm:.2f} cm."
            )
        else:
            self.size_hint_label.setText(
                f"Saída final: {config.frame_width_cm:.2f} x {config.frame_height_cm:.2f} cm."
            )

    def _on_dimensions_changed(self):
        if self._syncing_fields:
            return
        if self.preset_combo.currentText() != "Personalizado":
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentText("Personalizado")
            self.preset_combo.blockSignals(False)
        self._sync_photo_fields()

    def _on_shadow_toggled(self, _checked: bool):
        self._sync_photo_fields()

    def _on_caption_mode_changed(self, use_filename: bool):
        self.custom_caption_edit.setEnabled(not use_filename)
        if use_filename:
            self.custom_caption_edit.clear()

    def _on_font_auto_changed(self, auto: bool):
        self.font_size_spin.setEnabled(not auto)

    def _update_font_size_preview(self):
        if not self.font_auto_check.isChecked():
            return
        config = self._build_temp_config()
        inner_w, _ = config.inner_frame_size_cm()
        auto_size = config.resolve_font_size_px(inner_w)
        self.font_size_spin.blockSignals(True)
        self.font_size_spin.setValue(auto_size)
        self.font_size_spin.blockSignals(False)

    def _mark_custom_preset(self):
        if self.preset_combo.currentText() != "Personalizado":
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentText("Personalizado")
            self.preset_combo.blockSignals(False)

    def _on_preset_changed(self, preset_name: str):
        if preset_name == "Personalizado":
            return
        preset = PRESETS[preset_name]
        self._syncing_fields = True
        widgets = (
            (self.frame_width, preset.frame_width_cm),
            (self.frame_height, preset.frame_height_cm),
            (self.margin_top, preset.margin_top_cm),
            (self.margin_left, preset.margin_left_cm),
            (self.margin_bottom, preset.margin_bottom_cm),
            (self.margin_right, preset.margin_right_cm),
        )
        for widget, value in widgets:
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self._syncing_fields = False

        self.caption_check.setChecked(preset.use_filename_caption)
        self.custom_caption_edit.clear()
        self.font_auto_check.setChecked(preset.caption_font_auto)
        self.font_size_spin.setValue(preset.caption_font_size)
        self.shadow_check.setChecked(preset.with_shadow)
        self._sync_photo_fields()

    def _browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta de saída",
            self.output_edit.text() or str(default_output_folder()),
        )
        if folder:
            self.output_edit.setText(folder)

    def _load_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar imagens",
            str(Path.home()),
            IMAGE_FILTER,
        )
        if not files:
            return

        selected = [Path(path) for path in files[:MAX_FILES]]
        if len(files) > MAX_FILES:
            QMessageBox.warning(
                self,
                "Limite de arquivos",
                f"Apenas os primeiros {MAX_FILES} arquivos foram adicionados.",
            )

        self._files = selected
        self.files_list.clear()
        for file_path in self._files:
            self.files_list.addItem(file_path.name)
        self._update_files_count()

    def _clear_files(self):
        self._files.clear()
        self.files_list.clear()
        self._update_files_count()

    def _update_files_count(self):
        self.files_count_label.setText(f"{len(self._files)} arquivo(s) selecionado(s)")

    def _build_config(self) -> PhotoFrameConfig:
        preset_name = self.preset_combo.currentText()
        prefix = PRESETS[preset_name].output_prefix if preset_name in PRESETS else "foto_"
        config = PhotoFrameConfig(
            frame_width_cm=self.frame_width.value(),
            frame_height_cm=self.frame_height.value(),
            margin_top_cm=self.margin_top.value(),
            margin_left_cm=self.margin_left.value(),
            margin_bottom_cm=self.margin_bottom.value(),
            margin_right_cm=self.margin_right.value(),
            dpi=self.dpi_spin.value(),
            use_filename_caption=self.caption_check.isChecked(),
            custom_caption=self.custom_caption_edit.text(),
            caption_font_auto=self.font_auto_check.isChecked(),
            caption_font_size=self.font_size_spin.value(),
            with_shadow=self.shadow_check.isChecked(),
            output_prefix=prefix,
        )
        config.sync_photo_from_margins()
        return config

    def _set_busy(self, busy: bool):
        self.generate_btn.setEnabled(not busy)
        self.preset_combo.setEnabled(not busy)

    def _generate(self):
        if not self._files:
            QMessageBox.warning(self, "Atenção", "Selecione ao menos um arquivo de imagem.")
            return

        output_folder = Path(self.output_edit.text().strip())
        if not output_folder:
            QMessageBox.warning(self, "Atenção", "Informe a pasta de saída.")
            return

        if not self.caption_check.isChecked() and not self.custom_caption_edit.text().strip():
            reply = QMessageBox.question(
                self,
                "Sem legenda",
                "Nenhuma legenda foi definida. Deseja continuar sem legenda?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        config = self._build_config()
        error = config.validate()
        if error:
            QMessageBox.warning(self, "Configuração inválida", error)
            return

        self._set_busy(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Processando...")

        self._worker = ProcessWorker(self._files, output_folder, config)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str):
        percent = int((current / total) * 100) if total else 0
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Processando ({current}/{total}): {name}")

    def _on_finished(self, success: int, total: int, errors: list):
        self.progress_bar.setValue(100)

        if errors:
            details = "\n".join(errors[:8])
            if len(errors) > 8:
                details += f"\n... e mais {len(errors) - 8} erro(s)."
            QMessageBox.warning(
                self,
                "Concluído com avisos",
                f"{success}/{total} imagem(ns) gerada(s).\n\nErros:\n{details}",
            )
            self.status_label.setText(f"Concluído com erros: {success}/{total} salva(s).")
        else:
            QMessageBox.information(
                self,
                "Sucesso",
                f"{success} imagem(ns) gerada(s) em:\n{self.output_edit.text()}",
            )
            self.status_label.setText(f"Concluído: {success}/{total} imagem(ns) salva(s).")

        self._set_busy(False)
        self._worker = None


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    logo_path = resource_path("assets", "logo.png")
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
