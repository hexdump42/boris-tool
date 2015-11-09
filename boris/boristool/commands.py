
__doc__ = """
Boris-Tool command-line entry points.

Port of https://github.com/hexdump42/boris-tool/blob/master/boris/trunk/boristool/commands.py
to Python 3.4+
"""
from . version import version as __version__

import sys
import os
import time
import signal
import re
import threading
import platform
import argparse

from .common import parseconfig
from .common import directive
from .common import config
from .common import log
from .common import timequeue
from .common import sockets
from .common import datacollect
from .common import utils
from .common import borisspread

# Determine system type
osname = platform.uname()[0]
osver = platform.uname()[2]
osarch = platform.uname()[4]
systype = "%s/%s/%s" % (osname, osver, osarch)

boris_cfg = None

# load directives from common/directives
import boristool.common.directives
config.loadExtraDirectives(boristool.common.directives.__path__[0])


def start_threads(sargs, cargs):
    """Start any support threads that are required.
    Currently these are:
     - Scheduler thread: schedules directives to run [required]
     - Console Server thread: handles connections to console port [optional]
    """

    please_die.clear()                # reset thread signal

    global sthread                # the Scheduler thread
    sthread = threading.Thread(group=None, target=scheduler, name='Scheduler', args=sargs, kwargs={})
    sthread.start()                 # start the thread running

    global cthread                # the Console Server thread
    if config.consport > 0:        # don't start if CONSPORT=0
        cthread = threading.Thread(group=None, target=sockets.console_server_thread, name='Console', args=cargs, kwargs={})
        cthread.setDaemon(1)        # mark thread as Daemon-thread so BORIS will not block when trying to terminate
        cthread.start()

    return()


def stop_threads():
    """Stop any threads started by start_threads().
    """

    please_die.set()                # signal threads to die

    sthread.join()                # wait for scheduler thread to die

    if config.consport > 0:        # console thread not running if CONSPORT=0
        cthread.join()                # wait for console thread to die

    return()


def boris_exit():
    """Exit BORIS cleanly.
    """

    log.log('<boris>boris_exit(): BORIS exiting cleanly.', 5)
    # email admin any remaining messages
    log.sendadminlog(1)
    sys.exit(0)


def sig_handler(sig, frame):
    """Handle all the signals we are interested in.
    """
    if 'SIGHUP' in dir(signal) and sig == signal.SIGHUP:
        # SIGHUP (Hangup) - relead config
        log.log('<boris>sig_handler(): SIGHUP (Hangup) encountered - reloading config', 1)
        stop_threads()
        boris_exit()
        #TODO Reload config code goes here

    elif 'SIGINT' in dir(signal) and sig == signal.SIGINT:
        # SIGINT (CTRL-c) - quit now
        log.log('<boris>sig_handler(): SIGINT (KeyboardInterrupt) encountered - quitting', 1)
        log.log('<boris>sig_handler(): signalling scheduler thread to die', 6)
        stop_threads()
        boris_exit()

    elif 'SIGTERM' in dir(signal) and sig == signal.SIGTERM:
        # SIGTERM (Terminate) - quit now
        log.log('<boris>sig_handler(): SIGTERM (Terminate) encountered - quitting', 1)
        log.log('<boris>sig_handler(): signalling scheduler thread to die', 6)
        stop_threads()
        boris_exit()

    elif 'SIGALRM' in dir(signal) and sig == signal.SIGALRM:
        # SIGALRM (Alarm) - return to force a continue
        return

    else:
        # un-handled signal - log & ignore it
        log.log('<boris>sig_handler(): unknown signal received, %d - ignoring' % sig, 5)


def scheduler(q, cfg, die_event):
    """The BORIS scheduler thread.  This thread tracks the queue of waiting
    checks and executes them in their own thread as required.  It attempts
    to limit the number of actual checking threads running to keep things
    sane.
    """

    while not die_event.isSet():
        loop_start = time.time()        # get time when loop started
        while threading.activeCount() > config.num_threads:
            # do nothing while we have no active threads to play with
            # TODO: if we wait too long, something is probably wrong, so do something about it...
            log.log("<boris>scheduler(): active thread count is %d - waiting till <= %d" %
                    (threading.activeCount(), config.num_threads), 8)
            if time.time() - loop_start > 30*60:
                # if this loop has been running for over 30 mins, then all
                # threads are locked badly and something is wrong.  Force an
                # exit...
                # (there is no ability to kill threads in current Python implementation)
                log.log("<boris>scheduler(): active thread count has been %d for over %d mins - forcing exit" %
                        (threading.activeCount(), (time.time() - loop_start) / 60), 1)
                borisexit()

            try:
                time.sleep(1)
            except IOError:
                # Indicates a signal received under Linux, just continue
                # coz main thread should be setting up to exit.
                log.log("<boris>scheduler(): IOError received by sleep(1) #1 - assume exiting so ignoring", 8)
                pass

        # we have spare threads so get next checking object
        while not die_event.isSet():
            (c, t) = q.head(block=1)        # wait for next object from queue
            log.log("<boris>scheduler(): waiting object is %s at %s" %
                    (c, t), 9)
            if t <= time.time():
                log.log("<boris>scheduler(): object %s,%s is ready to run" %
                        (c, t), 9)
                break
            try:
                time.sleep(1)
            except IOError:
                # Indicates a signal received under Linux, just continue
                # coz main thread should be setting up to exit.
                log.log("<boris>scheduler(): IOError received by sleep(1) #2 - assume exiting so ignoring", 8)
                pass

        # break loop if we have been signaled to die
        if die_event.isSet():
            break

        # retrieve next object from queue
        (c, t) = q.get(block=1)

        if c.args.numchecks > 0:
            # start check in a new thread
            thr = threading.Thread(group=None, target=c.safeCheck, name="%s" %
                                   (c), args=(cfg,), kwargs={})
            log.log("<boris>scheduler(): Starting new thread for %s, %s" %
                    (c, thr), 8)
            thr.setDaemon(1)        # mark thread as Daemon-thread so BORIS will not block when trying to terminate
                                    # with still-running threads.
            thr.start()             # new thread starts running
        else:
            # when numchecks == 0 we don't do any checks at all...
            log.log("<boris>scheduler(): Not scheduling checks for %s when numchecks=%d" %
                    (c, c.args.numchecks), 7)

    log.log("<boris>scheduler(): die_event received, scheduler exiting", 8)


