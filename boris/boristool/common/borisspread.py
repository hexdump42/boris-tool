import sys
import threading
import time
import traceback
from .. _compat import PY2
if PY2:
    import cPickle as pickle
    from cStringIO import StringIO
    import Queue as queue
else:
    import pickle
    from io import StringIO
    import queue

from . import log


# Default Spread server settings - empty means Spread is disabled.
# These are overridden by SPREADSERVER and SPREADPORT config file options.
SPREADSERVER = 'localhost'
SPREADPORT = 4803


# Constants
ANYTIME = -1
BLOCK = 1


# Globals
use_spread = True        # Switch Spread usage on by default; disabled if modules not found

try:
    import spread
except ImportError:
    # no Spread module... disable Spread
    use_spread = False


# Exceptions:
class SpreadError(Exception):
    pass


class SpreadInitError(Exception):
    pass


class Message(object):
    """Defines a Spread message object which will be placed in the
    message queue waiting to be sent. Normally it will be sent instantly
    but it is possible (like when Spread server is down or network is
    unavailable) that the message could be sent some time after being
    inserted into the queue.
    Besides the notification message itself, this object contains a
    time parameter defining how long after being inserted into the
    queue the message is still valid for sending."""

    def __init__(self, emsg, validity_time):
        self.emsg = emsg                        # the notification message
        self.validity_time = validity_time        # message validity time (minutes)
        self.timestamp = time.time()                # store object creation time

    def __str__(self):
        string = str(self.emsg)
        return(string)

    def time_valid(self):
        """Calculate if message is still valid to be sent based on when
        it was created (self.timestamp) and the validity time
        (self.validity_time) setting."""

        if self.validity_time == ANYTIME:
            return True             # don't care when message is sent

        now = time.time()
        if (now-self.timestamp) <= self.validity_time*60.0:
            return True             # message still valid
        else:
            return False            # no longer valid to send


