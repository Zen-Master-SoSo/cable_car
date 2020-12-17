# cable\_car

A lightweight, simple set of classes for opening a TCP socket (to a particular
IP or using UDP broadcast) and passing messages between them.

There are three main parts: connectors (which make a connection), the
Messenger (which passes messages across the opened socket), and Message
(a class which encodes and decodes itself for transport across the wire).

## Connectors

Of the connectors, you have two choices:

### BroadcastConnector

The _BroadcastConnector_ is the more sophisticated one. This handy little bugger
allows two programs using the same BroadcastConnector setup to easily find each
other on the same subnet.

The BroadcastConnector starts three threads:

1. The first thread broadcasts UDP packets to your current subnet on whatever
   the port you desire.
2. The second thread listens for broadcast packets on the same port, and when
   it "hears" another computer's broadcast, it makes a TCP connection to that
   computer on "the TCP port".
3. Which brings us to the *third* thread, the one that acts as a server and
   listens for TCP connections. When thread 2 on machine "A", and thread 3 on
   machine "B" end up talking  to each other, they are added to the list of
   connected sockets and your program is immediately notified of the connection
   via a callback function which passes the socket.

Easy peasy Japanesy.

The BroadcastConnector keeps running after the first connection is made, so that
multiple peers can be discovered if you desire. If all you need is a one-to-one
peer connection, you simply flip a flag and the threads will die, leaving you with
the one connected socket to play with.

A quick example, (from tests/broadcast_connector\_test.py):

	bc = BroadcastConnector()
	bc.verbose = True
	bc.allow_loopback = True
	bc.timeout = 2.0
	bc.connect()
	assert my_ip in bc.addresses()

Attributes of significant interest:

#### BroadcastConnector.sockets

A dictionary of connected sockets [ip_address => socket]

The "sockets" dictionary contains all the sockets that were created when a
remote computer responded to the broadcast UDP packet by making a TCP
connection to this machine, as well as all the sockets which were created when
this computer responded to a UDP broadcast packet originating from a remote
machine. All of these sockets are setup as non-blocking TCP sockets. Have at
it. (Or read further on about the Messenger class.)

#### BroadcastConnector.on_connect_function

Function to call when a connection is made.

You can set this to any function in a module or a class, and whenever a
successful TCP connection is made, that function will be called with a
connected socket. You may query the socket for the remote computer's ip_address
using "socket.getpeername()" (see the python sockets documentation for more).

Peruse the BroadcastConnector source code for more attributes of interest.

### DirectConnect

Then there's the two subclasses of DirectConnect. These two classes are very
cleverly named "DirectClient" and "DirectServer". If you know the IP address of
the other machine, you can start one instance as a "server" and another
instance as a "client", and receive a connected socket from them which can
communicate with the other (assuming everything else on the network is working
like it's supposed to).

Like the BroadcastConnector, these classes use threads, but only for timing out
if no connection is made.


## Messenger

The whole point of the above operation is to get us a connected socket for the
next step: creating a Messenger.

The Messenger class takes "Message" objects and sends them encoded to another
Messenger waiting at the other end, which decodes it back into an object.
**Assuming** that the program at the other end is using the same Message
classes which are being encoded.

It uses the select() function to service its one socket. May sound like
overkill, but I hear it's the most foolproof way of determining whether or not
a socket is capable of sending and receiving, or is in error.

The Messenger needs to be updated on a cyclic basis for comms to occur. Some
other similar type programs call this the "pump" function, but that sounds
just a little too weird to me, so I use "xfer" instead. Sounds techie.

You call "xfer()" on a regular basis to make sure that comms occur, and then
you can peel off messages from the incoming buffer using "get()". One xfer()
might queue up multiple Message objects to get, so you can call get() as many
times as necessary in one cycle. Where there are no more messages in the queue,
"get()" returns None.

## Message

Which raises the issue of the Message class. Not content with sticking you with
one implementation, cable\_car provides two separate implementations of Message:
"byte" and "JSON". Both are actually sent across the pipe as bytearrays, but
the way they encode is very different.

First of all, a "message" is an instance of class Message, whose attributes and
identity are encoded and sent along the pipe. On the receiving end, the reverse
happens and reassembled instances pop out of the Messenger.get() function. In
your code, you create custom subclasses, which can have their own custom
properties and methods, and pass those back and forth across the network.

Let's say you have a game, and you want to send the position of something on
the screen to the other player. On the receiving end, the location of the thing
on the screen should be rotated 180 degrees, so that it's "seen" from the other
player's perspective. Your custom message class could have "x" and "y"
attributes which represent screen coordinates, and a "flip" or a "rotate"
function which takes those coordinates and fixes them so that they define a
position on the other player's screen.


### JSON messages

The "JSON" implementation of the Message class (found in
cable\_car/json\_messages.py) uses (you guessed it), JSON to encode python
built-in types. This can be pretty much done automatically for any Message
subclass, as long as it uses nothing but built-in types as attributes.

When an instance of a JSON -type Message is created, any arbitrary attributes
that you set on the Message are saved in it's "\_\_dict\_\_", just like any object
in python. The JSON Message class encodes that \_\_dict\_\_ as JSON. Done.

The python JSON encoder naturally handles only built-in types like
dictionaries, lists, and tuples. There's a way to define custom encoders, but
the cable\_car JSON Messsage class skips all that complexity.

The way that cable\_car.json_messages.Message does it is like this: If you need
to use Message attributes which are not built-in types, you can map them to a
dictionary on the way out in your own custom "Message.encode()" function, and map
that dictionary back to your own custom data types in your own custom
"Message.decode()" function. Nothing could be simpler.

Again it bears reapeating, that if you don't use any custom data types (like
custom classes or named tuples), then you don't even have to mess with any of
this. Creating simple JSON encoded messages is as simple as creating an
instance of a subclass with a set of keyword arguments, and you're done. The
same keywords and corresponding values pop out the other end.

