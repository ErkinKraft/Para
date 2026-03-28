import socket
import sys
import threading
from typing import Optional
"""
███████╗██████╗░██╗░░██╗██╗███╗░░██╗██╗░░██╗██████╗░░█████╗░███████╗████████╗
██╔════╝██╔══██╗██║░██╔╝██║████╗░██║██║░██╔╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝
█████╗░░██████╔╝█████═╝░██║██╔██╗██║█████═╝░██████╔╝███████║█████╗░░░░░██║░░░
██╔══╝░░██╔══██╗██╔═██╗░██║██║╚████║██╔═██╗░██╔══██╗██╔══██║██╔══╝░░░░░██║░░░
███████╗██║░░██║██║░╚██╗██║██║░╚███║██║░╚██╗██║░░██║██║░░██║██║░░░░░░░░██║░░░
╚══════╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝╚═╝░░╚══╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░░░░╚═╝░░░"""
from pynput import keyboard

from common import send_json_line


class KeyboardSender:
	def __init__(self, conn: socket.socket) -> None:
		self._conn = conn
		self._listener: Optional[keyboard.Listener] = None
		self._stopped = threading.Event()

	def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
		try:
			if isinstance(key, keyboard.KeyCode) and key.char is not None:
				send_json_line(self._conn, {"t": 1, "k": "char", "v": key.char})
			else:
				send_json_line(self._conn, {"t": 1, "k": "key", "v": getattr(key, "name", str(key))})
		except OSError:
			self.stop()

	def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
		try:
			if isinstance(key, keyboard.KeyCode) and key.char is not None:
				send_json_line(self._conn, {"t": 0, "k": "char", "v": key.char})
			else:
				send_json_line(self._conn, {"t": 0, "k": "key", "v": getattr(key, "name", str(key))})
		except OSError:
			self.stop()

	def start(self) -> None:
		self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release, suppress=False)
		self._listener.start()
		try:
			self._listener.join()
		finally:
			self.stop()

	def stop(self) -> None:
		if self._stopped.is_set():
			return
		self._stopped.set()
		try:
			if self._listener is not None:
				self._listener.stop()
		except Exception:
			pass
		try:
			self._conn.shutdown(socket.SHUT_RDWR)
		except Exception:
			pass
		try:
			self._conn.close()
		except Exception:
			pass


def run_sender_with_socket(conn: socket.socket) -> None:
	sender = KeyboardSender(conn)
	sender.start()


def main() -> None:
	if len(sys.argv) != 3:
		print("Usage: sender.py <host> <port>")
		sys.exit(2)
	host = sys.argv[1]
	port = int(sys.argv[2])
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((host, port))
	run_sender_with_socket(sock)


if __name__ == "__main__":
	main()

