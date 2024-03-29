
from __future__ import absolute_import
from __future__ import print_function

import time
import os
import sys
import threading

from . import utils

# Logfile & Log level (defaults)
logfile = "/var/log/boris.log"
loglevel = 2
hostname = None                # normally overwritten during startup

adminemail = 'root'
adminlevel = 0
adminlog = []
admin_notify = 86400        # default send admin summaries once per day
admin_notify_time = 0        # track time till next notify

loglevel_min = 0
loglevel_max = 9


def log(text='', level=1):
    """log() - if (level <= loglevel), text is appended to logfile
          with date/time prepended (nothing is ever logged when loglevel is 0).
          If (level <= adminlevel) then store log in adminlog list (never store
          anything if adminlevel is 0).
    """

    if loglevel == 0 and adminlevel == 0:
        return 0                # not logged

    datetime = time.asctime(time.localtime(time.time()))
    threadname = threading.currentThread().getName()
    logtext = "%s (%s)[%d]:%s\n" % (datetime, threadname, level, text)

    logged = 0                        # flag if anything is logged

    if level > 0 and level <= loglevel:
        # log to logfile
        try:
            with open(logfile, 'a') as logf:
                logf.write(logtext)
                logged = logged + 1
        except:
            # Cannot open logfile for writing - save this problem in adminlog
            logstr = "<Log>log() - Log warning - cannot write to logfile '%s'" % logfile
            print(logstr, file=sys.stderr)
            datetime = time.asctime(time.localtime(time.time()))
            logtext = "%s [%d]:%s\n" % (datetime, 3, logstr)
            adminlog.append(logtext)

    if adminlevel > 0 and level <= adminlevel:
        # log to adminlog
        adminlog.append(logtext)
        logged = logged + 1

    return logged                # 0=not logged, >0=logged


def sendadminlog(override=0):
    """sendadminlog() - send adminlog list to adminemail only if there
        is something in this list.
        If override==1 then admin_notify times are ignored.
    """

    global admin_notify_time
    global adminlog

    if override == 0:
        # if no admin_notify_time set, set one and return
        if admin_notify_time == 0:
            admin_notify_time = time.time() + admin_notify
            return

        # if time hasn't reached admin_notify_time then return
        if time.time() < admin_notify_time:
            return

    # time for notify - set new time and send the adminlog
    admin_notify_time = time.time() + admin_notify

    # if there isn't anything in adminlog don't bother
    if len(adminlog) == 0:
        return

    headers = 'To: %s\n' % adminemail
    headers = headers + 'Subject: [%s] Eddie Admin Messages\n' % hostname

    body = "Greetings Eddie Admin '%s', the following log messages are\n" % adminemail
    body = body + "being delivered to you for your perusal.  Enjoy.\n\n"
    body = body + "[Host:%s LogLevel=%d AdminLevel=%d AdminNotify=%s secs]\n" % (hostname,loglevel, adminlevel, admin_notify)
    body = body + "------------------------------------------------------------------------------\n"

    for i in adminlog:
        body = body + "%s" % (i)

    body = body + "------------------------------------------------------------------------------\n"
    r = utils.sendmail(headers, body)

    # clear adminlog
    adminlog = []