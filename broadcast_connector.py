"""
Provides the BroadcastConnector connector class.
"""
import threading, time, logging
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR


class BroadcastConnector:
	"""
	Uses UDP broadcast to announce availability of a service, makes a TCP
	connection to any other machines running the same type of BroadcastConnector,
	and makes the connected socket(s) available.
	"""

	udp_port				= 8222
	tcp_port				= 8223
	broadcast_interval		= 1
	verbose					= False
	allow_loopback			= False		# Whether to accept connections from, or try to connect to, the same ip address
	local_ip				= None		# Used especially to filter localhost when not "allow_loopback"
	tcp_connect_timeout		= 2.0		# Used when making a connection to a server which has broadcasted
	timeout					= 0.0		# Seconds to wait before quitting; 0.0 = no timeout
	broadcast_enable		= False		# Flag which tells the threads to exit when it goes False
	__udp_broadcast_thread	= None		# Thread which broadcasts on "udp_port"
	__udp_listen_thread		= None		# Thread which listens for broadcast messages on "udp_port" and initiates tcp connections
	__tcp_listen_thread		= None		# Thread which listens for tcp (SOCK_STREAM) connection requests
	__timeout_thread		= None		# Thread which waits self.timeout seconds then flips self.broadcast_enable
	sockets					= {}		# A dictionary of connected sockets [ip_address => socket]
	on_connect_function		= None		# Function to call when a connection is made.


	@classmethod
	def get_my_ip(cls):
		sock = socket(AF_INET, SOCK_DGRAM)
		sock.connect(('8.8.8.8', 7))
		return sock.getsockname()[0]


	def connect(self):
		"""
		Blocking function which starts broadcast/listen and waits for threads to exit.
		"""
		self._start_connector_threads()
		# Wait for threads to exit:
		self.join_threads()


	def _start_connector_threads(self):
		"""
		Non-blocking function which starts broadcast/listen and doesn't wait for
		threads to exit.
		"""
		self.broadcast_enable = True	# In case of re-start
		self.local_ip = self.get_my_ip()
		# Create a lock for appending to "sockets"
		self.__socket_lock = threading.Lock()
		# Create threads:
		self.__udp_broadcast_thread = threading.Thread(target=self.__udp_broadcast)
		self.__udp_listen_thread = threading.Thread(target=self.__udp_listen)
		self.__tcp_listen_thread = threading.Thread(target=self.__tcp_listen)
		# Start threads:
		self.__udp_broadcast_thread.start()
		self.__udp_listen_thread.start()
		self.__tcp_listen_thread.start()
		if self.timeout:
			self._quitting_time = time.time() + self.timeout
			self.__timeout_thread = threading.Thread(target=self._timeout)
			self.__timeout_thread.start()


	def join_threads(self):
		"""
		Wait for all threads to exit normally.
		"""
		try:
			self.__udp_broadcast_thread.join()
			self.__udp_listen_thread.join()
			self.__tcp_listen_thread.join()
			if self.__timeout_thread:
				self.__timeout_thread.join()
		except KeyboardInterrupt:
			self.broadcast_enable = False


	def stop_broadcasting(self):
		"""
		Stop both broadcasting and listening by setting the "broadcast_enable" flag False.
		"""
		self.broadcast_enable = False


	def _timeout(self):
		"""
		Optional timeout function. Enable by setting the "timeout" attribute of this
		class to any value other than zero.
		"""
		while self.broadcast_enable:
			if time.time() >= self._quitting_time:
				logging.debug("timed out")
				break
			time.sleep(0.25)
		self.broadcast_enable = False


	def __udp_broadcast(self):
		"""
		This thread sends a UDP packet to the broadcast address/port on a regular
		interval as long as "self.broadcast_enable" is True.
		"""
		logging.debug("%s sending broadcast messages from %s, port %s" % (threading.current_thread().name, self.local_ip, self.udp_port))
		broadcast_socket = socket(AF_INET, SOCK_DGRAM)
		broadcast_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		next_broadcast = time.time() + 0.1
		while self.broadcast_enable:
			time.sleep(0.25)
			if time.time() >= next_broadcast:
				broadcast_socket.sendto(b"BROADCAST", ("255.255.255.255", self.udp_port))
				next_broadcast = time.time() + self.broadcast_interval
		logging.debug("%s (sending broadcast messages) exiting." % (threading.current_thread().name))


	def __udp_listen(self):
		"""
		This thread listens for connections from other computers doing the same
		broadcasting. When a packet is received, a tcp connection is made with the host
		which broadcasted. When a connection is made, the socket is appended to the
		"sockets" dictionary.

		There is only one listen thread.
		"""
		logging.debug("%s listening for UDP broadcasts on port %s" % (threading.current_thread().name, self.udp_port))
		try:
			listen_socket = socket(AF_INET, SOCK_DGRAM)
			listen_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
			listen_socket.bind(("", self.udp_port))
			listen_socket.setblocking(0)
		except Exception as e:
			self.broadcast_enable = False
			logging.error(e)
			return
		while self.broadcast_enable:
			try:
				data, address_pair = listen_socket.recvfrom(1024)
			except BlockingIOError as be:
				continue
			except Exception as e:
				logging.error(e)
				self.broadcast_enable = False
			else:
				# logging.debug("%s received broadcast packet from %s, port %s" % (threading.current_thread().name, address_pair[0], address_pair[1]))
				address = address_pair[0]
				if address not in self.addresses() and (self.allow_loopback or address != self.local_ip):
					sock = socket(AF_INET, SOCK_STREAM)
					sock.settimeout(self.tcp_connect_timeout)
					sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
					logging.debug("%s connecting to %s" % (threading.current_thread().name, address))
					try:
						sock.connect((address, self.tcp_port))
					except Exception as e:
						sock.close()
						logging.error(e)
					else:
						self.__socket_lock.acquire(1)
						if address not in self.sockets.keys():
							self.sockets[address] = sock
						self.__socket_lock.release()
						if self.on_connect_function:
							self.on_connect_function(sock)
		logging.debug("%s (listening for UDP broadcasts) exiting." % (threading.current_thread().name))


	def __tcp_listen(self):
		"""
		This thread listens for TCP connections and adds the connected socket to
		"sockets" list.
		"""
		logging.debug("%s listening for TCP connections on port %s" % (threading.current_thread().name, self.tcp_port))
		try:
			listen_socket = socket(AF_INET, SOCK_STREAM)
			listen_socket.setblocking(0)
			listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			listen_socket.bind(("", self.tcp_port))
			listen_socket.listen(5)
		except Exception as e:
			self.broadcast_enable = False
			logging.error(e)
			return
		while self.broadcast_enable:
			try:
				sock, address_pair = listen_socket.accept()
			except BlockingIOError as be:
				pass
			except Exception as e:
				logging.error(e)
				self.broadcast_enable = False
			else:
				logging.debug("%s accepted TCP connection from %s" % (threading.current_thread().name, address_pair[0]))
				self.__socket_lock.acquire(1)
				if address_pair[0] not in self.sockets.keys():
					self.sockets[address_pair[0]] = sock
				self.__socket_lock.release()
				if self.on_connect_function:
					self.on_connect_function(sock)
		logging.debug("%s (listening for TCP connections) exiting." % (threading.current_thread().name))


	def addresses(self):
		"""
		Returns a list of ip addresses of computers connected (as either server or
		client). Only valid after broadcasting has started, and really only valid after
		broadcasting is finished.
		"""
		return self.sockets.keys()


