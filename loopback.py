"""
Provides the LoopbackClient and LoopbackServer classes for testing.
"""
import threading, time, logging
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR


class Loopback:
	"""
	Base class of Loopback with timout support.
	"""

	tcp_port				= 8223		# Port to connect to
	timeout					= 0.0		# Seconds to wait before quitting; 0.0 = no timeout
	_connect_enable			= True
	_timeout_thread			= None		# Thread; waits self.timeout seconds then flips self._connect_enable
	socket					= None		# Connected socket
	on_connect_function		= None		# Function to call when a connection is made.


	def _start_timeout_thread(self):
		self._timeout_thread = threading.Thread(target=self._timeout)
		self._timeout_thread.start()


	def _timeout(self):
		"""
		Optional timeout thread. Enable by setting the "timeout" attribute of this
		class to any value other than zero before starting connector threads.
		"""
		quitting_time = time.time() + self.timeout
		while self._connect_enable:
			if time.time() >= quitting_time:
				logging.debug("timed out")
				break
			time.sleep(0.25)
		self._connect_enable = False



class LoopbackClient(Loopback):
	"""
	Makes a TCP connection on the loopback address and returns the connected socket.
	"""

	tcp_connect_timeout		= 2.0		# Used when making a connection to a server


	def connect(self):
		"""
		Attempts to make a connection and waits for threads to exit.
		"""
		self._connect_enable = True
		if self.timeout:
			self._start_timeout_thread()
		while self._connect_enable:
			self.socket = socket(AF_INET, SOCK_STREAM)
			self.socket.settimeout(self.tcp_connect_timeout)
			self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			logging.debug("Client connecting")
			try:
				self.socket.connect(("127.0.0.1", self.tcp_port))
			except Exception as exception:
				logging.error("Client error: %s" % exception)
			else:
				logging.debug("Client made connection")
				if self.on_connect_function:
					self.on_connect_function(self.socket)
				self._connect_enable = False
		if self.timeout:
			self._timeout_thread.join()
		logging.debug("exiting LoopbackClient connect")



class LoopbackServer(Loopback):
	"""
	Makes a TCP connection on the loopback address and returns the connected socket.
	"""

	def connect(self):
		"""
		Accepts a connection attempt.
		"""
		self._connect_enable = True
		if self.timeout:
			self._start_timeout_thread()
		try:
			listen_socket = socket(AF_INET, SOCK_STREAM)
			listen_socket.setblocking(0)
			listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			listen_socket.bind(("127.0.0.1", self.tcp_port))
			listen_socket.listen(5)
			logging.debug("Server listening for connections")
		except Exception as exception:
			logging.error("Server error: %s" % exception)
			self._connect_enable = False
		while self._connect_enable:
			try:
				self.socket, address_pair = listen_socket.accept()
			except BlockingIOError as be:
				pass
			except Exception as exception:
				logging.error(exception)
				self._connect_enable = False
			else:
				logging.debug("Server accepted connection")
				if self.on_connect_function:
					self.on_connect_function(self.socket)
				self._connect_enable = False
		if self.timeout:
			self._timeout_thread.join()
		logging.debug("exiting LoopbackServer connect")

