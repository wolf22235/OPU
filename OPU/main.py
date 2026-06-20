import sys
import json
import os
import time
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from motor import motor

# =============================================================================
# БЛОК 1: ИМПОРТЫ И ГЛОБАЛЬНЫЕ КОНСТАНТЫ
# =============================================================================
STATE_OFF = 0
STATE_CONNECTING = 1
STATE_AUTHENTICATING = 2
STATE_WORKING = 3
STATE_CONNECTED = 4
STATE_DISCONNECTED = 5
SETTINGS_FILE = "motor_settings.json"

# =============================================================================
# БЛОК 2: СТИЛИ ИНТЕРФЕЙСА
# =============================================================================
STYLES = {
    STATE_OFF: "background-color: #555555; border: 1px solid #333;",
    STATE_CONNECTING: "background-color: orange; border: 1px solid darkorange;",
    STATE_AUTHENTICATING: "background-color: yellow; border: 1px solid gold;",
    STATE_WORKING: "background-color: #00ccff; border: 1px solid #0088aa;",
    STATE_CONNECTED: "background-color: green; border: 1px solid #008800;",
    STATE_DISCONNECTED: "background-color: red; border: 1px solid #880000;"
}

# =============================================================================
# БЛОК 3: КЛАСС РАБОЧЕГО ПОТОКА МОТОРА
# =============================================================================
class MotorWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(int, int)
    powerstep_signal = pyqtSignal(int, int)
    progress_signal = pyqtSignal(int, int, str)
    connection_result_signal = pyqtSignal(int, bool)
    settings_loaded_signal = pyqtSignal(int, dict)

    def __init__(self, motor_instance, motor_num, parent=None):
        super().__init__(parent)
        self.motor = motor_instance
        self.motor_num = motor_num
        self.task_queue = []
        self._is_running = True
        self.lock = QMutex()

    def run(self):
        while self._is_running:
            task = None
            self.lock.lock()
            if self.task_queue:
                task = self.task_queue.pop(0)
            self.lock.unlock()
            if task:
                try:
                    task_type = task.get('type')
                    if task_type == 'connect':
                        self._do_connect(task)
                    elif task_type == 'disconnect':
                        self._do_disconnect()
                    elif task_type == 'move_auto':
                        self._do_auto_move(task)
                    elif task_type == 'stop':
                        self._do_stop()
                    elif task_type == 'home':
                        self._do_home()
                    elif task_type == 'set_zero':
                        self._do_set_zero()
                    elif task_type == 'coords':
                        self._do_coords(task)
                    elif task_type == 'get_settings':
                        self._do_get_settings()
                    elif task_type == 'set_settings':
                        self._do_set_settings(task)
                except Exception as e:
                    self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка в потоке: {str(e)}")
                    self.status_signal.emit(self.motor_num, STATE_DISCONNECTED)
                    self.powerstep_signal.emit(self.motor_num, 0)
            else:
                self.msleep(10)

    def add_task(self, task_dict):
        self.lock.lock()
        self.task_queue.append(task_dict)
        self.lock.unlock()

    def stop_thread(self):
        self._is_running = False
        self.wait()

    def _do_connect(self, task):
        ip = task.get('ip')
        port = task.get('port')
        self.status_signal.emit(self.motor_num, STATE_CONNECTING)
        self.log_signal.emit(f"[Мотор {self.motor_num}] Начало подключения к {ip}:{port}")
        try:
            self.motor.IP = ip
            self.motor.PORT = port
            auth_res = self.motor.authorization()
            if auth_res == 0:
                self.log_signal.emit(f"[Мотор {self.motor_num}] Авторизация успешна")
                self._apply_settings_from_file()
                self.status_signal.emit(self.motor_num, STATE_CONNECTED)
                self.powerstep_signal.emit(self.motor_num, 0)
                self.connection_result_signal.emit(self.motor_num, True)
                self.progress_signal.emit(self.motor_num, 100, "Подключено")
            else:
                raise Exception(f"Код ошибки авторизации: {auth_res}")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка подключения: {str(e)}")
            self.status_signal.emit(self.motor_num, STATE_DISCONNECTED)
            self.powerstep_signal.emit(self.motor_num, 0)
            self.connection_result_signal.emit(self.motor_num, False)
            self.progress_signal.emit(self.motor_num, 0, "Ошибка")

    def _do_disconnect(self):
        try:
            self.motor.end_work()
            self.log_signal.emit(f"[Мотор {self.motor_num}] Соединение разорвано")
        except:
            pass
        finally:
            self.status_signal.emit(self.motor_num, STATE_OFF)
            self.powerstep_signal.emit(self.motor_num, 0)
            self.connection_result_signal.emit(self.motor_num, False)

    def _do_auto_move(self, task):
        direction = task.get('direction')
        speed = task.get('speed', 100)
        self.status_signal.emit(self.motor_num, STATE_WORKING)
        self.powerstep_signal.emit(self.motor_num, 1)
        self.log_signal.emit(f"[Мотор {self.motor_num}] Движение: {direction}, Скорость: {speed}")
        try:
            res = self.motor.run_f_or_r(direction, speed)
            self.log_signal.emit(f"[Мотор {self.motor_num}] Команда отправлена: {res}")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка движения: {e}")
            self._do_stop()

    def _do_stop(self):
        self.log_signal.emit(f"[Мотор {self.motor_num}] Остановка")
        try:
            if hasattr(self.motor, 'hard_stop'):
                self.motor.hard_stop()
        except:
            pass
        finally:
            self.powerstep_signal.emit(self.motor_num, 0)
            self.log_signal.emit(f"[Мотор {self.motor_num}] Остановлен")

    def _do_home(self):
        self.status_signal.emit(self.motor_num, STATE_WORKING)
        self.powerstep_signal.emit(self.motor_num, 1)
        self.log_signal.emit(f"[Мотор {self.motor_num}] Переход в ноль")
        try:
            if hasattr(self.motor, 'go_zero'):
                self.motor.go_zero()
                self.log_signal.emit(f"[Мотор {self.motor_num}] Команда Home отправлена")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка Home: {e}")
            self.powerstep_signal.emit(self.motor_num, 0)

    def _do_set_zero(self):
        self.log_signal.emit(f"[Мотор {self.motor_num}] Задание текущей позиции как 0")
        try:
            if hasattr(self.motor, 'set_zero'):
                self.motor.set_zero()
                self.log_signal.emit(f"[Мотор {self.motor_num}] Точка 0 установлена")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка set_zero: {e}")

    def _do_coords(self, task):
        dist = task.get('dist')
        dir_val = task.get('dir')
        self.status_signal.emit(self.motor_num, STATE_WORKING)
        self.powerstep_signal.emit(self.motor_num, 1)
        self.log_signal.emit(f"[Мотор {self.motor_num}] Перемещение в координату: {dist} ({dir_val})")
        try:
            if hasattr(self.motor, 'move_to_f_or_r'):
                self.motor.move_to_f_or_r(dist, dir_val)
                self.log_signal.emit(f"[Мотор {self.motor_num}] Команда перемещения отправлена")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка перемещения: {e}")
            self.powerstep_signal.emit(self.motor_num, 0)

    def _do_get_settings(self):
        try:
            min_s, max_s = self.motor.get_movement_parameters()
            self.motor.get_mode_parameters()
            settings = {
                "min_speed": min_s, "max_speed": max_s,
                "mode": self.motor.CURENT_OR_VOLTAGE, "motor_type": self.motor.MOTOR_TYPE,
                "microstepping": self.motor.MICROSTEPPING,
                "work_current": self.motor.WORK_CURRENT, "hold_current": self.motor.STOP_CURRENT
            }
            self.settings_loaded_signal.emit(self.motor_num, settings)
            self.log_signal.emit(f"[Мотор {self.motor_num}] Настройки считаны")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка чтения настроек: {e}")

    def _do_set_settings(self, task):
        s = task.get('settings', {})
        try:
            self.motor.CURENT_OR_VOLTAGE = s.get("mode", 1)
            self.motor.MOTOR_TYPE = s.get("motor_type", 30)
            self.motor.MICROSTEPPING = s.get("microstepping", 4)
            self.motor.WORK_CURRENT = s.get("work_current", 10)
            self.motor.STOP_CURRENT = s.get("hold_current", 0)
            min_speed = s.get("min_speed", 100)
            max_speed = s.get("max_speed", 500)
            acceleration = s.get("acceleration", 100)
            deceleration = s.get("deceleration", 200)
            self.motor.set_movement_parameters(min_speed, max_speed, acceleration, deceleration)
            self.motor.set_mode_parameters()
            self.log_signal.emit(f"[Мотор {self.motor_num}] Настройки применены")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка записи настроек: {e}")

    def _apply_settings_from_file(self):
        if not os.path.exists(SETTINGS_FILE): return
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            prefix = "m1_" if self.motor_num == 1 else "m2_"
            if prefix in settings:
                s = settings[prefix]
                self.motor.CURENT_OR_VOLTAGE = s.get("mode", 1)
                self.motor.MOTOR_TYPE = s.get("motor_type", 30)
                self.motor.MICROSTEPPING = s.get("microstepping", 4)
                self.motor.WORK_CURRENT = s.get("work_current", 10)
                self.motor.STOP_CURRENT = s.get("hold_current", 0)
                min_speed = s.get("min_speed", 100)
                max_speed = s.get("max_speed", 500)
                acc = s.get("acceleration", 100)
                dec = s.get("deceleration", 200)
                self.motor.set_movement_parameters(min_speed, max_speed, acc, dec)
                self.motor.set_mode_parameters()
                self.log_signal.emit(f"[Мотор {self.motor_num}] Конфигурация загружена из файла")
        except Exception as e:
            self.log_signal.emit(f"[Мотор {self.motor_num}] Ошибка загрузки конфига: {e}")

