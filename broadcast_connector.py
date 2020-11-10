""" Provides the BroadcastConnector connector class """
import threading, time, logging
from socket import *


class BroadcastConnector:
	""" Uses UDP broadcast to announce availability of a service, makes a TCP connection to any other
	machines running the same type of BroadcastConnector, and makes the connected socket(s) available. """

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


	def __init__(self, udp_port = 8222, tcp_port = 8223):
		"""Determine my ip address and create locks"""
		self.udp_port = udp_port
		self.tcp_port = tcp_port


	def connect(self):
		"""Blocking function which starts broadcast/listen and waits for all threads to exit"""
		self._make_connections()
		# Wait for threads to exit:
		self.join_threads()


	def _make_connections(self):
		"""Non-blocking function which starts broadcast/listen and doesn't wait for threads to exit"""
		self.broadcast_enable = True	# In case of re-start
		sock = socket(AF_INET, SOCK_DGRAM)
		sock.connect(('8.8.8.8', 7))
		self.local_ip = sock.getsockname()[0]
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
		"""Wait for all threads to exit normally"""
		try:
			self.__udp_broadcast_thread.join()
			self.__udp_listen_thread.join()
			self.__tcp_listen_thread.join()
			if self.__timeout_thread:
				self.__timeout_thread.join()
		except KeyboardInterrupt:
			self.broadcast_enable = False


	def stop_broadcasting(self):
		"""Stop both broadcasting and listening by setting the \"enable\" flag to False."""
		self.broadcast_enable = False


	def _timeout(self):
		while self.broadcast_enable:
			if time.time() >= self._quitting_time:
				logging.debug("timed out")
				break
			time.sleep(0.25)
		self.broadcast_enable = False


	def __udp_broadcast(self):
		"""This thread sends a UDP packet to the broadcast address/port on a regular interval
		as long as \"self.broadcast_enable\" is TRUE"""
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
		"""This thread listens for connections from other computers doing the same broadcasting.
		When a packet is received, a tcp connection is made with the host which broadcasted.
		When a connection is made, the socket is appended to the \"sockets\" dictionary.
		There is only one listen thread."""
		logging.debug("%s listening for UDP broadcasts on port %s" % (threading.current_thread().name, self.udp_port))
		listen_socket = socket(AF_INET, SOCK_DGRAM)
		listen_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		listen_socket.bind(("", self.udp_port))
		listen_socket.setblocking(0)
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
		logging.debug("%s listening for TCP connections on port %s" % (threading.current_thread().name, self.tcp_port))
		listen_socket = socket(AF_INET, SOCK_STREAM)
		listen_socket.setblocking(0)
		listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		listen_socket.bind(("", self.tcp_port))
		listen_socket.listen(5)
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
		"""Returns a list of ip addresses of computers connected (as either server or client).
		Only valid after broadcasting has started, and really only valid after broadcasting is finished."""
		return self.sockets.keys()



if __name__ == '__main__':
	import sys, os, optparse

	p = optparse.OptionParser()
	p.add_option('--loopback', '-l', action='store_true')
	p.add_option('--verbose', '-v', action='store_true')
	options, arguments = p.parse_args()

	logging.basicConfig(
		stream=sys.stdout,
		level=logging.DEBUG if options.verbose else logging.ERROR,
		format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
	)

	def _show_connection_details(sock):
		mine = sock.getsockname()
		other = sock.getpeername()
		logging.info("*** Connected to %s, port %s as %s, port %s " % (other[0], other[1], mine[0], mine[1]))
		bc.stop_broadcasting()

	bc = BroadcastConnector()
	bc.verbose = True
	bc.allow_loopback = options.loopback
	bc.timeout = 2.0 if options.loopback else 15.0	# Allow time to start on remote machine
	bc.on_connect_function = _show_connection_details
	bc.connect()

	logging.info("Addresses:")
	logging.info(bc.addresses())

	print("OKAY")
	sys.exit(0)

