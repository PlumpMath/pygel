pygel
=====

*pygel* is a pure-python event loop library that works on *Python 2.7+*, *Python 3.4+* and PyPy as well

*pygel* implements its own event loop library from scratch using [socketqueue](http://github.com/caetanus/socketqueue/)

it was initially based on pygtk2/gobject interfaces but has gained its own life and its own interfaces and the pygtk2/gobject is no longer supported anymore

it can interface with another event libraries as Qt4, Qt5, Gi(work in progress), pygtk2(work in progress)

in some level it mimicks single flow application in some methods as: *sleep*, *selector* and *@threaded_wrapper*

A more deatailed documentation is in progress.


Usage Example
---------------------


```python

"""
example using pygel
"""

import socket
from gel import Gel

reactor = Gel()
socket_server = socket.socket()
socket_server.bind(("", 12345))
socket_server.listen()
my_socket = socket.socket()
my_socket.connect(socket_server.getsockname())
connection, _ = socket_server.accept()

def application():
	connection.send(b"some data")
	reactor.sleep(2000)
	print("sleeping doesn't stop the main_loop")

def on_socket_read(sock):
	print("data received", sock.recv(1024))

def timeout():
	print("i'm called after the timeout.")
	reactor.main_quit()

reactor.register_io(my_socket)
reactor.idle_call(application)
reactor.timeout_call_seconds(3.0, timeout)
reactor.main()
```