# =============================================================================
# БЛОК 4: КЛАСС ОКНА ЛОГОВ
# =============================================================================
class LogWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Логи приложения")
        self.setFixedSize(800, 600)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_area.setFont(QFont("Consolas", 9))
        button_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setStyleSheet("background-color: #aa0000; color: white;")
        self.btn_clear.clicked.connect(self.clear_logs)
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setStyleSheet("background-color: #0088aa; color: white;")
        self.btn_save.clicked.connect(self.save_logs)
        button_layout.addWidget(self.btn_clear)
        button_layout.addWidget(self.btn_save)
        button_layout.addStretch()
        layout.addWidget(self.log_area)
        layout.addLayout(button_layout)
        central_widget.setLayout(layout)

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_area.appendPlainText(log_entry)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.log_area.clear()
        self.log_message("Логи очищены")

    def save_logs(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"motor_logs_{timestamp}.txt"
            log_content = self.log_area.toPlainText()
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(log_content)
            self.log_message(f"Логи сохранены в файл: {filename}")
            QMessageBox.information(self, "Сохранение", f"Логи успешно сохранены в файл: {filename}")
        except Exception as e:
            self.log_message(f"Ошибка сохранения логов: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить логи: {str(e)}")

# =============================================================================
# БЛОК 5: ВИДЖЕТЫ ИНДИКАТОРА И ПРОГРЕССА
# =============================================================================
class StatusIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.setStyleSheet(STYLES[STATE_OFF])
        self.setStyleSheet(f"{self.styleSheet()}border-radius: 25px;")
        self.current_state = STATE_OFF
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate)
        self.brightness = 1.0

    def set_state(self, state):
        self.current_state = state
        base_style = STYLES[state]
        self.setStyleSheet(f"{base_style}border-radius: 25px;")
        if state in [STATE_CONNECTING, STATE_AUTHENTICATING, STATE_WORKING]:
            self.animation_timer.start(150)
        else:
            self.animation_timer.stop()
            self.brightness = 1.0
            self.setStyleSheet(f"{base_style}border-radius: 25px;")

    def animate(self):
        self.brightness = 0.4 if self.brightness == 1.0 else 1.0
        if self.brightness == 0.4:
            self.setStyleSheet("background-color: #333333; border: 1px solid #555; border-radius: 25px;")
        else:
            base_style = STYLES[self.current_state]
            self.setStyleSheet(f"{base_style}border-radius: 25px;")

class ProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #f0f0f0; text-align: center; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00aa00, stop:1 #00ff00); }
        """)
        self.status_label = QLabel("Ожидание")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 9pt; font-weight: bold;")
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def set_progress(self, value, status_text=""):
        self.progress_bar.setValue(value)
        if status_text:
            self.status_label.setText(status_text)
        if value == 100:
            self.status_label.setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
        elif value > 50:
            self.status_label.setStyleSheet("color: orange; font-size: 9pt; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #666; font-size: 9pt; font-weight: bold;")

    def reset(self):
        self.progress_bar.setValue(0)
        self.status_label.setText("Ожидание")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt; font-weight: bold;")

# =============================================================================
# БЛОК 6: ДИАЛОГ НАСТРОЕК
# =============================================================================
class SettingsDialog(QDialog):
    def __init__(self, parent=None, log_callback=None, worker1=None, worker2=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки контроллеров")
        self.setFixedSize(900, 1000)
        self.log_callback = log_callback
        self.worker1 = worker1
        self.worker2 = worker2
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        group1 = QGroupBox("Настройки Мотор 1")
        scroll_layout.addWidget(group1)
        self.setup_motor_group(group1, "m1_")
        group2 = QGroupBox("Настройки Мотор 2")
        scroll_layout.addWidget(group2)
        self.setup_motor_group(group2, "m2_")
        button_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Применить настройки (Записать)")
        self.btn_apply.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.btn_apply)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        scroll_layout.addLayout(button_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        self.setLayout(layout)

    def setup_motor_group(self, group, prefix):
        main_layout = QFormLayout()
        main_layout.setSpacing(8)
        combo_mode = QComboBox()
        combo_mode.addItem("0 - Напряжение", 0)
        combo_mode.addItem("1 - Ток", 1)
        combo_mode.setCurrentIndex(1)
        setattr(self, f"{prefix}combo_mode", combo_mode)
        main_layout.addRow("Режим работы:", combo_mode)
        combo_motor_type = QComboBox()
        combo_motor_type.insertItem(0, "30 - FL60STH86-2008 1.8 deg последовательное", 30)
        combo_motor_type.insertItem(1, "27 - FL60STH65-2008 1.8 deg параллельное", 27)
        combo_motor_type.insertItem(2, "1 - FL42STH33-1334 1.8", 1)
        combo_motor_type.insertItem(3, "4 - FL42STH38-1684 1.8", 4)
        combo_motor_type.setCurrentIndex(0)
        setattr(self, f"{prefix}combo_motor_type", combo_motor_type)
        main_layout.addRow("Тип двигателя:", combo_motor_type)
        combo_micro = QComboBox()
        combo_micro.addItem("1", 0)
        combo_micro.addItem("1/2", 1)
        combo_micro.addItem("1/4", 2)
        combo_micro.addItem("1/8", 3)
        combo_micro.addItem("1/16", 4)
        combo_micro.setCurrentIndex(4)
        setattr(self, f"{prefix}combo_micro", combo_micro)
        main_layout.addRow("Дробление шага:", combo_micro)
        combo_current = QComboBox()
        for i in range(0, 80):
            current = i * 0.1
            combo_current.addItem(f"{i} - {current:.1f}А", i)
        combo_current.setCurrentIndex(1)
        setattr(self, f"{prefix}combo_current", combo_current)
        main_layout.addRow("Рабочий ток:", combo_current)
        combo_hold = QComboBox()
        combo_hold.addItem("0 - 25%", 0)
        combo_hold.addItem("1 - 50%", 1)
        combo_hold.addItem("2 - 75%", 2)
        combo_hold.addItem("3 - 100%", 3)
        combo_hold.setCurrentIndex(0)
        setattr(self, f"{prefix}combo_hold", combo_hold)
        main_layout.addRow("Ток удержания (%):", combo_hold)
        spin_min = QSpinBox()
        spin_min.setRange(0, 950)
        spin_min.setValue(100)
        spin_min.setSuffix(" шагов/сек")
        setattr(self, f"{prefix}spin_min", spin_min)
        main_layout.addRow("Минимальная скорость:", spin_min)
        spin_max = QSpinBox()
        spin_max.setRange(16, 15600)
        spin_max.setValue(500)
        spin_max.setSuffix(" шагов/сек")
        setattr(self, f"{prefix}spin_max", spin_max)
        main_layout.addRow("Максимальная скорость:", spin_max)
        spin_acc = QSpinBox()
        spin_acc.setRange(15, 59000)
        spin_acc.setValue(100)
        spin_acc.setSuffix(" шагов/сек?")
        setattr(self, f"{prefix}spin_acc", spin_acc)
        main_layout.addRow("Ускорение двигателя:", spin_acc)
        spin_dec = QSpinBox()
        spin_dec.setRange(15, 59000)
        spin_dec.setValue(200)
        spin_dec.setSuffix(" шагов/сек?")
        setattr(self, f"{prefix}spin_dec", spin_dec)
        main_layout.addRow("Замедление двигателя:", spin_dec)
        group.setLayout(main_layout)
        btn_layout = QHBoxLayout()
        btn_set = QPushButton("Задать параметры (SET)")
        btn_set.clicked.connect(lambda checked, p=prefix: self.send_parameters(p))
        btn_layout.addWidget(btn_set)
        btn_get = QPushButton("Считать параметры (GET)")
        btn_get.clicked.connect(lambda checked, p=prefix: self.get_parameters(p))
        btn_layout.addWidget(btn_get)
        main_layout.addRow(btn_layout)

    def send_parameters(self, prefix):
        motor_num = 1 if prefix == "m1_" else 2
        worker = self.worker1 if motor_num == 1 else self.worker2
        if not worker:
            QMessageBox.warning(self, "Ошибка", "Поток мотора не инициализирован")
            return
        combo_mode = getattr(self, f"{prefix}combo_mode")
        combo_micro = getattr(self, f"{prefix}combo_micro")
        combo_motor_type = getattr(self, f"{prefix}combo_motor_type")
        combo_current = getattr(self, f"{prefix}combo_current")
        combo_hold = getattr(self, f"{prefix}combo_hold")
        spin_min = getattr(self, f"{prefix}spin_min")
        spin_max = getattr(self, f"{prefix}spin_max")
        spin_acc = getattr(self, f"{prefix}spin_acc")
        spin_dec = getattr(self, f"{prefix}spin_dec")
        settings = {
            "mode": combo_mode.itemData(combo_mode.currentIndex()),
            "motor_type": combo_motor_type.itemData(combo_motor_type.currentIndex()),
            "microstepping": combo_micro.itemData(combo_micro.currentIndex()),
            "work_current": combo_current.itemData(combo_current.currentIndex()),
            "hold_current": combo_hold.itemData(combo_hold.currentIndex()),
            "min_speed": spin_min.value(),
            "max_speed": spin_max.value(),
            "acceleration": spin_acc.value(),
            "deceleration": spin_dec.value()
        }
        worker.add_task({'type': 'set_settings', 'settings': settings})
        self.save_settings_json(prefix, settings)
        QMessageBox.information(self, "Message", f"Команда на запись настроек Мотор {motor_num} отправлена")

    def get_parameters(self, prefix):
        motor_num = 1 if prefix == "m1_" else 2
        worker = self.worker1 if motor_num == 1 else self.worker2
        if worker:
            worker.add_task({'type': 'get_settings'})
        QMessageBox.information(self, "Info", "Запрос на чтение отправлен. Проверьте логи.")

    def apply_settings(self):
        self.save_settings()
        QMessageBox.information(self, "Message", "Настройки сохранены в файл конфигурации")

    def save_settings_json(self, prefix, settings):
        try:
            existing = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            existing[prefix] = settings
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if self.log_callback: self.log_callback(f"Ошибка сохранения файла: {str(e)}")

    def save_settings(self):
        prefixes = ["m1_", "m2_"]
        all_settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                all_settings = json.load(f)
        for prefix in prefixes:
            combo_mode = getattr(self, f"{prefix}combo_mode", None)
            if not combo_mode: continue
            settings = {
                "mode": combo_mode.itemData(combo_mode.currentIndex()),
                "motor_type": getattr(self, f"{prefix}combo_motor_type").itemData(getattr(self, f"{prefix}combo_motor_type").currentIndex()),
                "microstepping": getattr(self, f"{prefix}combo_micro").itemData(getattr(self, f"{prefix}combo_micro").currentIndex()),
                "work_current": getattr(self, f"{prefix}combo_current").itemData(getattr(self, f"{prefix}combo_current").currentIndex()),
                "hold_current": getattr(self, f"{prefix}combo_hold").itemData(getattr(self, f"{prefix}combo_hold").currentIndex()),
                "min_speed": getattr(self, f"{prefix}spin_min").value(),
                "max_speed": getattr(self, f"{prefix}spin_max").value(),
                "acceleration": getattr(self, f"{prefix}spin_acc").value(),
                "deceleration": getattr(self, f"{prefix}spin_dec").value()
            }
            all_settings[prefix] = settings
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_settings, f, ensure_ascii=False, indent=2)
            if self.log_callback: self.log_callback("Настройки сохранены в файл")
        except Exception as e:
            if self.log_callback: self.log_callback(f"Ошибка сохранения файла: {str(e)}")

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE): return
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            prefixes = ["m1_", "m2_"]
            for prefix in prefixes:
                if prefix in settings:
                    s = settings[prefix]
                    combo_mode = getattr(self, f"{prefix}combo_mode", None)
                    if not combo_mode: continue
                    idx = combo_mode.findData(s.get("mode", 1))
                    if idx >= 0: combo_mode.setCurrentIndex(idx)
                    idx = getattr(self, f"{prefix}combo_motor_type").findData(s.get("motor_type", 30))
                    if idx >= 0: getattr(self, f"{prefix}combo_motor_type").setCurrentIndex(idx)
                    idx = getattr(self, f"{prefix}combo_micro").findData(s.get("microstepping", 4))
                    if idx >= 0: getattr(self, f"{prefix}combo_micro").setCurrentIndex(idx)
                    idx = getattr(self, f"{prefix}combo_current").findData(s.get("work_current", 10))
                    if idx >= 0: getattr(self, f"{prefix}combo_current").setCurrentIndex(idx)
                    idx = getattr(self, f"{prefix}combo_hold").findData(s.get("hold_current", 0))
                    if idx >= 0: getattr(self, f"{prefix}combo_hold").setCurrentIndex(idx)
                    getattr(self, f"{prefix}spin_min").setValue(s.get("min_speed", 100))
                    getattr(self, f"{prefix}spin_max").setValue(s.get("max_speed", 500))
                    getattr(self, f"{prefix}spin_acc").setValue(s.get("acceleration", 100))
                    getattr(self, f"{prefix}spin_dec").setValue(s.get("deceleration", 200))
            if self.log_callback: self.log_callback("Настройки загружены из файла")
        except Exception as e:
            if self.log_callback: self.log_callback(f"Ошибка загрузки настроек: {str(e)}")

# =============================================================================
# БЛОК 7: ГЛАВНОЕ ОКНО ПРИЛОЖЕНИЯ
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление моторами")
        self.setFixedSize(1500, 990)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.motor1_obj = motor()
        self.motor2_obj = motor()
        self.worker1 = MotorWorker(self.motor1_obj, 1)
        self.worker2 = MotorWorker(self.motor2_obj, 2)
        self.worker1.start()
        self.worker2.start()
        self.log_window = LogWindow(self)
        self.log_window.show()
        self.main_page = MainPage(self.log_window, self.worker1, self.worker2)
        self.stack.addWidget(self.main_page)
        self.create_menu()
        self.log_message("Приложение запущено")

    def create_menu(self):
        menu_bar = self.menuBar()
        main_action = QAction("Главная", self)
        main_action.triggered.connect(lambda: self.stack.setCurrentIndex(0))
        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.open_settings)
        log_action = QAction("Логи", self)
        log_action.triggered.connect(self.open_log_window)
        graph_menu = menu_bar.addMenu("Графики")
        temp_action = QAction("Температура", self)
        pressure_action = QAction("Давление", self)
        power_action = QAction("Мощность", self)
        graph_menu.addAction(temp_action)
        graph_menu.addAction(pressure_action)
        graph_menu.addAction(power_action)
        menu_bar.addAction(main_action)
        menu_bar.addAction(settings_action)
        menu_bar.addAction(log_action)
        file_menu = menu_bar.addMenu("Файл")
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def open_settings(self):
        dialog = SettingsDialog(self, self.log_message, self.worker1, self.worker2)
        dialog.exec_()
        self.main_page.recalculate_steps_per_degree()

    def open_log_window(self):
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()

    def log_message(self, message):
        self.log_window.log_message(message)

    def closeEvent(self, event):
        self.worker1.stop_thread()
        self.worker2.stop_thread()
        event.accept()

# =============================================================================
# БЛОК 8: ГЛАВНАЯ СТРАНИЦА УПРАВЛЕНИЯ
# =============================================================================
class MainPage(QWidget):
    def __init__(self, log_window=None, worker1=None, worker2=None):
        super().__init__()
        self.log_window = log_window
        self.worker1 = worker1
        self.worker2 = worker2
        self._init_motor_status_panel()
        self._init_manual_area()
        self._init_automatic_area()
        self._setup_layout()
        self._connect_signals()
        self.load_connection_settings()
        self.worker1.log_signal.connect(self.log_message)
        self.worker1.status_signal.connect(self.handle_status_update)
        self.worker1.powerstep_signal.connect(self.handle_powerstep_update)
        self.worker1.progress_signal.connect(self.handle_progress_update)
        self.worker1.connection_result_signal.connect(self.handle_connection_result)
        self.worker2.log_signal.connect(self.log_message)
        self.worker2.status_signal.connect(self.handle_status_update)
        self.worker2.powerstep_signal.connect(self.handle_powerstep_update)
        self.worker2.progress_signal.connect(self.handle_progress_update)
        self.worker2.connection_result_signal.connect(self.handle_connection_result)
        self.Visible = False
        self.interface_locked = False
        self.motor1_connected = False
        self.motor2_connected = False
        self.motor1_angle = 0.0
        self.motor2_angle = 0.0
        self.motor1_steps_per_degree = 8.888888
        self.motor2_steps_per_degree = 8.888888
        self.current_microstep_idx_m1 = 4
        self.current_microstep_idx_m2 = 4
        self.recalculate_steps_per_degree()
        self.load_motor_angle()
        self.motor1_auto_timer = QTimer()
        self.motor1_auto_timer.timeout.connect(self._update_motor1_auto_angle)
        self.motor1_auto_last_time = 0
        self.motor1_auto_direction = 0
        self.simulation_timer1 = QTimer()
        self.simulation_timer2 = QTimer()

    def _init_motor_status_panel(self):
        GroupBox1 = QGroupBox("Состояние моторов")
        GroupBox1.setFont(QFont("Arial", 14, QFont.Bold))
        GroupBox1.setAlignment(Qt.AlignHCenter)
        motors_section = QGridLayout()
        self.indicator1 = StatusIndicator()
        self.name_label1 = QLabel("Мотор 1")
        self.name_label1.setFont(QFont("Arial", 14))
        self.name_label1.setAlignment(Qt.AlignCenter)
        self.status_label1 = QLabel("Выключен")
        self.status_label1.setStyleSheet("color: gray; font-size: 10pt;")
        self.powerstep_status1 = QLabel("PowerSTEP: 0")
        self.powerstep_status1.setStyleSheet("color: red; font-weight: bold; font-size: 11pt;")
        self.powerstep_status1.setAlignment(Qt.AlignCenter)
        self.microstep_label1 = QLabel("Microstep: --")
        self.microstep_label1.setStyleSheet("color: #555; font-size: 9pt;")
        self.microstep_label1.setAlignment(Qt.AlignCenter)
        self.ip_input1 = QLineEdit()
        self.ip_input1.setPlaceholderText("IP")
        self.ip_input1.setText("192.168.1.2")
        self.port_input1 = QLineEdit()
        self.port_input1.setPlaceholderText("PORT")
        self.port_input1.setText("5000")
        self.port_input1.setFixedWidth(90)
        self.btn_start_motor1 = QPushButton("Запустить Мотор 1")
        self.btn_start_motor1.setStyleSheet("background-color: #00aa00; color: white; font-weight: bold;")
        self.btn_disconnect1 = QPushButton("Разрыв соединения")
        self.btn_disconnect1.setStyleSheet("background-color: #aa0000; color: white;")
        self.progress1 = ProgressWidget()
        self.progress1.setFixedHeight(70)
        motors_section.addWidget(self.indicator1, 0, 0)
        motors_section.addWidget(self.name_label1, 0, 1)
        motors_section.addWidget(self.status_label1, 1, 0, 1, 2)
        motors_section.addWidget(self.powerstep_status1, 2, 0, 1, 2)
        motors_section.addWidget(self.microstep_label1, 3, 0, 1, 2)
        motors_section.addWidget(self.ip_input1, 4, 0)
        motors_section.addWidget(self.port_input1, 4, 1)
        motors_section.addWidget(self.btn_start_motor1, 5, 0, 1, 2)
        motors_section.addWidget(self.progress1, 6, 0, 1, 2)
        motors_section.addWidget(self.btn_disconnect1, 7, 0, 1, 2)
        self.indicator2 = StatusIndicator()
        self.name_label2 = QLabel("Мотор 2")
        self.name_label2.setFont(QFont("Arial", 14))
        self.name_label2.setAlignment(Qt.AlignCenter)
        self.status_label2 = QLabel("Выключен")
        self.status_label2.setStyleSheet("color: gray; font-size: 10pt;")
        self.powerstep_status2 = QLabel("PowerSTEP: 0")
        self.powerstep_status2.setStyleSheet("color: red; font-weight: bold; font-size: 11pt;")
        self.powerstep_status2.setAlignment(Qt.AlignCenter)
        self.microstep_label2 = QLabel("Microstep: --")
        self.microstep_label2.setStyleSheet("color: #555; font-size: 9pt;")
        self.microstep_label2.setAlignment(Qt.AlignCenter)
        self.ip_input2 = QLineEdit()
        self.ip_input2.setPlaceholderText("IP")
        self.ip_input2.setText("192.168.1.3")
        self.port_input2 = QLineEdit()
        self.port_input2.setPlaceholderText("PORT")
        self.port_input2.setText("5000")
        self.port_input2.setFixedWidth(90)
        self.btn_start_motor2 = QPushButton("Запустить Мотор 2")
        self.btn_start_motor2.setStyleSheet("background-color: #00aa00; color: white; font-weight: bold;")
        self.btn_disconnect2 = QPushButton("Разрыв соединения")
        self.btn_disconnect2.setStyleSheet("background-color: #aa0000; color: white;")
        self.progress2 = ProgressWidget()
        self.progress2.setFixedHeight(70)
        motors_section.addWidget(self.indicator2, 8, 0)
        motors_section.addWidget(self.name_label2, 8, 1)
        motors_section.addWidget(self.status_label2, 9, 0, 1, 2)
        motors_section.addWidget(self.powerstep_status2, 10, 0, 1, 2)
        motors_section.addWidget(self.microstep_label2, 11, 0, 1, 2)
        motors_section.addWidget(self.ip_input2, 12, 0)
        motors_section.addWidget(self.port_input2, 12, 1)
        motors_section.addWidget(self.btn_start_motor2, 13, 0, 1, 2)
        motors_section.addWidget(self.progress2, 14, 0, 1, 2)
        motors_section.addWidget(self.btn_disconnect2, 15, 0, 1, 2)
        spacer_item = QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
        motors_section.setRowStretch(motors_section.rowCount(), 1)
        motors_section.addItem(spacer_item, motors_section.rowCount(), 0, 1, 2)
        GroupBox1.setLayout(motors_section)
        self.motor_status_panel = GroupBox1

    def _init_manual_area(self):
        GroupBox2 = QGroupBox("Ручное движение")
        GroupBox2.setFont(QFont("Arial", 14, QFont.Bold))
        GroupBox2.setAlignment(Qt.AlignCenter)
        top_layout = QGridLayout()
        top_layout.setSpacing(8)
        self.azimuth = QLabel("Азимут М1 (градусы):")
        self.angle = QLabel("Угол наклона М2 (градусы):")
        self.input_azimuth = QLineEdit()
        self.input_azimuth.setPlaceholderText("Введите градусы")
        self.input_angle = QLineEdit()
        self.input_angle.setPlaceholderText("Введите градусы")
        self.btn_send_coordinates = QPushButton("Отправить координаты")
        self.btn_send_coordinates.setEnabled(False)
        self.btn_send_coordinates.setStyleSheet("background-color: #808080; color: black;")
        self.btn_send_coordinates.setMinimumHeight(40)
        self.angle_display1 = QLabel("Текущий угол М1: 0.00°")
        self.angle_display1.setStyleSheet("color: #0055aa; font-weight: bold; font-size: 12pt;")
        self.angle_display1.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.azimuth, 0, 0)
        top_layout.addWidget(self.input_azimuth, 0, 1)
        top_layout.addWidget(self.angle, 1, 0)
        top_layout.addWidget(self.input_angle, 1, 1)
        top_layout.addWidget(self.btn_send_coordinates, 2, 0, 1, 2)
        top_layout.addWidget(self.angle_display1, 3, 0, 1, 2)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(8)
        self.btn_stop_motor1 = QPushButton("Остановка азимутального двигателя")
        self.btn_stop_motor1.setEnabled(False)
        self.btn_stop_motor1.setStyleSheet("background-color: #808080; color: black;")
        self.btn_stop_motor1.setMinimumHeight(45)
        self.btn_stop_motor1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_home_m1 = QPushButton("Начальное положение М1")
        self.btn_home_m1.setEnabled(False)
        self.btn_home_m1.setStyleSheet("background-color: #808080; color: black;")
        self.btn_home_m1.setMinimumHeight(45)
        self.btn_home_m1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        col1_layout.addWidget(self.btn_stop_motor1)
        col1_layout.addWidget(self.btn_home_m1)
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(8)
        self.btn_stop_motor2 = QPushButton("Остановка углового двигателя")
        self.btn_stop_motor2.setEnabled(False)
        self.btn_stop_motor2.setStyleSheet("background-color: #808080; color: black;")
        self.btn_stop_motor2.setMinimumHeight(45)
        self.btn_stop_motor2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_home_m2 = QPushButton("Начальное положение М2")
        self.btn_home_m2.setEnabled(False)
        self.btn_home_m2.setStyleSheet("background-color: #808080; color: black;")
        self.btn_home_m2.setMinimumHeight(45)
        self.btn_home_m2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        col2_layout.addWidget(self.btn_stop_motor2)
        col2_layout.addWidget(self.btn_home_m2)
        bottom_layout.addLayout(col1_layout)
        bottom_layout.addLayout(col2_layout)
        main_manual_layout = QVBoxLayout()
        main_manual_layout.addLayout(top_layout)
        main_manual_layout.addLayout(bottom_layout)
        GroupBox2.setLayout(main_manual_layout)
        self.manual_area = GroupBox2

    def _init_automatic_area(self):
        GroupBox3 = QGroupBox("Автоматическое движение")
        GroupBox3.setFont(QFont("Arial", 14, QFont.Bold))
        GroupBox3.setAlignment(Qt.AlignCenter)
        auto_layout = QGridLayout()
        az_group = QGroupBox("По азимуту (М1)")
        az_layout = QVBoxLayout()
        self.btn_auto_m1_forward = QPushButton("Вперёд (удерживать)")
        self.btn_auto_m1_forward.setStyleSheet("background-color: #808080; color: black;")
        self.btn_auto_m1_forward.setMinimumHeight(50)
        self.btn_auto_m1_forward.setEnabled(False)
        self.btn_auto_m1_backward = QPushButton("Назад (удерживать)")
        self.btn_auto_m1_backward.setStyleSheet("background-color: #808080; color: black;")
        self.btn_auto_m1_backward.setMinimumHeight(50)
        self.btn_auto_m1_backward.setEnabled(False)
        self.btn_stop_auto_m1 = QPushButton("Остановка двигателя")
        self.btn_stop_auto_m1.setStyleSheet("background-color: #808080; color: black;")
        self.btn_stop_auto_m1.setMinimumHeight(50)
        self.btn_stop_auto_m1.setEnabled(False)
        az_layout.addWidget(self.btn_auto_m1_forward)
        az_layout.addWidget(self.btn_auto_m1_backward)
        az_layout.addWidget(self.btn_stop_auto_m1)
        az_group.setLayout(az_layout)
        angle_group = QGroupBox("По углу наклона (М2)")
        angle_layout = QVBoxLayout()
        self.btn_auto_m2_forward = QPushButton("Вперёд (удерживать)")
        self.btn_auto_m2_forward.setStyleSheet("background-color: #808080; color: black;")
        self.btn_auto_m2_forward.setMinimumHeight(50)
        self.btn_auto_m2_forward.setEnabled(False)
        self.btn_auto_m2_backward = QPushButton("Назад (удерживать)")
        self.btn_auto_m2_backward.setStyleSheet("background-color: #808080; color: black;")
        self.btn_auto_m2_backward.setMinimumHeight(50)
        self.btn_auto_m2_backward.setEnabled(False)
        self.btn_stop_auto_m2 = QPushButton("Остановка двигателя")
        self.btn_stop_auto_m2.setStyleSheet("background-color: #808080; color: black;")
        self.btn_stop_auto_m2.setMinimumHeight(50)
        self.btn_stop_auto_m2.setEnabled(False)
        angle_layout.addWidget(self.btn_auto_m2_forward)
        angle_layout.addWidget(self.btn_auto_m2_backward)
        angle_layout.addWidget(self.btn_stop_auto_m2)
        angle_group.setLayout(angle_layout)
        auto_layout.addWidget(az_group, 0, 0)
        auto_layout.addWidget(angle_group, 0, 1)
        GroupBox3.setLayout(auto_layout)
        self.automatic_area = GroupBox3

    def _setup_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.motor_status_panel)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.manual_area)
        right_layout.addWidget(self.automatic_area)
        layout.addLayout(right_layout)
        self.setLayout(layout)

    def _connect_signals(self):
        self.btn_start_motor1.clicked.connect(self.start_motor1_real)
        self.btn_start_motor2.clicked.connect(self.start_motor2_real)
        self.btn_disconnect1.clicked.connect(lambda: self.disconnect_motor(1))
        self.btn_disconnect2.clicked.connect(lambda: self.disconnect_motor(2))
        self.btn_send_coordinates.clicked.connect(self.send_coordinates)
        self.btn_stop_motor1.clicked.connect(self.stop_all_motor1)
        self.btn_stop_motor2.clicked.connect(self.stop_all_motor2)
        self.btn_home_m1.clicked.connect(lambda: self.home_position(1))
        self.btn_home_m2.clicked.connect(lambda: self.home_position(2))
        self.btn_auto_m1_forward.pressed.connect(lambda: self.auto_move_start(1, 'f'))
        self.btn_auto_m1_forward.released.connect(lambda: self.auto_move_stop(1))
        self.btn_auto_m1_backward.pressed.connect(lambda: self.auto_move_start(1, 'r'))
        self.btn_auto_m1_backward.released.connect(lambda: self.auto_move_stop(1))
        self.btn_stop_auto_m1.clicked.connect(self.stop_all_motor1)
        self.btn_auto_m2_forward.pressed.connect(lambda: self.auto_move_start(2, 'f'))
        self.btn_auto_m2_forward.released.connect(lambda: self.auto_move_stop(2))
        self.btn_auto_m2_backward.pressed.connect(lambda: self.auto_move_start(2, 'r'))
        self.btn_auto_m2_backward.released.connect(lambda: self.auto_move_stop(2))
        self.btn_stop_auto_m2.clicked.connect(self.stop_all_motor2)

    def load_connection_settings(self):
        if not os.path.exists(SETTINGS_FILE): return
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            if "connection" in settings:
                conn = settings["connection"]
                self.ip_input1.setText(conn.get("m1_ip", "192.168.1.2"))
                self.port_input1.setText(str(conn.get("m1_port", 5000)))
                self.ip_input2.setText(conn.get("m2_ip", "192.168.1.3"))
                self.port_input2.setText(str(conn.get("m2_port", 5000)))
        except Exception as e:
            self.log_message(f"Ошибка загрузки настроек соединения: {str(e)}")

    def save_connection_settings(self):
        try:
            settings = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            if "connection" not in settings: settings["connection"] = {}
            settings["connection"]["m1_ip"] = self.ip_input1.text()
            settings["connection"]["m1_port"] = int(self.port_input1.text())
            settings["connection"]["m2_ip"] = self.ip_input2.text()
            settings["connection"]["m2_port"] = int(self.port_input2.text())
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"Ошибка сохранения настроек соединения: {str(e)}")

    def load_motor_angle(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            m1_settings = settings.get("m1_", {})
            saved_angle = m1_settings.get("last_angle", 0.0)
            self.motor1_angle = float(saved_angle)
            self.update_motor1_angle_display()
            self.log_message(f"Угол М1 загружен из файла: {self.motor1_angle:.2f}°")
        except Exception as e:
            self.log_message(f"Ошибка загрузки угла М1: {str(e)}")
            self.motor1_angle = 0.0

    def save_motor_angle(self):
        try:
            settings = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            if "m1_" not in settings:
                settings["m1_"] = {}
            settings["m1_"]["last_angle"] = self.motor1_angle
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log_message(f"Угол М1 сохранен: {self.motor1_angle:.2f}°")
        except Exception as e:
            self.log_message(f"Ошибка сохранения угла М1: {str(e)}")

    def log_message(self, message):
        if self.log_window: self.log_window.log_message(message)

    def handle_status_update(self, motor_num, state):
        if motor_num == 1:
            self.update_status(self.indicator1, self.status_label1, state)
            if state == STATE_CONNECTED:
                self.recalculate_steps_per_degree()
        else:
            self.update_status(self.indicator2, self.status_label2, state)
            if state == STATE_CONNECTED:
                self.recalculate_steps_per_degree()

    def handle_powerstep_update(self, motor_num, status):
        if motor_num == 1:
            self.powerstep_status1.setText(f"PowerSTEP: {status}")
            self.powerstep_status1.setStyleSheet(f"color: {'green' if status == 1 else 'red'}; font-weight: bold; font-size: 11pt;")
        else:
            self.powerstep_status2.setText(f"PowerSTEP: {status}")
            self.powerstep_status2.setStyleSheet(f"color: {'green' if status == 1 else 'red'}; font-weight: bold; font-size: 11pt;")

    def handle_progress_update(self, motor_num, value, text):
        if motor_num == 1:
            self.progress1.set_progress(value, text)
            if value == 100: QTimer.singleShot(1500, self.progress1.reset)
        else:
            self.progress2.set_progress(value, text)
            if value == 100: QTimer.singleShot(1500, self.progress2.reset)

    def handle_connection_result(self, motor_num, success):
        if motor_num == 1: self.motor1_connected = success
        else: self.motor2_connected = success
        if success: self._enable_control_buttons()
        else: self._update_auto_buttons_state()
        if not self.motor1_connected and not self.motor2_connected:
            self.btn_send_coordinates.setEnabled(False)
            self.btn_home_m1.setEnabled(False)
            self.btn_home_m2.setEnabled(False)

    def update_status(self, indicator, label, state):
        indicator.set_state(state)
        statuses = {STATE_OFF: "Выключен", STATE_CONNECTING: "Подключение", STATE_AUTHENTICATING: "Авторизация",
                    STATE_WORKING: "Работает", STATE_CONNECTED: "Подключён", STATE_DISCONNECTED: "Отключён"}
        label.setText(statuses.get(state, "Неизвестно"))

    def _lock_interface(self, locked=True):
        self.interface_locked = locked
        self.btn_send_coordinates.setEnabled(not locked and (self.motor1_connected or self.motor2_connected))
        if self.motor1_connected: self.btn_home_m1.setEnabled(not locked)
        if self.motor2_connected: self.btn_home_m2.setEnabled(not locked)
        self._update_auto_buttons_state()
        self.btn_stop_motor1.setEnabled(True)
        self.btn_stop_motor2.setEnabled(True)
        self.btn_disconnect1.setEnabled(True)
        self.btn_disconnect2.setEnabled(True)
        self.input_azimuth.setEnabled(not locked)
        self.input_angle.setEnabled(not locked)

    def _update_auto_buttons_state(self):
        can_use_m1 = self.motor1_connected and not self.interface_locked
        can_use_m2 = self.motor2_connected and not self.interface_locked
        self.btn_auto_m1_forward.setEnabled(can_use_m1)
        self.btn_auto_m1_forward.setStyleSheet("background-color: #0088cc; color: white; font-weight: bold;" if can_use_m1 else "background-color: #808080; color: black;")
        self.btn_auto_m1_backward.setEnabled(can_use_m1)
        self.btn_auto_m1_backward.setStyleSheet("background-color: #cc6600; color: white; font-weight: bold;" if can_use_m1 else "background-color: #808080; color: black;")
        self.btn_auto_m2_forward.setEnabled(can_use_m2)
        self.btn_auto_m2_forward.setStyleSheet("background-color: #0088cc; color: white; font-weight: bold;" if can_use_m2 else "background-color: #808080; color: black;")
        self.btn_auto_m2_backward.setEnabled(can_use_m2)
        self.btn_auto_m2_backward.setStyleSheet("background-color: #cc6600; color: white; font-weight: bold;" if can_use_m2 else "background-color: #808080; color: black;")
        self.btn_stop_auto_m1.setEnabled(self.motor1_connected)
        self.btn_stop_auto_m1.setStyleSheet("background-color: #aa0000; color: white; font-weight: bold;" if self.motor1_connected else "background-color: #808080; color: black;")
        self.btn_stop_auto_m2.setEnabled(self.motor2_connected)
        self.btn_stop_auto_m2.setStyleSheet("background-color: #aa0000; color: white; font-weight: bold;" if self.motor2_connected else "background-color: #808080; color: black;")

    def _enable_control_buttons(self):
        any_connected = self.motor1_connected or self.motor2_connected
        self.btn_send_coordinates.setEnabled(any_connected)
        self.btn_home_m1.setEnabled(self.motor1_connected)
        self.btn_home_m2.setEnabled(self.motor2_connected)
        self.btn_stop_motor1.setEnabled(self.motor1_connected)
        self.btn_stop_motor2.setEnabled(self.motor2_connected)
        self._update_auto_buttons_state()
        if any_connected: self.btn_send_coordinates.setStyleSheet("background-color: #0088cc; color: white; font-weight: bold;")
        if self.motor1_connected:
            self.btn_home_m1.setStyleSheet("background-color: #00aa00; color: white; font-weight: bold;")
            self.btn_stop_motor1.setStyleSheet("background-color: #00aa00; color: white; font-weight: bold;")
        else:
            self.btn_home_m1.setStyleSheet("background-color: #808080; color: black;")
            self.btn_stop_motor1.setStyleSheet("background-color: #808080; color: black;")
        if self.motor2_connected:
            self.btn_home_m2.setStyleSheet("background-color: #00aa00; color: white; font-weight: bold;")
            self.btn_stop_motor2.setStyleSheet("background-color: #00aa00; color: white; font-weight: bold;")
        else:
            self.btn_home_m2.setStyleSheet("background-color: #808080; color: black;")
            self.btn_stop_motor2.setStyleSheet("background-color: #808080; color: black;")
        self.Visible = True

    def recalculate_steps_per_degree(self):
        """
        Пересчитывает шаги на градус согласно ВАШЕЙ специфической калибровке:
        Индекс 4 (1/16) -> 3200 шагов/оборот
        Индекс 3 (1/8)  -> 6400 шагов/оборот
        Индекс 2 (1/4)  -> 12800 шагов/оборот
        Индекс 1 (1/2)  -> 25600 шагов/оборот
        Индекс 0 (1)    -> 51200 шагов/оборот
        """
        # ЖЕСТКАЯ ТАБЛИЦА: Индекс комбобокса -> Шагов на ПОЛНЫЙ ОБОРОТ (360 градусов)
        # Это исправляет ошибку, когда при смене режима менялось количество оборотов вместо количества шагов.
        STEPS_PER_REV_MAP = {
            0: 51200,  # Режим "1"
            1: 25600,  # Режим "1/2"
            2: 12800,  # Режим "1/4"
            3: 6400,   # Режим "1/8"  <-- Здесь было 1600 по старой формуле, теперь 6400
            4: 3200    # Режим "1/16" <-- Базовое значение
        }

        idx1, idx2 = 4, 4  # Значения по умолчанию

        # Читаем актуальные индексы из файла настроек
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                # Получаем индексы, приводим к int для надежности
                idx1 = int(settings.get("m1_", {}).get("microstepping", 4))
                idx2 = int(settings.get("m2_", {}).get("microstepping", 4))
            except Exception:
                pass

        self.current_microstep_idx_m1 = idx1
        self.current_microstep_idx_m2 = idx2

        # Берем количество шагов на оборот напрямую из таблицы
        rev_steps1 = STEPS_PER_REV_MAP.get(idx1, 3200)
        rev_steps2 = STEPS_PER_REV_MAP.get(idx2, 3200)

        # Считаем шаги на 1 градус
        self.motor1_steps_per_degree = rev_steps1 / 360.0
        self.motor2_steps_per_degree = rev_steps2 / 360.0

        # Обновляем интерфейс
        self.update_motor1_angle_display()
        self.update_microstep_labels()



    def update_microstep_labels(self):
        micro_names = ["1", "1/2", "1/4", "1/8", "1/16"]
        idx1 = self.current_microstep_idx_m1
        name1 = micro_names[idx1] if 0 <= idx1 < len(micro_names) else "?"
        self.microstep_label1.setText(f"Microstep: {name1}")
        idx2 = self.current_microstep_idx_m2
        name2 = micro_names[idx2] if 0 <= idx2 < len(micro_names) else "?"
        self.microstep_label2.setText(f"Microstep: {name2}")

    def update_motor1_angle_display(self):
        self.angle_display1.setText(f"Текущий угол М1: {self.motor1_angle:.2f}°")

    def _update_motor1_auto_angle(self):
        now = time.time()
        dt = now - self.motor1_auto_last_time
        self.motor1_auto_last_time = now
        speed = self._get_motor_speed(1)
        steps_moved = speed * dt
        deg_moved = steps_moved / self.motor1_steps_per_degree
        self.motor1_angle += deg_moved * self.motor1_auto_direction
        self.update_motor1_angle_display()

    def start_motor1_real(self):
        self.log_message("Запуск подключения Мотор 1...")
        self.save_connection_settings()
        self.recalculate_steps_per_degree()
        task = {'type': 'connect', 'ip': self.ip_input1.text(), 'port': int(self.port_input1.text())}
        self.worker1.add_task(task)

    def start_motor2_real(self):
        self.log_message("Запуск подключения Мотор 2...")
        self.save_connection_settings()
        task = {'type': 'connect', 'ip': self.ip_input2.text(), 'port': int(self.port_input2.text())}
        self.worker2.add_task(task)

    def disconnect_motor(self, motor_num):
        if motor_num == 1:
            self.motor1_auto_timer.stop()
            self.motor1_auto_direction = 0
            self.worker1.add_task({'type': 'disconnect'})
            self.motor1_connected = False
            self.log_message("Команда отключения Мотор 1 отправлена")
        else:
            self.worker2.add_task({'type': 'disconnect'})
            self.motor2_connected = False
            self.log_message("Команда отключения Мотор 2 отправлена")
        self._update_auto_buttons_state()
        if not self.motor1_connected and not self.motor2_connected:
            self.btn_send_coordinates.setEnabled(False)
            self.btn_home_m1.setEnabled(False)
            self.btn_home_m2.setEnabled(False)

    def _get_motor_speed(self, motor_num):
        if not os.path.exists(SETTINGS_FILE): return 100
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            prefix = "m1_" if motor_num == 1 else "m2_"
            if prefix in settings: return settings[prefix].get("max_speed", 100)
        except: pass
        return 100

    def auto_move_start(self, motor_num, direction):
        if self.interface_locked: return
        if motor_num == 1:
            if not self.motor1_connected:
                QMessageBox.warning(self, "Ошибка", "Мотор 1 не подключён!")
                return
            self.motor1_auto_timer.stop()
            self.motor1_auto_direction = 1 if direction == 'f' else -1
            self.motor1_auto_last_time = time.time()
            self.motor1_auto_timer.start(50)
            speed = self._get_motor_speed(1)
            self.worker1.add_task({'type': 'move_auto', 'direction': direction, 'speed': speed})
        elif motor_num == 2:
            if not self.motor2_connected:
                QMessageBox.warning(self, "Ошибка", "Мотор 2 не подключён!")
                return
            speed = self._get_motor_speed(2)
            self.worker2.add_task({'type': 'move_auto', 'direction': direction, 'speed': speed})

    def auto_move_stop(self, motor_num):
        if motor_num == 1:
            self.motor1_auto_timer.stop()
            self.motor1_auto_direction = 0
            self.worker1.add_task({'type': 'stop'})
        elif motor_num == 2:
            self.worker2.add_task({'type': 'stop'})

    def stop_all_motor1(self):
        if self.motor1_connected:
            self.motor1_auto_timer.stop()
            self.motor1_auto_direction = 0
            self.worker1.add_task({'type': 'stop'})

    def stop_all_motor2(self):
        if self.motor2_connected:
            self.worker2.add_task({'type': 'stop'})

    def home_position(self, motor_num):
        if motor_num == 1 and not self.motor1_connected:
            QMessageBox.warning(self, "Ошибка", "Мотор 1 не подключен!")
            return
        if motor_num == 2 and not self.motor2_connected:
            QMessageBox.warning(self, "Ошибка", "Мотор 2 не подключен!")
            return
        if motor_num == 1:
            self.btn_home_m1.setEnabled(False)
            self.worker1.add_task({'type': 'home'})
            self.motor1_angle = 0.0
            self.update_motor1_angle_display()
            self.save_motor_angle()
            self.log_message("Команда Home отправлена Мотору 1")
            QTimer.singleShot(3000, lambda: self._reset_home_status(1))
        else:
            self.btn_home_m2.setEnabled(False)
            self.worker2.add_task({'type': 'home'})
            self.log_message("Команда Home отправлена Мотору 2")
            QTimer.singleShot(3000, lambda: self._reset_home_status(2))

    def _reset_home_status(self, motor_num):
        if motor_num == 1 and self.motor1_connected:
            self.btn_home_m1.setEnabled(True)
            self.handle_status_update(1, STATE_CONNECTED)
            self.handle_powerstep_update(1, 0)
        elif motor_num == 2 and self.motor2_connected:
            self.btn_home_m2.setEnabled(True)
            self.handle_status_update(2, STATE_CONNECTED)
            self.handle_powerstep_update(2, 0)

    def send_coordinates(self):
        az_text = self.input_azimuth.text().strip()
        ang_text = self.input_angle.text().strip()
        if not az_text and not ang_text:
            QMessageBox.warning(self, "Ошибка", "Введите хотя бы одну координату (в градусах)!")
            return
        tasks_sent = False
        if az_text:
            if not self.motor1_connected:
                QMessageBox.warning(self, "Ошибка", "Мотор 1 не подключен, но введен азимут!")
                return
            try:
                target_deg = float(az_text)
                delta_deg = target_deg - self.motor1_angle
                steps = int(round(abs(delta_deg) * self.motor1_steps_per_degree))
                dir_val = 'f' if delta_deg >= 0 else 'r'
                if steps > 0:
                    self.worker1.add_task({'type': 'coords', 'dist': steps, 'dir': dir_val})
                    self.motor1_angle = target_deg
                    self.update_motor1_angle_display()
                    tasks_sent = True
                    self.handle_status_update(1, STATE_WORKING)
                    self.handle_powerstep_update(1, 1)
                    QTimer.singleShot(3000, lambda: self._reset_coord_status(1))
                else:
                    self.log_message("Целевой угол совпадает с текущим")
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Неверный формат азимута (используйте число градусов)!")
                return
        if ang_text:
            if not self.motor2_connected:
                QMessageBox.warning(self, "Ошибка", "Мотор 2 не подключен, но введен угол!")
                return
            try:
                target_deg = float(ang_text)
                if not hasattr(self, 'motor2_angle'):
                    self.motor2_angle = 0.0
                delta_deg_2 = target_deg - self.motor2_angle
                steps_2 = int(round(abs(delta_deg_2) * self.motor2_steps_per_degree))
                dir_val_2 = 'f' if delta_deg_2 >= 0 else 'r'
                if steps_2 > 0:
                    self.worker2.add_task({'type': 'coords', 'dist': steps_2, 'dir': dir_val_2})
                    self.motor2_angle = target_deg
                    tasks_sent = True
                    self.handle_status_update(2, STATE_WORKING)
                    self.handle_powerstep_update(2, 1)
                    QTimer.singleShot(3000, lambda: self._reset_coord_status(2))
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Неверный формат угла!")
                return
        if tasks_sent:
            self.log_message("Команды перемещения отправлены")

    def _reset_coord_status(self, motor_num):
        if motor_num == 1:
            self.handle_status_update(1, STATE_CONNECTED)
            self.handle_powerstep_update(1, 0)
        else:
            self.handle_status_update(2, STATE_CONNECTED)
            self.handle_powerstep_update(2, 0)

# =============================================================================
# БЛОК 9: ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
