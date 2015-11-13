
from __future__ import absolute_import
from __future__ import print_function

import os
import string
import sys
import re
import time
from importlib import import_module

from . import log
from . import utils
from . import borisspread


# Globals
UseSyslog = True


# Import syslog python modules if possible
try:
    import syslog
except ImportError:
    UseSyslog = False


# define exceptions
class SpreadRRDFailure(Exception):
    """SpreadRRDFailure: a problem occured when trying to send data to Spread RRD
    listener."""

# DEFINE ALL THE ACTIONS AVAILABLE

class action:
    """The action class defines all the available actions available to
    Boris directives. Every action method (excluding __init__()) is
    an Boris action, called from directive arguments such as 'action'
    and 'act2ok'."""

    def __init__(self):
        self.runcount = 0        # chris 2002-12-29: count consecutive action calls

    def log(self, message, vias):
        """
        Post messages to log file, boris tty, or syslog.
        For logging to the boris tty:       'via' should be 'tty'
        For logging by appending to a file: 'via' should begin with a '/'
        For logging via syslog:             'via' should be 'FACILITY.LEVEL'
        Note that you may specify multiple vias by separating them with a ';'.
        """

        if not isinstance(message, str):
            # if msg is not a string, assume it is a MSG object
            message = message.subject

        # Substitute variables in message string
        message = utils.parse_vars(message, self.varDict)

        for via in vias.split(';'):

            # remove leading and trailing whitespace
            via = via.strip()

            # Determine if this is a syslog-type log request
            syslogmatch = re.match('^([A-Z0-9]+)\.([A-Z]+)$', via.upper())

            # boris tty logging (via == "tty")
            if via == 'tty':
                # get the current day/time
                datetime = time.asctime(time.localtime(time.time()))
                print("%s %s" % (datetime,message))

            # file logging (via like "/path/to/logfile")
            elif via.startswith('/'):
                try:
                    f = open(via, 'a')
                    # get the current day/time
                    datetime = time.asctime(time.localtime(time.time()))
                    f.write("%s %s\n" % (datetime,message))
                    f.close()
                except:
                    log.log("<action>action.log(): unable to open file for append '%s'" %
                            (via), 5)

            # syslog logging (via like "USER.INFO")
            elif syslogmatch is not None:
                """Post messages via syslog().

                The parameter priority should be a string in "facility.level" format,
                defaulting to USER.INFO.  See man syslog(3) for a list of valid
                facilities and levels, or the syslog.h header file.  Feel free to use
                upper or lower case.

                Note that in order to see the log messages, your local syslog daemon
                must be configured to do something with the messages: see man
                syslog.conf(5) for details.
                """

                global UseSyslog
                if not UseSyslog:
                    log.log("<action>action.syslog(): syslog not supported on this system", 5)
                    return

                # The priority is the syslog.LOG_(facility) | syslog.LOG_(level)
                try:
                    prio = eval('syslog.LOG_%s' % (syslogmatch.group(1))) | eval('syslog.LOG_%s' % (syslogmatch.group(2)))
                except:
                    log.log("<action>action.log(): unable to parse valid syslog facility and level from '%s'" %
                            (via), 5)
                    return

                # Send the message off... note that syslog() is UDP, and therefore not
                # acknowledged, so we have no return value
                syslog.syslog(prio, message)

            else:
                log.log("<action>action.log(): unknown logging via '%s'" %
                        (via), 5)

        return

    def email(self, address, subject="", body=""):
        """The standard email action.

        address should be a standard string containing a standard email address
        or list of email addresses separated by ','.

        subject should be either a standard string which will be used as the
        email subject the name of a MSG object.

        body should be a string containing the body of the email.
        """

        if not isinstance(subject, str):
            # if subject is not a string, assume it is a MSG object
            body = subject.message
            subj = subject.subject
        else:
            subj = subject

        # replace text that look like newlines with newlines
        body = body.replace('\\n', '\n')

        # Create problem age and other statistics if this is not the first time
        # the problem was found.
        # Stored in %(problemage)s and %(problemfirstdetect)s
        self.varDict['problemage'] = ''
        self.varDict['problemfirstdetect'] = ''
        t = self.state.faildetecttime
        tl = self.state.lastfailtime
        if tl != t:
            tage = self.state.age()
            agestr = "Problem age: "
            if tage[0] > 0:
                agestr = agestr + " %d year" % tage[0]
                if tage[0] > 1:
                    agestr = agestr + "s"
            if tage[1] > 0:
                agestr = agestr + " %d month" % tage[1]
                if tage[1] > 1:
                    agestr = agestr + "s"
            if tage[2] > 0:
                agestr = agestr + " %d day" % tage[2]
                if tage[2] > 1:
                    agestr = agestr + "s"
            if tage[3] > 0:
                agestr = agestr + " %d hour" % tage[3]
                if tage[3] > 1:
                    agestr = agestr + "s"
            if tage[4] > 0:
                agestr = agestr + " %d minute" % tage[4]
                if tage[4] > 1:
                    agestr = agestr + "s"
            if tage[5] > 0:
                agestr = agestr + " %d second" % tage[5]
                if tage[5] > 1:
                    agestr = agestr + "s"
            if agestr != "":
                self.varDict['problemage'] = agestr
            self.varDict['problemfirstdetect'] = "First detected: %04d/%02d/%02d %d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])

        # run thru utils.parse_vars() to substitute variables from varDict
        address = utils.parse_vars(address, self.varDict)
        subj = utils.parse_vars(subj, self.varDict)
        body = utils.parse_vars(body, self.varDict)

        headers = 'To: %s\nSubject: [%s] %s\n' % (address,log.hostname,subj)
        r = utils.sendmail(headers, body)

        if r:
            log.log("<action>action.email(): address='%s' subject='%s' body='%s...' successful)" %
                    (address,subj,body[:20]), 6)
        else:
            log.log("<action>action.email(): address='%s' subject='%s' body='%s...' failed)" %
                    (address,subj,body[:20]), 4)

    def system(self, cmd):
        """This action allows execution of external commands via the
        os.system() call.  The only user argument, 'cmd', contains the
        string of commands to execute.
        TODO: can/should we check this cmd for security problems ??
        """

        # Substitute variables in string
        cmd = utils.parse_vars(cmd, self.varDict)

        if len(cmd) == 0:
            log.log("<action>action.system(): Error, no command given", 5)
            return

        # Call system() to execute the command
        log.log("<action>action.system(): calling os.system() with cmd '%s'" % (cmd), 6)
        # TODO: possibly not thread-safe to simply call os.system() without
        # locking; this might have to be part of the thread-safe group of
        # system commands in utils.py
        retval = os.system(cmd)

        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.system(): Alert, return value for cmd '%s' is %d" %
                    (cmd,retval), 5)

        log.log("<action>action.system(): cmd '%s', return value %d" %
                (cmd,retval), 6)

    # restart()
    # returns: 0 = success
    #      1-255 = return code of restart call
    #       1001 = Security error - illegal characters in command
    #       1002 = Syntax error - command is empty
    def restart(self, cmd):
        # cmd is cmd to be executed with: '/etc/init.d/cmd start'.
        # cmd should not contain any path information, hence if '/'s are found it
        # is not executed.

        # Substitute variables in string
        cmd = utils.parse_vars(cmd, self.varDict)

        # Security: if cmd contains any illegal characters, "/#;!$%&*|~`", then we abort.
        if utils.charpresent(cmd, '/#;!$%&*|~`') != 0:
            log.log("<action>action.restart(): Alert, restart() arg contains illegal character and is not being executed, cmd is '%s'" %
                    (cmd), 5)
            return 1001

        if len(cmd) == 0:
            log.log("<action>action.restart(): Error, no command given", 5)
            return 1002

        # Build command
        cmd = '/etc/init.d/'+cmd+' start'

        # Call system() to execute the command
        log.log("<action>action.restart(): calling os.system() with cmd '%s'" %
                (cmd), 6)
        # TODO: possibly not thread-safe to simply call os.system() without
        # locking; this might have to be part of the thread-safe group of
        # system commands in utils.py
        retval = os.system(cmd)

        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.restart(): Alert, return value for cmd '%s' is %d" %
                    (cmd,retval), 5)

        log.log("<action>action.restart(): cmd '%s', return value %d" %
                (cmd,retval), 6)

        return retval

    # nice()
    def nice(self, *arg):
        # Can be called with absolute or relative priority as follows:
        # nice(val) - val is new absolute priority,
        # nice(incr, val) - incr is incrementor which should be one of '-' or '+'
        # and val is relative offset.
        # %pid should contain the pid of the process who's priority is being
        # modified.
        # Note that Boris must be running as Super-User to set a negative nice
        # level.

        # Min & max nice values.
        # TODO: Are these different for different systems?  Can we get max & mins
        # from system ??
        nice_min = -20
        nice_max = 19

        if len(arg) < 0 or len(arg) > 2:
            log.log("<action>action.nice(): Error, %d arguments found, expecting 1 or 2" %
                    (len(arg)), 5)
            return

        # if one argument given, it is absolute priority level.
        # if two arguments given, first is incrementor ('-' or '+'), second is
        # offset
        if len(arg) == 1:
            # Absolute priority given
            val = string.atoi(arg[0])
            incr = ''

            # If val out of range, error.
            if val < nice_min or val > nice_max:
                log.log("<action>action.nice(): Error, val out of range, val is %d, range is %d-%d" %
                        (val,nice_min,nice_max), 5)
                return
        elif len(arg) == 2:
            # Relative priority given, incr must be '-' or '+'
            incr = arg[0]
            val = string.atoi(arg[1])
            if incr != '-' and incr != '+':
                log.log("<action>action.nice(): Error, incremental is '%s', expecting '-' or '+'" %
                        (incr), 5)
                return

        # If %pid not defined, error.
        try:
            pid = varDict['pid']
        except KeyError:
            log.log("<action>action.nice(): Error, %%pid is not defined", 5)

        # Build command
        if incr == '':
            cmd = '/usr/bin/renice %d %s' % (val,pid)
        else:
            cmd = '/usr/bin/renice -n %s%d %s' % (incr,val,pid)

        # Call renice()
        log.log("<action>action.nice(): calling os.system() with cmd '%s'" %
                (cmd), 9)
        # TODO: possibly not thread-safe to simply call os.system() without
        # locking; this might have to be part of the thread-safe group of
        # system commands in utils.py
        retval = os.system(cmd)

        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.nice(): Alert, return value for cmd '%s' is %d" % (cmd,retval), 5)

        log.log("<action>action.nice(): cmd '%s', return value %d" % (cmd,retval), 6)

    # borislog()
    def borislog(self, *arg):
        # if one argument supplied, this text is logged with a loglevel of 0
        # if two arguments, first is text to log, second is log level.

        if len(arg) < 0 or len(arg) > 2:
            log.log("<action>action.borislog(): Error, %d arguments found, expecting 1 or 2" %
                    (len(arg)), 5)
            return

        logstr = arg[0]

        # if two arguments given, second arg is log level.  Otherwise assume 0.
        if len(arg) == 2:
            loglevel = string.atoi(arg[1])

            # If loglevel out of range, error.
            if loglevel < log.loglevel_min or loglevel > log.loglevel_max:
                log.log("<action>action.borislog(): Error, loglevel out of range, loglevel is %d, range is %d-%d" %
                        (loglevel,log.loglevel_min,log.loglevel_max), 5)
                return
        else:
            loglevel = log.loglevel_min

        # Parse the text string to replace variables
        logstr = utils.parse_vars(logstr, self.varDict)

        # Log the text
        retval = log.log(logstr, loglevel)

        # Alert if return value == 0
        if retval == 0:
            log.log("<action>action.borislog(): Alert, return value for log.log('%s', %d) is %d" %
                    (logstr,loglevel,retval), 5)
        else:
            log.log("<action>action.borislog(): text '%s', loglevel %d" %
                    (logstr,loglevel), 6)

    def ticker(self, msg, timeout=10):
        """A directive action to send a standard Elvin ticker message.
        See http://elvin.dstc.edu.au/projects/tickertape/ for clients and more
        info.
        - 'msg' is the text string to be send (TICKERTEXT)
        - 'timeout' is the timeout setting for the ticker message (minutes)
        """

        if borisElvin4.UseElvin == 0:
            log.log("<action>action.ticker(): Elvin is not available - skipping.", 5)
            return 0

        if not isinstance(msg, str):
            # if msg is not a string, assume it is a MSG object
            body = msg.subject
        else:
            # msg is a string
            body = msg

        if len(body) == 0:
            # body must contain something
            log.log("<action>action.ticker(): Error, body is empty", 5)
            return

        if type(timeout) != type(1):
            # timeout must be integer
            log.log("<action>action.ticker(): Error, timeout is not integer", 5)
            return

        # Substitute variables in string
        body = utils.parse_vars(body, self.varDict)

        retval = elvin.Ticker(body, timeout)

        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.ticker(): Alert, return value for e.sendmsg('%s') is %d" %
                    (body, retval), 5)
        else:
            log.log("<action>action.ticker('%s') complete" % (body), 6)

    # Temporary: page via email for now...
    # page()
    def page(self, pager, msg):
        self.email(pager, msg)

    def elvindb(self, table, data=None):
        """Send information to remote database listener via Spread.
        Elvin no longer supported, uses spreaddb instead."""
        self.spreaddb(table, data)

    def spreaddb(self, table, data=None):
        """Send information to remote database listener via Spread.
           Data to insert in db can be specified in the data argument as
           'col1=data1, col2=data2, col3=data3' or if data is None it will
           use self.storedict
        """

        log.log("<action>action.spreaddb(table='%s' data='%s')"%
                (table, data), 6)

        if not borisspread.use_spread:
            log.log("<action>action.spreaddb(): Spread is not available - skipping.", 5)
            return 0

        if data is None:
            # if nothing passed in data storedict will be used
            retval = elvin.elvindb(table, self.storedict)
        else:
            data = utils.parse_vars(data, self.varDict)        # substitute variables
            datas = data.split(',')                # separate key/val pairs
            storedict = {}
            for d in datas:
                (key, val) = d.split('=')        # separate key & value
                key = string.strip(key)                        # strip spaces

                val = utils.stripquote(val)                # strip spaces then quotes
                # try to convert val to float or int if possible
                try:
                    val = float(val)
                except ValueError:
                    try:
                        val = int(val)
                    except ValueError:
                        pass

                storedict[key] = val

            retval = elvin.elvindb(table, storedict)

        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.spreaddb('%s', dict): Alert, return value for e.send() is %d" %
                    (table,retval), 5)
        else:
            log.log("<action>action.spreaddb('%s', dict): completed" % (table), 6)

    def elvinrrd(self, key, data):
        """Send information to remote RRDtool database listener via Elvin
        Elvin is no longer supported, so uses spreadrrd instead"""
        self.spreadrrd(key, data)

    def spreadrrd(self, key, *data):
        """Send information to remote RRDtool database listener via Spread.
           key is the RRD name configured in the spread consumer to store the data.
               data is a variable length list of strings of the form 'var=data'
            where var is the RRD variable name and data is the data to store.
               Example use in a directive:
            SYS loadavg1_rrd:
                    rule='True'        # always execute
                    scanperiod='1m'
                    action="spreadrrd('loadavg1-%(h)s', 'loadavg1=%(sysloadavg1)f')"
        """

        log.log("<action>action.spreadrrd( key='%s' data='%s' )" %
                (key, data), 6)

        sendrrd = None
        if borisspread.use_spread:
            sendrrd = spread.rrd

        if sendrrd is None:
            log.log("<action>action.spreadrrd(): No messaging system available - skipping.", 5)
            return 0

        if len(data) == 0:
            log.log("<action>action.spreadrrd(): No data supplied.", 5)
            raise SpreadRRDFailure("no data supplied")

        datadict = {}
        for d in data:
            (var, val) = string.split(d, '=')
            if var is None or var == '' or val is None:
                msg = "data error: var='%s' val='%s'" % (var,val)
                log.log("<action>action.spreadrrd(): %s." % msg, 5)
                raise SpreadRRDFailure(msg)
            var = utils.parse_vars(var, self.varDict)        # substitute variables
            val = utils.parse_vars(val, self.varDict)        # substitute variables
            datadict[var] = val

        key = utils.parse_vars(key, self.varDict)        # substitute variables

        log.log("<action>action.spreadrrd() sending: key='%s' data=%s" %
                (key, datadict), 6)
        retval = sendrrd(key, datadict)

        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.spreadrrd(%s, %s), Alert, return value for e.send() is %d" %
                    (key, datadict, retval), 5)
        else:
            log.log("<action>action.spreadrrd(%s, %s): completed" %
                    (key, datadict), 6)

    def netsaint(self, desc, output, retcode):
        """
        Send information to remote netsaint server via Spread.
        Usage:
            action=netsaint("BorisFS", "Disk / at %(fscapac)s percent", 1)

        By Dougal Scott <dwagon@connect.com.au>
        """

        log.log("<action>action.netsaint(desc='%s', output='%s', retcode=%s)" %
                (desc,output,retcode), 8)

        if not borisspread.use_spread:
            log.log("<action>action.netsaint(), Spread is not available - skipping.", 8)
            return 0

        datadict = {}
        datadict['hostname']=log.hostname
        datadict['desc']=desc
        datadict['output']=utils.parse_vars(output, self.varDict)
        datadict['return']=retcode

        retval = elvin.netsaint(datadict)
        # Alert if return value != 0
        if retval != 0:
            log.log("<action>action.netsaint(%s), Alert, return value for e.send() is %d" %
                    (datadict, retval), 3)
        else:
            log.log("<action>action.netsaint(%s): store ok" % datadict, 7)


def _load_action_plugins():
    """When module is loaded, look for action plugins and add to action class"""
    from os.path import isfile, join, splitext
    from . import actions
    plugin_dir = actions.__path__[0]
    plugin_files = [f for f in os.listdir(plugin_dir)
                    if isfile(join(plugin_dir, f)) and f.endswith('.py')]
    for module_file in plugin_files:
        plugin_module = import_module("boristool.common.actions.%s" % splitext(module_file)[0])
        for func in [f for f in dir(plugin_module) if not f.startswith('_')]:
            plugin = eval("plugin_module.%s" % func)
            if not hasattr(plugin, 'is_action'):
                continue
            if not plugin.is_action:
                continue
            setattr(action, func, plugin)


_load_action_plugins()
