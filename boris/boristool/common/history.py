
from __future__ import absolute_import

import threading
from . import log


# Container of data
class Hist:
    pass


# Store a list of historical data
class History:
    def __init__(self, size):
        self.size = size
        self.history = []
        self.history_semaphore = threading.Semaphore()

    def push(self, data):
        self.history_semaphore.acquire()        # Thread safety

        h = Hist()
        for d in list(data.keys()):
            exec("h.%s = data[d]" % (d))
        self.history.insert(0, h)        # add new data to front of list
        if len(self.history) > self.size:
            self.history.pop()                # remove oldest data

        self.history_semaphore.release()

        log.log("<history>History.push(): Added data %s" % (data, ), 8)

    def getsize(self):
        return len(self.history)

    def __getitem__(self, index):
        if index < 1 or index > self.size:
            log.log("<history>History.__getitem__(): index out of range %d"%
                    (index), 4)
            return None

        self.history_semaphore.acquire()        # Thread safety
        data = self.history[index-1]
        self.history_semaphore.release()
        log.log("<history>History.__getitem__(): fetched history[%d]=%s"%
                (index, data), 8)
        return data

    def __repr__(self):
        return "%s" % self.history
