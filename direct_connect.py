"""
Provides the DirectClient and DirectServer classes for testing.
"""
import threading, time, logging
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR


class DirectConnect:
	"""
	Base class of DirectConnect with timout support.
	"""

	timeout					= 0.0		# Seconds to wait before quitting; 0.0 = no timeout
	_connect_enable			= True		# Attempt to connect only while this flag stays "True"
	_timeout_thread			= None		# Thread; waits self.timeout seconds then flips self._connect_enable
	_timed_out				= False
	socket					= None		# Connected socket


	def __init__(self, tcp_port=8223, ip_address="127.0.0.1"):
		self.tcp_port = tcp_port
		self.ip_address = ip_address


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
				self._timed_out = True
				break
			time.sleep(0.25)
		self._connect_enable = False


	def cancel(self):
		self._connect_enable = False



class DirectClient(DirectConnect):
	"""
	Makes a TCP connection on the loopback address and returns the connected socket.
	"""

	tcp_connect_timeout		= 2.0		# Used when making a connection to a server


	def connect(self):
		"""
		Attempts to make a connection and waits for threads to exit.
		"""
		try:
			self.socket = socket(AF_INET, SOCK_STREAM)
			self.socket.settimeout(self.tcp_connect_timeout)
			self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			logging.debug("Client connecting")
		except Exception as exception:
			logging.error("Client error: (%s) %s" % (type(exception).__name__, exception))
			return
		if self.timeout:
			self._start_timeout_thread()
		self._connect_enable = True
		while self._connect_enable:
			try:
				self.socket.connect((self.ip_address, self.tcp_port))
			except ConnectionRefusedError:
				pass
			except Exception as exception:
				logging.error("Client error: (%s) %s" % (type(exception).__name__, exception))
				self._connect_enable = False
			else:
				logging.debug("Client made connection")
				self._connect_enable = False
		if self.timeout:
			self._timeout_thread.join()
		if self._timed_out:
			self.socket.close()
			self.socket = None
		logging.debug("exiting DirectClient connect")



class DirectServer(DirectConnect):
	"""
	Makes a TCP connection on the loopback address and returns the connected socket.
	"""

	def connect(self):
		"""
		Accepts a connection attempt.
		"""
		try:
			listen_socket = socket(AF_INET, SOCK_STREAM)
			listen_socket.setblocking(False)
			listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			listen_socket.bind((self.ip_address, self.tcp_port))
			listen_socket.listen(5)
			logging.debug("Server listening for connections")
		except Exception as exception:
			logging.error("Server error: (%s) %s" % (type(exception).__name__, exception))
			return
		if self.timeout:
			self._start_timeout_thread()
		self._connect_enable = True
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
				self._connect_enable = False
		if self.timeout:
			self._timeout_thread.join()
		if self._timed_out:
			self.socket.close()
			self.socket = None
		logging.debug("exiting DirectServer connect")

