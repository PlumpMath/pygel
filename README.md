pygel
=====

An implementation of some functionalities of gobject/glib/gio in pure python, but adding a lot of new features.

how to use:

```python
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
```

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
