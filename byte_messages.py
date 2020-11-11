"""Provides classes which are primarily used to pass JSON-encoded messages across a network,
but could also be used for other purposes, such as an undo/redo facility."""

import sys, logging, json
from socket import gethostname
from getpass import getuser
from cable_car.network_messenger import Message


class Byte_Message(Message):
    """A Message class which encodes and decodes as a series of compact bytes.
    The format of each message is:
        Byte
        --------    ----------------------------------------------------------------------
           0        Message length
           1        Single-digit class code, identifying the Message class to instantiate
        2 .. len    (optional) Encoded data which is unique to the subclass
        --------    ----------------------------------------------------------------------

    Each class which subclasses this must define custom encode / decode functions."""

    class_defs = {} # dictionary of <code>: <class definition>


    @classmethod
    def register(cls):
        """Registers a subclass of Message so that instances may be constructed by the Message class."""
        cls.class_defs[cls.code] = cls


    @classmethod
    def peel_from_buffer(cls, read_buffer):
        """ Select the relevant part of a NetworkMessenger's read buffer as a complete message bytearray.
        In the Byte_Message class the determination of message completeness is determined by the number
        of bytes to read from the buffer, determined by the first byte of the message."
        Returns a tuple (Message, bytes_read) """
        if(len(read_buffer) and len(read_buffer) >= read_buffer[0]):
            logging.debug("Received %d-byte message" % read_buffer[0])
            if read_buffer[1] in cls.class_defs:
                msg = cls.class_defs[read_buffer[1]]()
                assert(isinstance(msg, Message))
                if read_buffer[0] > 2:
                    msg.decode_data(read_buffer[2:])
                return msg, read_buffer[0]
            else:
                raise KeyError("%d is not a registered Byte_Message code" % read_buffer[1])
        return None, 0


    def encoded(self):
        """Called from network_messenger, prepends the byte length and class code to the return value of
        this class' encode() function. Do not extend this function. Use the encode() function in your subclass."""
        encoded_data = self.encode()
        data_len = len(encoded_data)
        logging.debug("Encoded %d-bytes of message data" % data_len)
        payload = bytearray([data_len + 2, self.code])
        return payload + encoded_data if data_len else payload


    def encode(self):
        """Default function which returns an empty bytearray. This is the function to extend in your subclass."""
        return bytearray()


    def decode_data(self, msg_data):
        """Default function which does nothing. Extend in your subclass to populate class attributes."""
        pass


    def __str__(self):
        return self.__class__.__name__



class Identify(Byte_Message):
    code = 0x1
    def __init__(self, username=None, hostname=None):
        self.username = username or getuser()
        self.hostname = hostname or gethostname()


    def decode_data(self, msg_data):
        """Read username and hostname from message data."""
        self.username, self.hostname = msg_data.decode().split("@")


    def encode(self):
        """Encode username@hostname."""
        return ("%s@%s" % (self.username, self.hostname)).encode('ASCII')


class Join(Byte_Message):
    code = 0x2
    pass



class Retry(Byte_Message):
    code = 0x3
    pass



class Quit(Byte_Message):
    code = 0x4
    pass



Identify.register()
Join.register()
Retry.register()
Quit.register()


if __name__ == '__main__':

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="%(relativeCreated)6d [%(filename)24s:%(lineno)3d] %(message)s"
    )

    # Test basic encoding/decoding:

    msg = Join()
    assert(isinstance(msg, Join))
    encoded_message = msg.encoded()

    buff = encoded_message
    msg, pos = Byte_Message.peel_from_buffer(buff)
    assert(isinstance(msg, Join))
    assert(pos == len(encoded_message))

    msg = Identify()
    assert(isinstance(msg, Identify))
    assert(msg.username is not None)
    assert(msg.hostname is not None)
    username = msg.username
    hostname = msg.hostname
    encoded_message = msg.encoded()

    buff = encoded_message
    msg, pos = Byte_Message.peel_from_buffer(buff)
    assert(isinstance(msg, Identify))
    assert(pos == len(encoded_message))
    assert(username == msg.username)
    assert(hostname == msg.hostname)

    # Test passing several messages in one buffer
    buff = Join().encoded()
    buff.extend(Identify().encoded())
    buff.extend(Retry().encoded())
    buff.extend(Quit().encoded())

    msg, byte_len = Byte_Message.peel_from_buffer(buff)
    buff = buff[byte_len:]
    assert(isinstance(msg, Join))
    msg, byte_len = Byte_Message.peel_from_buffer(buff)
    buff = buff[byte_len:]
    assert(isinstance(msg, Identify))
    msg, byte_len = Byte_Message.peel_from_buffer(buff)
    buff = buff[byte_len:]
    assert(isinstance(msg, Retry))
    msg, byte_len = Byte_Message.peel_from_buffer(buff)
    buff = buff[byte_len:]
    assert(isinstance(msg, Quit))


    print("OKAY")