So why subclass at all then? You really don't have to, as long as your messages
only pass around built-in types. It's always up to you.


### Byte messages

The second implementation of the Message class (found in
cable\_car/byte\_messages.py) is a bit more difficult to implement, but its a lot
more compact, if that matters. **Every** byte encoded Message that needs to send
data needs to implement the "Message.encode()" and "Message.decode()"
functions. *How* you encode and decode your messages is entirely up to
you. This gives you a chance to get creative.

It's probably best to explain this by example. Inside the byte\_messages module
you'll find the MsgIdentify class. Let's take a close look at each function and
explain how it works. But first, the class definition:

	class MsgIdentify(Message):
		code = 0x1

Notice the class variable; "code". Each Message subclass has a one-byte code
which identifies the class. In the JSON Message class, the full class name is
sent with each message. For the "MsgIdentify" class, that's 13 bytes, including
the quotes, and you'll need some brackets and commas thrown in there to fill
out the JSON encoding. With byte encoded messages, you only need one byte.

Maybe that seems a bit fussy, but if you're writing a game and you expect to
send 20, 50, or 100 messages all in one go, it adds up.

Moving on to the \_\_init\_\_ function:

	def __init__(self, username=None, hostname=None):
		self.username = username or getuser()
		self.hostname = hostname or gethostname()

The MsgIdentify class has two attributes, and in this function we take them as
arguments, or set them programmatically by default. Nothing magic happening
here. They remain as attributes of the Message.

Now we need to figure out a way of encoding these attributes. Here's the way
it's implemented:

	def encode(self):
		""" Encode as "username@hostname" """
		return ("%s@%s" % (self.username, self.hostname)).encode('ASCII')

Simple. We take a string formatted with an ampersand separating our values, and
encode that string into a bytearray. There's no need for a terminator
character, because byte encoded messages don't use terminators. Message length
is sent as a single byte at the beginning. Whatever you return from "encode()",
is all that will be sent, with the addition of the message length (1 byte), and
the message code (1 byte).

Of course, this brings up a very important point. Byte encoded messages have a
size limit. No message may be more than 254 bytes.

That might sound like a **crippling limitation**, and if it is then this library
is not right for your application. The point of this exercise is to create a
messaging system for very small nuggets of state information to be passed
around, like you might need in a game or something, not for sending huge files
or streaming. There's plenty of other libraries for that.

On the receiving end, the same Message class is given the opportunity to
decipher whatever we had encoded on the sender. When the message data comes in,
it is passed to the "decode()" function:

	def decode(self, msg_data):
		""" Decode username and hostname from message data. """
		self.username, self.hostname = msg_data.decode().split("@")

Again, this is a very simple implementation of a very simple problem. You can
use your imagination and come up with many other scenarios. Actually coming up
with your own protocols is kinda fun. I enjoy it, anyway.

It's worth mentioning again, that if a Message class doesn't send or receive
data, but the type of Message itself *is* the message, then there's not going
to be any need to write an "encode()" or "decode()" function at all for that
class.


## Summary

That's pretty much all there is to it. There's an example program included
which sends some status information about your computer(s), which you can
find it at:

	examples/cpu_mon.py

It's 100 lines long and pretty easy to understand. All it does is compile a
list of machine stats (mostly) using the "psutil" library, and sends them to
whichever computer on your network is running the same program, "cpu\_mon.py".
Of course, you'll need "psutil" to get it to work.

## FAQ

#### Are there size limits on the JSON encoded Message?

No.

### Can cable\_car connect using host names?

No. You must do a hostname lookup and give it an ip address.

#### Does cable\_car support SSL?

No. Not in its current incarnation.

#### Does cable\_car support encryption?

I suppose you could encrypt byte -style messages. Sure why not. There's no
terminator character to worry about, after all. But remember that 254 byte
limit! You could also encrypt data and send it as JSON, but now its just
getting weird. This isn't what the library was written for. The initial use
case was sending small, fast messages for games. Encryption is simply outside
the scope of this project.

## Thanks!

Thanks for taking a look. This is one of my first public repos I've shared. And
thanks to all the python and other open source developers who make all of this
fun possible.


