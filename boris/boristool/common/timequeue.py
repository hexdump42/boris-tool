from .._compat import *

if PY2:
    import Queue as queue
else:
    import queue


__doc__ = '''Queue-derived queue ordering objects by next-run time.

TimeQueue is the queuing class derived from Python's Queue class.  It is as
thread-friendly as Queue, the major difference being objects are inserted
into the queue based on a given time.  Objects with the lowest times are
closest to the front of the queue.

To support this, objects have to be added along with their time, so a 
2-tuple must be added, eg: q.put( (obj, time) ).  Similarly q.get()
returns the same 2-tuple.

An extra public method has been added, over what Queue offers, q.head().
This method returns the item (and time) from the front of the queue,
exactly as q.get(), but does not remove it from the queue.
'''


class TimeQueue(queue.Queue):
    """We only need to override the methods below to implement
    our own type of queue.  The parent Queue class handles the rest.
    These will only be called with appropriate locks held."""

    def head(self, block=1, timeout=None):
        """Return the head item in the queue without removing it from
        the queue. (get() will remove item from queue.)

        If optional arg 'block' is 1 (the default), block if
        necessary until an item is available.  Otherwise (block is 0),
        return an item if one is immediately available, else raise the
        Empty exception."""

        if 'not_empty' in dir(self):
            self.not_empty.acquire()
            try:
                if not block:
                    if self._empty():
                        raise Empty
                elif timeout is None:
                    while self._empty():
                        self.not_empty.wait()
                else:
                    if timeout < 0:
                        raise ValueError("'timeout' must be a positive number")
                    endtime = _time() + timeout
                    while self._empty():
                        remaining = endtime - _time()
                        if remaining <= 0.0:
                            raise Empty
                        self.not_empty.wait(remaining)
                item = self._head()
                self.not_full.notify()
                return item
            finally:
                self.not_empty.release()

        return item

    # Initialize the queue representation
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.time_queue = []        # queue in order of time
        self.object_list = []        # list of objects to return

    def _qsize(self):
        return len(self.time_queue)

    # Check whether the queue is empty
    def _empty(self):
        return not self.time_queue

    # Check whether the queue is full
    def _full(self):
        return self.maxsize > 0 and len(self.time_queue) == self.maxsize

    # Put a new item in the queue
    def _put(self, it):
        (item, time) = it
        if self._empty():
            # queue is empty, add to start
            self.time_queue.append(time)
            self.object_list.append(item)
        else:
            i = 0
            while i < len(self.time_queue):
                if time < self.time_queue[i]:
                    self.time_queue.insert(i, time)
                    self.object_list.insert(i, item)
                    break
                i = i + 1
            if i == len(self.time_queue):
                # append to end
                self.time_queue.append(time)
                self.object_list.append(item)

    # Get an item from the queue
    # We always want the first item from queue
    def _get(self):
        time = self.time_queue[0]
        item = self.object_list[0]
        del self.time_queue[0]
        del self.object_list[0]
        return (item,time)

    # Get item from the top of the queue but do not remove it
    def _head(self):
        time = self.time_queue[0]
        item = self.object_list[0]
        return (item, time)