class Spread(object):
    """Sets up Spread connection if possible and starts dedicated Spread
    thread to handle all messaging."""

    def __init__(self):
        global use_spread
        if not use_spread:
            raise SpreadInitError("Spread modules not found")

        global SPREADPORT
        if not SPREADSERVER and not SPREADPORT:
            use_spread = False
            raise SpreadInitError("Spread administratively disabled")

        if not SPREADPORT:
            SPREADPORT = spread.DEFAULT_SPREAD_PORT
        self.server = "%d@%s" % (SPREADPORT, SPREADSERVER)

        self.eq = queue.Queue()                # Spread message queue

        self.connected = False

    def startup(self):
        """Start the Spread management thread."""

        self.sthread = threading.Thread(group=None, target=self.main,
                                        name='Spread',
                                        args=(), kwargs={})
        self.sthread.setDaemon(1)       # die automatically when Main thread dies
        self.sthread.start()            # start the thread running

    def main(self):
        """The Spread management thread.
        Loop to watch message queue for any Spread notifications to be sent
            from other Spread functions or actions.
        This means no other threads should block when sending Spread notifications.
        """

        while True:
            m = self.eq.get(BLOCK)        # get next message or wait for one
            log.log("<borisSpread>Spread.main(): got msg from queue, size now: %d" %
                    (self.eq.qsize()), 9)
            if m.time_valid():

                while not self.connected:
                    self.connect()

                log.log("<borisSpread>Spread.main(): Sending msg from queue, %s" %
                        (m), 9)
                try:
                    self._actual_send(m.emsg)
                    log.log("<borisSpread>Spread.main(): msg sent, %s" %
                            (m), 6)
                except Exception as details:
                    log.log("<borisSpread>Spread.main(): Spread exception, %s, msg %s not sent" %
                            (details, m), 3)
                    if details[0] == -8 or 'closed mbox' in str(details):
                        # connection has been closed or died, so break out & try to re-connect
                        log.log("<borisSpread>Spread.main(): Spread connection closed unexpectedly", 4)
                        self.connected = False
                        self.eq.put(m)        # put msg back in queue for re-try
            else:
                log.log("<borisSpread>Spread.main(): message no longer valid, discarding %s" %
                        (m), 9)

            if self.eq.qsize() == 0:
                log.log("<borisSpread>Spread.main(): queue empty, disconnecting from Spread.", 9)
                self.disconnect()

    def connect(self):
        """Create a Spread connection.
        """

        waittime = 1     # time to wait before re-connecting

        while not self.connected:
            # Create Spread connection
            log.log("<borisSpread>Spread.connect(): Opening connection to Spread, '%s'" %
                    (self.server), 6)

            try:
                self.connection = spread.connect(self.server, '', 0, 0)
            except spread.error as msg:
                log.log("<borisSpread>Spread.connect(): Spread could not connect, '%s'. Waiting %d secs for retry" %
                        (msg, waittime), 5)
                time.sleep(waittime)
                waittime = min(waittime * 2, 60*10) # inc wait time but max 10 minutes
            else:
                log.log("<borisSpread>Spread.connect(): Connected to Spread, '%s'" %
                        (self.server), 6)
                self.connected = True

    def disconnect(self):
        try:
            log.log("<borisSpread>Spread.disconnect(): disconnecting from Spread.", 6)
            self.connection.disconnect()
        except:
            pass
        self.connected = False

    def join(self):
        self.connection.join('boris')

    def notify(self, emsg, validity_time=ANYTIME):
        """Add Spread notification message to message queue to be sent by
        main Spread management thread as soon as possible.
        """

        m = Message(emsg, validity_time)
        self.eq.put(m)
        log.log("<borisSpread>Spread.notify(): msg added to queue, size now: %d" %
                (self.eq.qsize()), 9)

        return 0

    def _actual_send(self, msg):
        sio = StringIO()
        p = pickle.Pickler(sio)
        p.dump(msg)
        r = self.connection.multicast(spread.FIFO_MESS, 'elvinrrd',
                                      sio.getvalue())
        if r == 0:
            raise SpreadError("Spread multicast failed")

    # Public methods for Boris functions/actions to use

    def Ticker(self, msg, timeout):
        """Send a Spread tickertape message to the Tickertape group Boris'.
        The Tickertape user will be the hostname of the machine sending the message.
        msg is the text string to send (TICKERTEXT).
        """

        msg = {
            'TICKERTAPE': 'Boris',
            'TICKERTEXT': msg,
            'USER': log.hostname,
            'TIMEOUT': timeout,
        }

        r = self.notify( msg, validity_time=10 )        # Send message, within 10 mins

        if r != 0:
            # failed
            log.log("<borisSpread>Spread.Ticker(), notify failed, msg: %s" %
                    (msg), 5)
        else:
            # succeeded
            log.log("<borisSpread>Spread.Ticker(), msg added to queue, msg: %s" %
                    (msg), 6)

        return r

    def rrd(self, key, data):
        """Send a dictionary through Spread to a listener process which should store
        the data into an RRDtool database.
         - 'key' will be matched by the elvinrrd consumer
         - 'data' is a dictionary of data to be sent in the message
        """

        # Create db entry creation 'command'
        edict = {
            'ELVINRRD': key,
            'timestamp': time.time(),
        }
        edict.update(data)                # add data dictionary to edict

        r = self.notify(edict)        # Send message

        if r != 0:
            # failed
            log.log("<borisSpread>Spread.rrd(): notify failed, key:%s" % (key), 5)
        else:
            log.log("<borisSpread>Spread.rrd(): msg added to notify queue, key:%s" % (key), 6)

        return r

    def netsaint(self,data):
        """by Dougal Scott <dwagon@connect.com.au>
        """

        edict = {'NETSAINT': 'NETSAINT'}
        edict.update(data)              # add data dictionary to edict
        r = self.notify(edict)        # Send message
        if r != 0:
            # failed
            log.log("<borisSpread>Spread.netsaint(): notify failed", 4)
        else:
            # succeeded
            log.log("<borisSpread>Spread.netsaint(): notify successful", 8)
        return r
