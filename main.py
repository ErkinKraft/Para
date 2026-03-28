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

from common import create_client_socket, create_server_socket, pick_random_port, wrap_accepted_socket
from receiver import run_receiver_with_socket
from sender import run_sender_with_socket


class ModernWindow(QtWidgets.QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("Клавиатура по сети")
		self.setMinimumSize(560, 360)
		self._apply_modern_style()

		self._central = QtWidgets.QWidget(self)
		self.setCentralWidget(self._central)

		self._stack = QtWidgets.QStackedLayout()
		root_layout = QtWidgets.QVBoxLayout(self._central)
		root_layout.setContentsMargins(24, 24, 24, 24)
		root_layout.setSpacing(16)

		title = QtWidgets.QLabel("Выберите режим")
		title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
		title.setStyleSheet("font-size: 22px; font-weight: 600;")
		root_layout.addWidget(title)
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
				background: #2d2d30; border: 1px solid #3f3f46; border-radius: 8px; padding: 8px;
			}
			QPushButton {
				background: #0078d7; color: white; border: none; border-radius: 10px; padding: 10px 16px; font-weight: 600;
			}
			QPushButton:hover { background: #1c88e5; }
			QPushButton:disabled { background: #3f3f46; color: #aaaaaa; }
			QGroupBox {
				border: 1px solid #3f3f46; border-radius: 10px; margin-top: 20px; padding: 16px;
			}
			QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0px 4px; }
			QLabel[headline=\"true\"] { font-size: 18px; font-weight: 600; }
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
		return w

	def _build_send_page(self) -> QtWidgets.QWidget:
		w = QtWidgets.QWidget()
		l = QtWidgets.QVBoxLayout(w)
		l.setSpacing(12)
		gb = QtWidgets.QGroupBox("Режим отправки")
		gb_l = QtWidgets.QFormLayout(gb)
		self._edit_ip = QtWidgets.QLineEdit()
		self._edit_ip.setPlaceholderText("IP адрес получателя (например, 192.168.1.10)")
		self._spin_port = QtWidgets.QSpinBox()
		self._spin_port.setRange(1, 65535)
		self._spin_port.setValue(30000)
		gb_l.addRow("IP:", self._edit_ip)
		gb_l.addRow("Порт:", self._spin_port)
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
		self._btn_back2.clicked.connect(lambda: self._stack.setCurrentWidget(self._page_role))
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

	def _on_back_from_receive(self) -> None:
		self._stop_server_thread()
		self._receive_port = pick_random_port()
		self._port_label.setText(f"Порт: {self._receive_port}")
		self._status_receive.setText("Ожидание подключения...")
		self._ok_icon_receive.hide()
		self._stack.setCurrentWidget(self._page_role)

	def _start_receive_if_needed(self) -> None:
		if self._server_thread and self._server_thread.is_alive():
			return
		self._status_receive.setText("Ожидание подключения...")
		self._server_stop.clear()
		self._server_thread = threading.Thread(target=self._accept_once_thread, daemon=True)
		self._server_thread.start()

	def _stop_server_thread(self) -> None:
		self._server_stop.set()
		if self._server_socket is not None:
			try:
				self._server_socket.close()
			except Exception:
				pass
			self._server_socket = None

	def _accept_once_thread(self) -> None:
		try:
			server = create_server_socket("0.0.0.0", self._receive_port)
			self._server_socket = server
			# Accept loop with cancellation
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
		threading.Thread(target=run_receiver_with_socket, args=(conn,), daemon=False).start()
		QtCore.QTimer.singleShot(1000, self._minimize_window)

	def _on_connect_send(self) -> None:
		host = self._edit_ip.text().strip()
		port = int(self._spin_port.value())
		if not host:
			self._status_send.setText("Введите IP адрес.")
			return
		self._status_send.setText("Подключение...")
		self._btn_connect.setDisabled(True)
		threading.Thread(target=self._connect_and_launch_sender, args=(host, port), daemon=True).start()

	def _connect_and_launch_sender(self, host: str, port: int) -> None:
		try:
			sock = create_client_socket(host, port, timeout_s=5.0)
		except Exception as e:
			self._status_send.setText(f"Не удалось подключиться: {e}")
			self._btn_connect.setDisabled(False)
			return
		self._status_send.setText("Подключено.")
		self._ok_icon_send.show()
		threading.Thread(target=run_sender_with_socket, args=(sock,), daemon=False).start()
		self._btn_connect.setDisabled(False)
		QtCore.QTimer.singleShot(1000, self._minimize_window)


def main() -> None:
	app = QtWidgets.QApplication(sys.argv)
	win = ModernWindow()
	win.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()