def build_check_queue(q, cfg):
    """Build the queue of checks that the scheduler will start with.
    """
    log.log("<boris>buildCheckQueue(): Adding directives to Queue for hostname '%s'" %
            (log.hostname), 8)

    for i in cfg.groupDirectives.keys():
        # if directive template is 'self', do not schedule it
        d = cfg.groupDirectives[i]
        if d.args.template != 'self':
            if log.hostname in d.excludehosts:
                log.log("<boris>buildCheckQueue(): skipped by excludehosts: %s" %
                        (d,), 8)
            else:
                log.log("<boris>buildCheckQueue(): adding to Queue: %s" %
                        (d,), 8)
                q.put((d, 0))

    shorthostname = log.hostname.split('.')[0]
    shorthostname = shorthostname.replace('-', '_')


def do_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument('config_file', metavar='FILE',
                        default=None,
                        help='Load config from FILE')
    parser.add_argument('--showconfig', action='store_true',
                        help='Dump config')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-d', '--daemon', action='store_true',
                        help='Run as a daemon')
    parser.add_argument('-S', '--startup-delay', metavar='SECONDS', type=int,
                        help='Number of SECONDS to pause at startup before monitoring rule execution commences')
    options = parser.parse_args()

    return options


def main():
    """Startup routine - setup and then start the main loop
    """

    options = do_args()
    config_file = options.config_file
    log.version = __version__

    # Catch the most important signals
    for sig in ('SIGALRM', 'SIGHUP', 'SIGINT', 'SIGTERM'):
        if sig in dir(signal):
            signal.signal(eval("signal.%s" % (sig)), sig_handler)

    log.hostname = platform.node()
    buildstr = 'Unknown'

    boris_cfg = config.Config('__main__')

    # data_modules handles access to all data collector modules
    data_modules = datacollect.DataModules(osname, osver, osarch)
    directive.data_modules = data_modules

    # read in config and rules
    parseconfig.readConf(config_file, boris_cfg)

    log.log("<boris>main(): Configuration complete from '%s'" % (config_file), 6)
    log.log("<boris>main(): BORIS %s%s, systype: %s" % (__version__, buildstr, systype), 5)
    log.log("<boris>main(): Python version: %s" % (sys.version), 5)
    log.log("<boris>main(): oslibdirs: %s" % (data_modules.os_search_path), 8)

    if options.showconfig:
        # Just display configuration & exit
        print('-- Displaying BORIS configuration --')
        print(boris_cfg)
        boris_exit()

    if options.startup_delay:
        delay = options.startup_delay
        if delay > 0:
            log.log("<boris>main(): pausing %d seconds before executing rules" %
                    delay, 5)
            time.sleep(delay)

    if options.daemon:
        # Create a child process, then have the parent exit
        cpid = utils.create_child(True)
        if cpid != 0:
            log.log("<boris>main(): Created child process %d. Parent exiting..." %
                    (cpid,), 6)
            # don't call boris_exit(), because its still running (as a daemon)
            sys.exit(0)

    # Initialise Spread connection and thread to handle Spread messaging
    try:
        spread = borisspread.Spread()
    except borisspread.SpreadInitError as details:
        log.log( "<boris>main(): Spread init failed, %s, Spread functionality will be disabled." %
                (details), 5 )
        spread = None
    else:
        spread.startup()                # Start up the Spread management thread
    boris_cfg.set_spread(spread)

    # Main Loop
    # Initialise check queue
    q = timequeue.TimeQueue(0)
    build_check_queue(q, boris_cfg)
    boris_cfg.q = q

    global please_die
    please_die = threading.Event()  # Event object to notify the scheduler to die
    global sthread

    sargs = (q, boris_cfg, please_die)
    cargs = (boris_cfg, please_die, config.consport)
    start_threads(sargs, cargs)

    while not please_die.isSet():
        try:
            log.log("<boris>main(): Threads in use = %d." % (threading.activeCount()), 8)
            log.log("<boris>main(): Threads: %s" % (threading.enumerate()), 8)

            please_die.wait(1*60)  # sleep for 1 minute between housekeeping duties

        except KeyboardInterrupt:
            # CTRL-c hit - quit now
            log.log('<boris>main(): KeyboardInterrupt encountered - quitting', 1)
            borisexit()

    log.log('<boris>main(): main thread signaled to die - exiting', 1)
    boris_exit()


def agent():
    main()
    try:
        main()
    except:
        e = sys.exc_info()
        sys.stderr.write("BORIS died with exception:")
        sys.stderr.write(str(sys.exc_info()[0]))
        sys.exit(1)
