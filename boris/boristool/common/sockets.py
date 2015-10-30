
import sys
import socket
import string
import select
import traceback
import errno

from . import log


# class wrapper for socket
class socketstate:
    def __init__(self, family, type, s=None):
        # self.state=CONNECTING
        self.fields = ['V1.0', '0'.zfill(6), '0'.zfill(5),
                       '0', '0', '0'.zfill(8), '0'.zfill(8),
                       '0'.zfill(20), '0'.zfill(5), '0001']
        self.comment = ''
        self.resendonerror = 1
        self.family = family
        self.type = type
        if s:
            self.s = s
        else:
            self.s = socket.socket(family, type)
            self.s.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR,
                self.s.getsockopt(socket.SOL_SOCKET,
                                  socket.SO_REUSEADDR) | 1)

    def accept(self):
        conn, addr = self.s.accept()
        return socketstate(self.family, self.type, conn), addr

    def __getattr__(self, name):
        if self.s:
            return getattr(self.s, name)
        else:
            return None


def printState(Config, ccsock):
    # Get the name of this Config object
    cname = Config.name + "."
    if cname == "__main__.":
        cname = ""                # root Config has no name

    # Loop the active config and print the state of each rule
    for i in list(Config.groupDirectives.keys()):
        d = Config.groupDirectives[i]
        # do not show templates or directives where console=None
        if d.args.template != 'self' and d.console_output is not None:
            try:
                cstr = d.console_str()
            except KeyError:
                cstr = "<directive not ready>"
            except:
                e = sys.exc_info()
                tb = traceback.format_list(traceback.extract_tb(e[2]))
                log.log("<sockets>printState(): console_str exception for %s: %s %s %s" %
                        (d, e[0], e[1], tb), 5)
                cstr = ""
            msg = bytearray("%s%s - %s\n" % (cname, d, cstr), encoding='utf-8')
            ccsock.send(msg)

    shorthostname = log.hostname.split('.')[0]

    # chris 2004-12-30: replace '-' with '_' for now...
    # TODO: this is a hack as group names in the config cannot contain '-'; this will
    # be resolved in the future when proper matching options are implemented fully.
    shorthostname = shorthostname.replace('-', '_')

    for c in Config.groups:
        if c.name == shorthostname or (c.name in
                                       list(
                                        Config.classDict.keys()) and
                                       shorthostname in
                                       Config.classDict[c.name]):
            printState(c, ccsock)


def listen(s, Config, die_event):

    while not die_event.isSet():
        # Select timeout 1 second
        try:
            r, w, e = select.select([s], [s], [s], 1.0)
        except:
            e = sys.exc_info()
            tb = traceback.format_list(traceback.extract_tb(e[2]))

            if e[1][0] == 4:    # Interrupted system call, caused by CTRL-C,
                                # which is already being handled
                log.log("<sockets>listen(), Interrupted system call, ignored.", 5)
                continue
            else:
                log.log("<sockets>listen(), exception in select(): %s, %s, %s" %
                        (e[0], e[1], tb), 3)
                break

        if r:
            ccsock, addr = s.accept()
            log.log("<sockets>listen(), accepted connection from %s:%d" %
                    addr, 6)

            ccsock.send(b'Boris Console Gateway\n')

            printState(Config, ccsock)

            ccsock.close()


def console_server_thread(Config, die_event, consport):

    socketerrors = 0
    s = None
    while not die_event.isSet():
        try:
            # set up socket if required
            if s is None:
                s = socketstate(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', consport))
                log.log("<sockets>console_server_thread(), Bind to port %d successful" %
                        (consport), 5)

            s.listen(50)

            # main loop
            listen(s, Config, die_event)

            s.close()

        except socket.error:
            e = sys.exc_info()

            if e[1][0] == errno.EADDRINUSE:                # address already in use
                log.log("<sockets>console_server_thread(), Port %d already in use - exiting" % (consport), 3)
                sys.stderr.write("Boris: port %d already in use, quitting\n" % (consport))
                die_event.set()                # signal other threads to exit
                s.close()
                s = None
                return

            if e[1][0] == errno.ECONNRESET:        # 'Connection reset by peer'
                log.log("<sockets>console_server_thread(), Connection reset by peer - continuing.",
                        7)
                continue

            if e[1][0] == errno.EPIPE:                # 'Broken Pipe'
                log.log("<sockets>console_server_thread(), Broken pipe - continuing.",
                        8)
                continue

            log.log("<sockets>console_server_thread(), Socket error - resetting socket and continuing: %s, %s" %
                    (e[1][0], e[1][1]), 5)

            socketerrors = socketerrors + 1
            s.close()
            s = None

            if socketerrors > 100:
                log.log("<sockets>console_server_thread(), Too many socket errors - exiting.",
                        3)
                die_event.set()                # signal other threads to exit
                return
