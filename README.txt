pygel
=====

An implementation of some functionalities of gobject/glib/gio in pure python, but adding a lot of new features.

how to use:

an example using pygobject,
note the same code is valid using gel,
the only change is:
import gel in the place gobject
import main from gel.


   """
   example using gobject
   """
   
   import socket
   import gobject
   from gtk import main
   import time
   my_socket = socket.socket()
   
   def on_socket_read(self, sock):
   	print "data received", sock.recv(1024)
   
   def idle_generator():
   	v = ['|','/','-','\']
   	n = 0
   	while True:
   		n = (n+1) % len(v)
   		yield v[i]
   
   idle_caret = idle_generator()
   
   def im_idle():
   	print '\r%s' % idle_caret.next()
   	return True
   
   def called_after_10_seconds():
   	print '\r', time.asctime()
   
   gobject.io_add_watch(my_socket, gobject.IO_IN, on_socket_read)
   gobject.idle_add(im_idle)
   gobject.timeout_add(10000, called_after_10_seconds)
   my_socket.connect(("someaddress",SOMEPORT))
   main()
   
   """
   with gel, the only diference is that the main function is in gel.
   """

example using file monitor:

   """
   example using file monitor
   """
   import gel
   from gel.event_lib.file_monitor import FileWatch
   
   file_watcher = FileWatch(gel)
   
   def file_altered(the_path):
       print "the file %s was altered" % the_path
   
   def directory_altered(the_path):
   	print "the directory was altered" % the_path
   
   file_watcher.watch_file('my_file.txt', file_altered)
   file_watcher.watch_file('my_directory', directory_altered)
   
   gel.main()
   
other functionalities of gel is almost the same of gobject,
http://www.pygtk.org/pygtk2reference/gobject-functions.html

currently the functions supported are:

* idle_add(callback, ...)
* io_add_watch(fd, condition, callback, ...)
* source_remove(tag)
* timeout_add(interval_miliseconds, callback, ...)
* timeout_add_seconds(interval_seconds, callback, ...)
* main_quit() <- this function actually belongs to gtk in gobject schema, but in gel belongs
  to gel.
* main()
* get_current_time()

the signal functions will be implemented as soon as possible
