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
from typing import Optional
from pynput import keyboard

from common import JsonLineReader


class KeyboardReceiver:
	def __init__(self, conn: socket.socket) -> None:
		self._conn = conn
		self._reader = JsonLineReader(conn)
		self._controller = keyboard.Controller()
		self._stopped = threading.Event()
		self._remote_requested_close = False

	def _apply_event(self, typ: int, kind: str, value: str) -> None:
		try:
			if kind == "char":
				target = value
			else:
				target = getattr(keyboard.Key, value, None)
				if target is None:
					return

			if typ == 1:
				self._controller.press(target)
			else:
				self._controller.release(target)
		except Exception:
			pass

	def start(self) -> None:
		while not self._stopped.is_set():
			msg = self._reader.read_one()
			if msg is None:
				break
		
			if isinstance(msg, dict) and msg.get("bye") == 1:
				self._remote_requested_close = True
				break
			typ = msg.get("t")
			kind = msg.get("k")
			value = msg.get("v")
			if isinstance(typ, int) and isinstance(kind, str) and isinstance(value, str):
				self._apply_event(typ, kind, value)
		self.stop()

	def stop(self) -> None:
		if self._stopped.is_set():
			return
		self._stopped.set()
		try:
			self._conn.shutdown(socket.SHUT_RDWR)
		except Exception:
			pass
		try:
			self._conn.close()
		except Exception:
			pass


def run_receiver_with_socket(conn: socket.socket) -> None:
	receiver = KeyboardReceiver(conn)
	receiver.start()


def main() -> None:
	if len(sys.argv) != 2:
		print("Usage: receiver.py <port>")
		sys.exit(2)
	port = int(sys.argv[1])
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind(("0.0.0.0", port))
	server.listen(1)
	conn, _ = server.accept()
	run_receiver_with_socket(conn)


if __name__ == "__main__":
	main()

