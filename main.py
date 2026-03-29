"""
███████╗██████╗░██╗░░██╗██╗███╗░░██╗██╗░░██╗██████╗░░█████╗░███████╗████████╗
██╔════╝██╔══██╗██║░██╔╝██║████╗░██║██║░██╔╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝
█████╗░░██████╔╝█████═╝░██║██╔██╗██║█████═╝░██████╔╝███████║█████╗░░░░░██║░░░
██╔══╝░░██╔══██╗██╔═██╗░██║██║╚████║██╔═██╗░██╔══██╗██╔══██║██╔══╝░░░░░██║░░░
███████╗██║░░██║██║░╚██╗██║██║░╚███║██║░╚██╗██║░░██║██║░░██║██║░░░░░░░░██║░░░
╚══════╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝╚═╝░░╚══╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░░░░╚═╝░░░"""
import socket
import sys
import threading
import time
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from common import create_client_socket, create_server_socket, pick_random_port, wrap_accepted_socket, JsonLineReader, send_json_line
from receiver import run_receiver_with_socket
from sender import run_sender_with_socket


class ModernWindow(QtWidgets.QMainWindow):
	disconnectedSend = QtCore.Signal(str)
	disconnectedReceive = QtCore.Signal(str)
	def __init__(self) -> None:
		super().__init__()
		self._version = "V1.1"
		self.setWindowTitle("Клавиатура по сети")
		self.setMinimumSize(560, 360)
		self._apply_modern_style()

		self._central = QtWidgets.QWidget(self)
		self.setCentralWidget(self._central)

		self._stack = QtWidgets.QStackedLayout()
		root_layout = QtWidgets.QVBoxLayout(self._central)
		root_layout.setContentsMargins(24, 24, 24, 24)
		root_layout.setSpacing(16)

		title_row = QtWidgets.QHBoxLayout()
		title = QtWidgets.QLabel("Выберите режим")
		title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
		title.setStyleSheet("font-size: 22px; font-weight: 600;")
		title_row.addWidget(title, 1)
		self._btn_help = QtWidgets.QToolButton()
		self._btn_help.setText("?")
		self._btn_help.setToolTip("Справка")
		self._btn_help.setFixedSize(28, 28)
		self._btn_help.setStyleSheet("QToolButton { border-radius: 14px; } QToolButton:hover { background: rgba(255,255,255,0.08); }")
		self._btn_help.clicked.connect(self._show_help)
		title_row.addWidget(self._btn_help, 0, QtCore.Qt.AlignRight)
		root_layout.addLayout(title_row)
		root_layout.addLayout(self._stack)

		self._page_role = self._build_role_page()
		self._page_receive = self._build_receive_page()
		self._page_send = self._build_send_page()
		self._stack.addWidget(self._page_role)
		self._stack.addWidget(self._page_receive)
		self._stack.addWidget(self._page_send)
		self._stack.currentChanged.connect(self._on_stack_changed)

		self._server_thread: Optional[threading.Thread] = None
		self._server_socket: Optional[socket.socket] = None
		self._server_stop = threading.Event()
		self._sender_thread: Optional[threading.Thread] = None
		self._sender_socket: Optional[socket.socket] = None
		self._connect_cancel = threading.Event()
		self._require_password = False
		self._receive_password = ""
		self._lan_discovery_enabled = False
		self._discovery_thread: Optional[threading.Thread] = None
		self._discovery_stop = threading.Event()
		self._tray: Optional[QtWidgets.QSystemTrayIcon] = None
		self._act_toggle_console: Optional[QtGui.QAction] = None
		self._console_visible = True
		self._sender_monitor_thread: Optional[threading.Thread] = None
		self._receiver_thread: Optional[threading.Thread] = None
		self._local_sender_close = threading.Event()
		self._local_receiver_close = threading.Event()
		self._active_receive_conn: Optional[socket.socket] = None

		self._init_tray()
		self.disconnectedSend.connect(self._on_disconnected_send)
		self.disconnectedReceive.connect(self._on_disconnected_receive)

	def _apply_modern_style(self) -> None:
		QtWidgets.QApplication.setStyle("Fusion")
		palette = QtGui.QPalette()
		palette.setColor(QtGui.QPalette.Window, QtGui.QColor(45, 45, 48))
		palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
		palette.setColor(QtGui.QPalette.Base, QtGui.QColor(37, 37, 38))
		palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(45, 45, 48))
		palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
		palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
		palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
		palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 48))
		palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
		palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
		palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(0, 120, 215))
		palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)
		self.setPalette(palette)
		self.setAutoFillBackground(True)
		self.setStyleSheet("""
			QWidget { color: #ffffff; }
			QLineEdit, QSpinBox {
				background: #2d2d30; border: 1px solid #3f3f46; border-radius: 10px; padding: 10px;
			}
			QPushButton {
				background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1b88f3, stop:1 #0b6bd4);
				color: white; border: none; border-radius: 12px; padding: 10px 18px; font-weight: 700; letter-spacing: 0.3px;
			}
			QPushButton:hover { background: #1c88e5; }
			QPushButton:disabled { background: #3f3f46; color: #aaaaaa; }
			QGroupBox {
				border: 1px solid #39393f; border-radius: 14px; margin-top: 22px; padding: 18px;
				background: rgba(255,255,255,0.02);
			}
			QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0px 4px; }
			QLabel[headline=\"true\"] { font-size: 18px; font-weight: 700; }
			QCheckBox { spacing: 8px; }
			QMenu { background: #2b2b2f; border: 1px solid #3f3f46; }
			QMenu::item { padding: 8px 14px; }
			QMenu::item:selected { background: #0078d7; }
		""")

	def _build_role_page(self) -> QtWidgets.QWidget:
		w = QtWidgets.QWidget()
		l = QtWidgets.QVBoxLayout(w)
		l.setSpacing(20)

		btn_receive = QtWidgets.QPushButton("Принимать")
		btn_send = QtWidgets.QPushButton("Отправлять")
		btn_receive.setMinimumHeight(48)
		btn_send.setMinimumHeight(48)
		l.addWidget(btn_receive)
		l.addWidget(btn_send)
		l.addStretch()

		btn_receive.clicked.connect(self._on_choose_receive)
		btn_send.clicked.connect(lambda: self._stack.setCurrentWidget(self._page_send))
		return w

	def _build_receive_page(self) -> QtWidgets.QWidget:
		w = QtWidgets.QWidget()
		l = QtWidgets.QVBoxLayout(w)
		l.setSpacing(12)

		gb = QtWidgets.QGroupBox("Режим приема")
		gb_l = QtWidgets.QVBoxLayout(gb)
		self._port_label = QtWidgets.QLabel()
		self._port_label.setProperty("headline", True)
		gb_l.addWidget(self._port_label)
	
		opts_form = QtWidgets.QFormLayout()
		self._cb_discovery = QtWidgets.QCheckBox("Разрешить обнаружение в локальной сети")
		self._cb_require_pwd = QtWidgets.QCheckBox("Требовать пароль на подключение")
		self._edit_pwd_recv = QtWidgets.QLineEdit()
		self._edit_pwd_recv.setEchoMode(QtWidgets.QLineEdit.Password)
		self._btn_toggle_pwd_recv = QtWidgets.QToolButton()
		self._btn_toggle_pwd_recv.setCheckable(True)
		self._btn_toggle_pwd_recv.setAutoRaise(True)
		self._btn_toggle_pwd_recv.setText("👁")
		self._btn_toggle_pwd_recv.setToolTip("Показать/скрыть пароль")
		self._btn_toggle_pwd_recv.setFixedSize(28, 28)
		self._btn_toggle_pwd_recv.setStyleSheet("QToolButton { border-radius: 14px; } QToolButton:hover { background: rgba(255,255,255,0.08); }")
		def _toggle_recv_echo(checked: bool) -> None:
			self._edit_pwd_recv.setEchoMode(QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password)
			self._btn_toggle_pwd_recv.setText("🙈" if checked else "👁")
		self._btn_toggle_pwd_recv.toggled.connect(_toggle_recv_echo)
		_pwd_recv_row = QtWidgets.QHBoxLayout()
		_pwd_recv_row.setContentsMargins(0, 0, 0, 0)
		_pwd_recv_row.setSpacing(6)
		_pwd_recv_row.addWidget(self._edit_pwd_recv, 1)
		_pwd_recv_row.addWidget(self._btn_toggle_pwd_recv, 0)
		_pwd_recv_widget = QtWidgets.QWidget()
		_pwd_recv_widget.setLayout(_pwd_recv_row)
		self._edit_pwd_recv.setEnabled(False)
		self._cb_require_pwd.toggled.connect(self._edit_pwd_recv.setEnabled)
		opts_form.addRow(self._cb_discovery)
		opts_form.addRow(self._cb_require_pwd)
		opts_form.addRow("Пароль:", _pwd_recv_widget)
		gb_l.addLayout(opts_form)
		self._status_receive = QtWidgets.QLabel("Ожидание подключения...")
		gb_l.addWidget(self._status_receive)
		self._ok_icon_receive = QtWidgets.QLabel("✓")
		self._ok_icon_receive.setAlignment(QtCore.Qt.AlignCenter)
		self._ok_icon_receive.setFixedSize(40, 40)
		self._ok_icon_receive.setStyleSheet("background:#16a34a; color:white; font-weight:800; border-radius:20px;")
		self._ok_icon_receive.hide()
		ok_wrap = QtWidgets.QHBoxLayout()
		ok_wrap.addStretch()
		ok_wrap.addWidget(self._ok_icon_receive)
		ok_wrap.addStretch()
		gb_l.addLayout(ok_wrap)

		self._btn_back1 = QtWidgets.QPushButton("Назад")
		btns = QtWidgets.QHBoxLayout()
		btns.addStretch()
		btns.addWidget(self._btn_back1)
		btns.addStretch()
		gb_l.addLayout(btns)
		l.addWidget(gb)
		l.addStretch()

		self._receive_port = pick_random_port()
		self._port_label.setText(f"Порт: {self._receive_port}")

		self._btn_back1.clicked.connect(self._on_back_from_receive)
	
		self._cb_discovery.toggled.connect(self._restart_receive_if_active)
		self._cb_require_pwd.toggled.connect(self._restart_receive_if_active)
		self._edit_pwd_recv.textChanged.connect(self._restart_receive_if_active)
		return w

	def _build_send_page(self) -> QtWidgets.QWidget:
		w = QtWidgets.QWidget()
		l = QtWidgets.QVBoxLayout(w)
		l.setSpacing(12)
		gb = QtWidgets.QGroupBox("Режим отправки")
		gb_l = QtWidgets.QFormLayout(gb)
		self._edit_ip = QtWidgets.QLineEdit()
		self._edit_ip.setPlaceholderText("IP адрес получателя (например, 192.168.1.10)")
		self._edit_port = QtWidgets.QLineEdit()
		self._edit_port.setPlaceholderText("Введите порт")
		self._edit_port.setValidator(QtGui.QIntValidator(1, 65535, self))
		self._edit_pwd_send = QtWidgets.QLineEdit()
		self._edit_pwd_send.setEchoMode(QtWidgets.QLineEdit.Password)
		self._btn_toggle_pwd_send = QtWidgets.QToolButton()
		self._btn_toggle_pwd_send.setCheckable(True)
		self._btn_toggle_pwd_send.setAutoRaise(True)
		self._btn_toggle_pwd_send.setText("👁")
		self._btn_toggle_pwd_send.setToolTip("Показать/скрыть пароль")
		self._btn_toggle_pwd_send.setFixedSize(28, 28)
		self._btn_toggle_pwd_send.setStyleSheet("QToolButton { border-radius: 14px; } QToolButton:hover { background: rgba(255,255,255,0.08); }")
		def _toggle_send_echo(checked: bool) -> None:
			self._edit_pwd_send.setEchoMode(QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password)
			self._btn_toggle_pwd_send.setText("🙈" if checked else "👁")
		self._btn_toggle_pwd_send.toggled.connect(_toggle_send_echo)
		_pwd_send_row = QtWidgets.QHBoxLayout()
		_pwd_send_row.setContentsMargins(0, 0, 0, 0)
		_pwd_send_row.setSpacing(6)
		_pwd_send_row.addWidget(self._edit_pwd_send, 1)
		_pwd_send_row.addWidget(self._btn_toggle_pwd_send, 0)
		_pwd_send_widget = QtWidgets.QWidget()
		_pwd_send_widget.setLayout(_pwd_send_row)
		find_wrap = QtWidgets.QHBoxLayout()
		self._btn_find = QtWidgets.QPushButton("Найти в сети")
		find_wrap.addWidget(self._btn_find)
		find_wrap.addStretch()
		gb_l.addRow("IP:", self._edit_ip)
		gb_l.addRow("Порт:", self._edit_port)
		gb_l.addRow("Пароль:", _pwd_send_widget)
		gb_l.addRow(find_wrap)
		self._status_send = QtWidgets.QLabel("")
		gb_l.addRow(self._status_send)

		btns = QtWidgets.QHBoxLayout()
		self._btn_connect = QtWidgets.QPushButton("Подключиться")
		self._btn_back2 = QtWidgets.QPushButton("Назад")
		btns.addWidget(self._btn_connect)
		btns.addWidget(self._btn_back2)
		l.addWidget(gb)
		self._ok_icon_send = QtWidgets.QLabel("✓")
		self._ok_icon_send.setAlignment(QtCore.Qt.AlignCenter)
		self._ok_icon_send.setFixedSize(40, 40)
		self._ok_icon_send.setStyleSheet("background:#16a34a; color:white; font-weight:800; border-radius:20px;")
		self._ok_icon_send.hide()
		ok_wrap = QtWidgets.QHBoxLayout()
		ok_wrap.addStretch()
		ok_wrap.addWidget(self._ok_icon_send)
		ok_wrap.addStretch()
		l.addLayout(ok_wrap)
		l.addLayout(btns)
		l.addStretch()

		self._btn_connect.clicked.connect(self._on_connect_send)
		self._btn_find.clicked.connect(self._on_find_in_lan)
		self._btn_back2.clicked.connect(self._on_back_from_send)
		return w

	def _on_choose_receive(self) -> None:
		self._stack.setCurrentWidget(self._page_receive)
		self._start_receive_if_needed()

	def _on_stack_changed(self, index: int) -> None:
		w = self._stack.widget(index)
		if w is self._page_receive:
			self._start_receive_if_needed()

	def _minimize_window(self) -> None:
		self.setWindowState(self.windowState() | QtCore.Qt.WindowMinimized)
		self.showMinimized()
		self.hide()

	def _on_back_from_receive(self) -> None:

		if self._active_receive_conn is not None:
			self._local_receiver_close.set()
			try:
				send_json_line(self._active_receive_conn, {"bye": 1})
			except Exception:
				pass
			try:
				self._active_receive_conn.shutdown(socket.SHUT_RDWR)
			except Exception:
				pass
			try:
				self._active_receive_conn.close()
			except Exception:
				pass
			self._active_receive_conn = None
		self._stop_server_thread()
		self._receive_port = pick_random_port()
		self._port_label.setText(f"Порт: {self._receive_port}")
		self._status_receive.setText("Ожидание подключения...")
		self._ok_icon_receive.hide()
		self._stack.setCurrentWidget(self._page_role)

	def _on_back_from_send(self) -> None:
		self._connect_cancel.set()
		self._local_sender_close.set()
		
		if self._sender_socket is not None:
			try:
				send_json_line(self._sender_socket, {"bye": 1})
			except Exception:
				pass
		self._stop_sender_if_running()
		self._status_send.setText("")
		self._ok_icon_send.hide()
		self._btn_connect.setDisabled(False)
		self._stack.setCurrentWidget(self._page_role)

	def closeEvent(self, event: QtGui.QCloseEvent) -> None:  
		
		if self._tray and self._tray.isVisible():
			event.ignore()
			self.hide()
		else:
			super().closeEvent(event)

	def _init_tray(self) -> None:
		self._tray = QtWidgets.QSystemTrayIcon(self)
		icon = self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
		self._tray.setIcon(icon)
		menu = QtWidgets.QMenu()
		act_open = menu.addAction("Открыть интерфейс")
		self._act_toggle_console = menu.addAction("Скрыть консоль" if self._console_visible else "Показать консоль")
		menu.addSeparator()
		act_exit = menu.addAction("Выход")
		act_open.triggered.connect(self._restore_from_tray)
		self._act_toggle_console.triggered.connect(self._toggle_console_action)
		act_exit.triggered.connect(QtWidgets.QApplication.instance().quit) 
		self._tray.setContextMenu(menu)
		self._tray.activated.connect(self._on_tray_activated)
		self._tray.show()

	def _on_tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
		if reason == QtWidgets.QSystemTrayIcon.Trigger:
			self._restore_from_tray()

	def _on_disconnected_send(self, reason: str) -> None:
		self._status_send.setText("Соединение разорвано второй стороной")
		self._ok_icon_send.hide()
		self._btn_connect.setDisabled(False)

		self._stop_sender_if_running()
		self._connect_cancel.clear()
		self._local_sender_close.clear()
		if self._tray:
			self._tray.showMessage("Para", "Соединение (отправка) разорвано второй стороной", QtWidgets.QSystemTrayIcon.Information, 3000)

	def _on_disconnected_receive(self, reason: str) -> None:
		self._status_receive.setText("Соединение разорвано второй стороной")
		self._ok_icon_receive.hide()
		self._active_receive_conn = None
		if self._tray:
			self._tray.showMessage("Para", "Соединение (приём) разорвано второй стороной", QtWidgets.QSystemTrayIcon.Information, 3000)

		self._server_thread = None
		self._server_socket = None
		self._server_stop.clear()
		if self._stack.currentWidget() is self._page_receive:
			self._start_receive_if_needed()

	def _restore_from_tray(self) -> None:
		self.showNormal()
		self.activateWindow()
		self.raise_()

	def _toggle_console_action(self) -> None:
		if self._console_visible:
			self._hide_console()
			self._console_visible = False
		else:
			self._show_console()
			self._console_visible = True
		if self._act_toggle_console is not None:
			self._act_toggle_console.setText("Скрыть консоль" if self._console_visible else "Показать консоль")

	def _hide_console(self) -> None:
		try:
			import ctypes
			kernel32 = ctypes.WinDLL("kernel32")
			user32 = ctypes.WinDLL("user32")
			hwnd = kernel32.GetConsoleWindow()
			if hwnd:
				user32.ShowWindow(hwnd, 0)  
		except Exception:
			pass

	def _show_console(self) -> None:
		try:
			import ctypes
			kernel32 = ctypes.WinDLL("kernel32")
			user32 = ctypes.WinDLL("user32")
			hwnd = kernel32.GetConsoleWindow()
			if hwnd:
				user32.ShowWindow(hwnd, 5)  
		except Exception:
			pass
	def _start_receive_if_needed(self) -> None:
		if self._server_thread and self._server_thread.is_alive():
			return
		self._status_receive.setText("Ожидание подключения...")

		self._lan_discovery_enabled = self._cb_discovery.isChecked()
		self._require_password = self._cb_require_pwd.isChecked()
		self._receive_password = self._edit_pwd_recv.text()
		self._server_stop.clear()
		self._server_thread = threading.Thread(target=self._accept_once_thread, daemon=True)
		self._server_thread.start()
	
		self._start_discovery_responder_if_needed()

	def _restart_receive_if_active(self) -> None:
	
		if self._stack.currentWidget() is not self._page_receive:
			return
		self._stop_server_thread()
		self._start_receive_if_needed()

	def _stop_server_thread(self) -> None:
		self._server_stop.set()
		if self._server_socket is not None:
			try:
				self._server_socket.close()
			except Exception:
				pass
			self._server_socket = None
		self._stop_discovery_responder()

	def _stop_sender_if_running(self) -> None:
		if self._sender_socket is not None:
			try:
				self._sender_socket.shutdown(socket.SHUT_RDWR)
			except Exception:
				pass
			try:
				self._sender_socket.close()
			except Exception:
				pass
			self._sender_socket = None
		if self._sender_thread is not None and self._sender_thread.is_alive():
			try:
				self._sender_thread.join(timeout=0.5)
			except Exception:
				pass
		self._sender_thread = None
		self._sender_monitor_thread = None

	def _start_discovery_responder_if_needed(self) -> None:
		if not self._lan_discovery_enabled:
			return
		if self._discovery_thread and self._discovery_thread.is_alive():
			return
		self._discovery_stop.clear()
		self._discovery_thread = threading.Thread(target=self._discovery_responder_thread, daemon=True)
		self._discovery_thread.start()

	def _stop_discovery_responder(self) -> None:
		self._discovery_stop.set()

	def _discovery_responder_thread(self) -> None:
		import socket as _s
		udp = None
		try:
			udp = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
			udp.setsockopt(_s.SOL_SOCKET, _s.SO_REUSEADDR, 1)
			try:
				udp.bind(("0.0.0.0", 53555))
			except OSError:
		
				return
			udp.settimeout(0.5)
			while not self._discovery_stop.is_set():
				try:
					data, addr = udp.recvfrom(1024)
				except TimeoutError:
					continue
				except OSError:
					if self._discovery_stop.is_set():
						break
					continue
				if not data:
					continue
				if data.strip() == b"PARA_DISCOVER":
					reply = f"PARA_OFFER:{self._receive_port}".encode("utf-8")
					try:
						udp.sendto(reply, addr)
					except OSError:
						pass
		finally:
			if udp is not None:
				try:
					udp.close()
				except Exception:
					pass

	def _on_find_in_lan(self) -> None:
		
		import socket as _s
		self._status_send.setText("Поиск в сети...")
		def worker() -> None:
			s = None
			try:
				s = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
				s.setsockopt(_s.SOL_SOCKET, _s.SO_BROADCAST, 1)
				s.settimeout(3.0)
				for _ in range(3):
					try:
						s.sendto(b"PARA_DISCOVER", ("255.255.255.255", 53555))
					except OSError:
						pass
				deadline = time.time() + 3.0
				while time.time() < deadline:
					try:
						data, (ip, _) = s.recvfrom(1024)
					except _s.timeout:
						break
					if not data:
						continue
					if data.startswith(b"PARA_OFFER:"):
						try:
							port = int(data.split(b":", 1)[1].decode("utf-8"))
						except Exception:
							continue
						self._edit_ip.setText(ip)
						self._edit_port.setText(str(port))
						self._status_send.setText(f"Найдено: {ip}:{port}")
						return
				self._status_send.setText("Поиск завершён. Устройств не найдено.")
			finally:
				if s is not None:
					try:
						s.close()
					except Exception:
						pass
		threading.Thread(target=worker, daemon=True).start()

	def _switch_to_english_layout(self) -> None:
		
		try:
			import ctypes, time as _t
			user32 = ctypes.WinDLL("user32", use_last_error=True)
			LoadKeyboardLayoutW = user32.LoadKeyboardLayoutW
			ActivateKeyboardLayout = user32.ActivateKeyboardLayout
			GetForegroundWindow = user32.GetForegroundWindow
			SendMessageTimeoutW = user32.SendMessageTimeoutW
		
			KLF_ACTIVATE = 0x00000001
			KLF_SETFORPROCESS = 0x00000100
			WM_INPUTLANGCHANGEREQUEST = 0x0050
			SMTO_ABORTIFHUNG = 0x0002
		
			hkl = LoadKeyboardLayoutW("00000409", KLF_ACTIVATE | KLF_SETFORPROCESS)
			if not hkl:
				return
			ActivateKeyboardLayout(hkl, 0)
			hwnd = GetForegroundWindow()
			if hwnd:
			
				for _ in range(3):
					SendMessageTimeoutW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, hkl, SMTO_ABORTIFHUNG, 100, None)
					_t.sleep(0.03)
		except Exception:
			pass
	def _accept_once_thread(self) -> None:
		try:
			server = create_server_socket("0.0.0.0", self._receive_port)
			self._server_socket = server
	
			server.settimeout(0.5)
			while not self._server_stop.is_set():
				try:
					conn, addr = server.accept()
				except TimeoutError:
					continue
				except OSError:
					if self._server_stop.is_set():
						return
					continue
				conn = wrap_accepted_socket(conn)
			
				if self._require_password:
					try:
						conn.settimeout(5.0)
						reader = JsonLineReader(conn)
						msg = reader.read_one()
					except Exception:
						try:
							conn.close()
						except Exception:
							pass
						continue
					finally:
						try:
							conn.settimeout(None)
						except Exception:
							pass
					if not isinstance(msg, dict) or msg.get("auth") != self._receive_password:
						try:
							conn.close()
						except Exception:
							pass
						continue
				
				try:
					send_json_line(conn, {"hello": 1})
				except Exception:
					try:
						conn.close()
					except Exception:
						pass
					continue
				self._launch_receiver(conn, addr)
				return
		finally:
			if self._server_socket is not None:
				try:
					self._server_socket.close()
				except Exception:
					pass
				self._server_socket = None

	def _launch_receiver(self, conn: socket.socket, addr: tuple) -> None:
		self._status_receive.setText(f"Подключено: {addr[0]}:{addr[1]}")
		self._ok_icon_receive.show()
		self._switch_to_english_layout()
		self._local_receiver_close.clear()
		self._active_receive_conn = conn
		self._receiver_thread = threading.Thread(target=run_receiver_with_socket, args=(conn,), daemon=False)
		self._receiver_thread.start()
	
		def waiter() -> None:
			if self._receiver_thread is not None:
				self._receiver_thread.join()
	
			if not self._local_receiver_close.is_set():
				try:
					self.disconnectedReceive.emit("remote")
				except Exception:
					pass
		threading.Thread(target=waiter, daemon=True).start()
		QtCore.QTimer.singleShot(1000, self._minimize_window)

	def _on_connect_send(self) -> None:
		host = self._edit_ip.text().strip()
		port_text = self._edit_port.text().strip()
		if not host:
			self._status_send.setText("Введите IP адрес.")
			return
		if not port_text:
			self._status_send.setText("Введите порт.")
			return
		try:
			port = int(port_text)
		except Exception:
			self._status_send.setText("Неверный порт.")
			return
		if port < 1 or port > 65535:
			self._status_send.setText("Неверный порт.")
			return
		self._status_send.setText("Подключение...")
		self._btn_connect.setDisabled(True)
		self._connect_cancel.clear()
		threading.Thread(target=self._connect_and_launch_sender, args=(host, port), daemon=True).start()

	def _connect_and_launch_sender(self, host: str, port: int) -> None:
		if self._connect_cancel.is_set():
			self._btn_connect.setDisabled(False)
			return
		try:
			sock = create_client_socket(host, port, timeout_s=5.0)
		except Exception as e:
			self._status_send.setText(f"Не удалось подключиться: {e}")
			self._btn_connect.setDisabled(False)
			return
		if self._connect_cancel.is_set():
			try:
				sock.close()
			except Exception:
				pass
			self._btn_connect.setDisabled(False)
			return
	
		send_pwd = self._edit_pwd_send.text().strip()
		if send_pwd:
			try:
				send_json_line(sock, {"auth": send_pwd})
			except Exception as e:
				self._status_send.setText(f"Не удалось послать пароль: {e}")
				try:
					sock.close()
				except Exception:
					pass
				self._btn_connect.setDisabled(False)
				return

		handshake_ok = False
		try:
			sock.settimeout(3.0)
			reader = JsonLineReader(sock)
			msg = reader.read_one()
			if isinstance(msg, dict) and msg.get("hello") == 1:
				handshake_ok = True
		except Exception as e:
			self._status_send.setText(f"Приём подтверждения не удался: {e}")
		finally:
			try:
				sock.settimeout(None)
			except Exception:
				pass

		if not handshake_ok:
			try:
				sock.close()
			except Exception:
				pass
			self._btn_connect.setDisabled(False)
			if not self._status_send.text():
				self._status_send.setText("Удалённая сторона не подтвердила соединение.")
			return

		self._status_send.setText("Подключено.")
		self._ok_icon_send.show()
		self._switch_to_english_layout()
		self._sender_socket = sock
		self._local_sender_close.clear()
		self._sender_thread = threading.Thread(target=run_sender_with_socket, args=(sock,), daemon=False)
		self._sender_thread.start()
		
		def sender_waiter() -> None:
			if self._sender_thread is not None:
				self._sender_thread.join()
			if not self._local_sender_close.is_set():
				try:
					self.disconnectedSend.emit("remote")
				except Exception:
					pass
		self._sender_monitor_thread = threading.Thread(target=sender_waiter, daemon=True)
		self._sender_monitor_thread.start()
		self._btn_connect.setDisabled(False)
		QtCore.QTimer.singleShot(1000, self._minimize_window)

	def _show_help(self) -> None:
		text = (
			"<b>Как подключиться</b><br>"
			"1) На принимающем ПК откройте вкладку «Принимать». Включите при необходимости «Разрешить обнаружение…». "
			"Можете задать пароль и включить «Требовать пароль». Сообщите отправителю IP и порт, если не используете поиск.<br><br>"
			"2) На отправляющем ПК откройте «Отправлять», введите IP и порт (или нажмите «Найти в сети»), при необходимости введите пароль и нажмите «Подключиться».<br><br>"
			"<b>Подсказки</b><br>"
			"- Поиск работает в локальной сети, убедитесь что на принимающем включено «Разрешить обнаружение…».<br>"
			"- После успешного подключения окно сворачивается в трей, доступно меню: Открыть, Показать/Скрыть консоль, Выход.<br>"
			"- Язык ввода переключается на английский автоматически перед началом работы.<br><br>"
			"<b>О программе</b><br>"
			"Para {ver}<br>"
			"Разработчик: ErkinKraft"
		).format(ver=self._version)
		msg = QtWidgets.QMessageBox(self)
		msg.setWindowTitle("Справка")
		msg.setTextFormat(QtCore.Qt.RichText)
		msg.setText(text)
		msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
		msg.exec()


def main() -> None:
	app = QtWidgets.QApplication(sys.argv)
	win = ModernWindow()
	win.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()

