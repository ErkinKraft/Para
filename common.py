import json
import socket
import threading
from typing import Any, Dict, Optional, Tuple
"""
███████╗██████╗░██╗░░██╗██╗███╗░░██╗██╗░░██╗██████╗░░█████╗░███████╗████████╗
██╔════╝██╔══██╗██║░██╔╝██║████╗░██║██║░██╔╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝
█████╗░░██████╔╝█████═╝░██║██╔██╗██║█████═╝░██████╔╝███████║█████╗░░░░░██║░░░
██╔══╝░░██╔══██╗██╔═██╗░██║██║╚████║██╔═██╗░██╔══██╗██╔══██║██╔══╝░░░░░██║░░░
███████╗██║░░██║██║░╚██╗██║██║░╚███║██║░╚██╗██║░░██║██║░░██║██║░░░░░░░░██║░░░
╚══════╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝╚═╝░░╚══╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░░░░╚═╝░░░"""

DEFAULT_HOST = "0.0.0.0"
RANDOM_PORT_RANGE: Tuple[int, int] = (20000, 60000)


def create_server_socket(bind_host: str, bind_port: int) -> socket.socket:
	server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
	server_sock.bind((bind_host, bind_port))
	server_sock.listen(1)
	return server_sock


def create_client_socket(target_host: str, target_port: int, timeout_s: float = 5.0) -> socket.socket:
	client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
	client_sock.settimeout(timeout_s)
	client_sock.connect((target_host, target_port))
	client_sock.settimeout(None)
	return client_sock


def wrap_accepted_socket(conn: socket.socket) -> socket.socket:
	try:
		conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
	except OSError:
		pass
	return conn


def send_json_line(sock: socket.socket, message: Dict[str, Any]) -> None:
	data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
	sock.sendall(data)


class JsonLineReader:
	def __init__(self, sock: socket.socket, max_buffer_size: int = 1_000_000) -> None:
		self._sock = sock
		self._buffer = bytearray()
		self._lock = threading.Lock()
		self._max_buffer_size = max_buffer_size

	def read_one(self) -> Optional[Dict[str, Any]]:
		while True:
			with self._lock:
				nl_index = self._buffer.find(b"\n")
				if nl_index != -1:
					line = self._buffer[:nl_index]
					del self._buffer[: nl_index + 1]
					if not line:
						continue
					try:
						return json.loads(line.decode("utf-8"))
					except json.JSONDecodeError:
						continue

			chunk = self._sock.recv(4096)
			if not chunk:
				return None
			with self._lock:
				self._buffer.extend(chunk)
				if len(self._buffer) > self._max_buffer_size:
					self._buffer.clear()


def pick_random_port() -> int:
	import random

	return random.randint(RANDOM_PORT_RANGE[0], RANDOM_PORT_RANGE[1])


