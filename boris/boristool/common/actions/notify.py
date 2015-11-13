from __future__ import absolute_import
from __future__ import print_function

from .. import log
from .. import utils


def notify(self, subject="", body=""):
    """Use the platform specific desktop notification system

    subject should be either a standard string which will be used as the
    notification subject or a MSG object.

    body should be a string containing the body of the notification.
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
    subj = utils.parse_vars(subj, self.varDict)
    body = utils.parse_vars(body, self.varDict)

    n = utils.notify(subj, body)

    if n:
        log.log("<action>action.notify(): subject='%s' body='%s...' successful)" %
                (subj, body[:20]), 6)
    else:
        log.log("<action>action.notify(): subject='%s' body='%s...' failed)" %
                (subj, body[:20]), 4)


notify.is_action = True  # flag the function as an action plugin