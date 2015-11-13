
import sys
import string
import os

from . import directive
from . import definition
from . import log
from . import utils


# Define exceptions
class ParseFailure(Exception):
    pass


# DEFAULT SETTINGS
# Scan Period in seconds (default is 10 minutes)
scanperiod = 10*60
scanperiodraw = '10m'

# Maximum number of threads Boris will attempt to limit to.
# Set with NUMTHREADS in config.
num_threads = 10

# Default port to colisten to console connections
consport = 33343

# Constantly rescan config files for changes? True/False
# Set with RESCANCONFIGS in config.
rescan_configs = True


class Config:
    """The main Boris configuration class."""

    def __init__(self, name, parent=None):
        if len(name) < 1:
            raise SyntaxError

        self.name = name
        self.type = "Config"
        # flag to indicate if we have displayed some info about the config (ie: only display it once)
        self.display = 0

        # initialise our config colists/dicts
        self.groupDirectives = {}                # holds all directives for this group
        self.MDict = definition.MsgDict()        # object which holds all Message definitions
        if parent is not None:
            self.MDict.update(parent.MDict)        # inherit parent M-tree

        self.aliasDict = {}                        # dictionary of ALIASes
        self.NDict = {}                                # dictionary of Notification definitions
        self.classDict = {}                        # dictionary of Class definitions

        self.groups = []
        self.configfiles = {}                        # dictionary of config file mtimes

        # Inherit parent properties if given
        self.parent = parent
        if parent is not None:
            self.aliasDict.update(parent.aliasDict)
            self.NDict.update(parent.NDict)

    def __str__(self):
        """Display Config in readable format (ie: for debugging)."""

        str = "<Config name='%s' type='%s'" % (self.name, self.type)
        str = str + "\n\n groupDirectives: %s" % self.groupDirectives
        str = str + "\n\n groups:"
        for i in self.groups:
            str = str + " %s" % i
        str = str + "\n\n MDict:"
        for i in self.MDict.keys():
            str = str + " %s" % self.MDict[i]
        str = str + "\n\n aliasDict: %s" % self.aliasDict
        str = str + "\n\n NDict:"
        for i in self.NDict.keys():
            str = str + " %s" % self.NDict[i]
        str = str + "\n\n classDict: %s" % self.classDict
        str = str + "\n>"
        return str

    def newgroup(self, tokcolist, toktypes, parent=None):
        """Add new rules group."""

        # Require 3 tokens, ('group', <str>, ':')
        if len(tokcolist) < 3:
            raise ParseFailure("Syntax error at group statement")

        # 3rd token must be a ':'
        if tokcolist[2] != ':':
            raise ParseFailure("Expected ':', found '%s'" % tokcolist[2])

        # group name (2nd token) should be text (ie: token type 'NAME')
        if toktypes[1] != 'NAME':
            raise ParseFailure("Unexpected group type, should be text")
        groupname = tokcolist[1]

        # duplicate group names not allowed at same level
        for i in parent.groups:
            if groupname == i.name:
                log.log("<config>newgroup(): merging group %s with previous definition"
                        % (groupname), 8)
                return i

        # Create new group
        newgroup = Config(groupname, parent)

        # Add to parent's group colist
        if parent is not None:
            parent.groups.append(newgroup)

        return newgroup

    def give(self, obj):
        """Object 'obj' is given to Config, and placed in the appropriate colist.
        """

        if obj.type == 'N':
            self.NDict[obj.name] = obj
        elif obj.type == 'M':
            self.MDict[obj.name] = obj
        elif obj.type == 'ALIAS':
            self.aliasDict[obj.name] = obj.value
        elif obj.type == 'CLASS':
            self.classDict[obj.name] = obj.hosts
        elif obj.type in directives.keys():
            if obj.ID in self.groupDirectives.keys():
                raise ParseFailure("Duplicate directive name: %s" % obj.ID)
            # add directive
            self.groupDirectives[obj.ID] = obj
        else:
            return

    def set_spread(self, spread):
        """Store the Spread connection object, and pass through to other
        objects which need it (e.g., action module)."""

        self.spread = spread
        from . import action
        action.spread = spread

    def checkfiles(self):
        """Check if any of the config or rules files have been modified."""

        for f in self.configfiles.keys():
            try:
                if os.stat(f)[8] != self.configfiles[f]:                # check mtime
                    return True
            except os.error:
                if sys.exc_value == 'Connection timed out':
                    # can happen when files on NFS mounted filesystem
                    log.log("<config>Config.checkfiles(): Timeout while trying to stat '%s' - skipping file checks."
                            % (f), 5)
                    return False

        return False


# The base configuration class.  Derive all config options from this base class.
class ConfigOption(object):
    def __init__(self, colist, typecolist):
        self.basetype = 'ConfigOption'     # the object can know its own basetype
        self.type = colist[0]                # the config option type of this instance


# CONFIGURATION OPTIONS

# SCANPERIOD - the time (in seconds) to pause between checks
class SCANPERIOD(ConfigOption):
    def __init__(self, colist, typecolist):

        super(SCANPERIOD, self).__init__(colist, typecolist)

        # if we don't have 3 or 4 elements ['SCANPERIOD', '=', <int>, [<char>,]]
        # then raise an error
        if len(colist) < 3 or len(colist) > 4:
            raise ParseFailure("SCANPERIOD definition has %d tokens when expecting 3 or 4"
                               % len(colist))

        # ok, value is 3rd[+4th] colist element
        if len(colist) == 3:
            value = colist[2]
        else:
                value = colist[2]+colist[3]

        global scanperiodraw
        scanperiodraw = value                        # keep the raw scanperiod
        value = utils.val2secs(value)                # convert value to seconds
        if value > 0:
            global scanperiod
            scanperiod = value                        # set the config option
        log.log("<config>SCANPERIOD(): scanperiod set to %s (%d seconds)."
                % (scanperiodraw, scanperiod), 8)


# LOGFILE - where to store log messages
class LOGFILE(ConfigOption):
    def __init__(self, colist, typecolist):
        super(LOGFILE, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['LOGFILE', '=', <val>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("LOGFILE definition has %d tokens when expecting 3"
                               % len(colist))

        # ok, value is 3rd colist element
        log.logfile = utils.stripquote(colist[2])  # set the config option
        log.log("<config>LOGFILE(): logfile set to '%s'." % (log.logfile), 8)


# LOGLEVEL - how much logging to do
class LOGLEVEL(ConfigOption):
    def __init__(self, colist, typecolist):
        super(LOGLEVEL, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['LOGLEVEL', '=', <val>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("LOGLEVEL definition has %d tokens when expecting 3"
                               % len(colist))

        # ok, value is 3rd colist element
        loglevel = int(colist[2])
        if loglevel < 0 or loglevel > 9:
            raise ParseFailure("LOGLEVEL value should be between 0 and 9 not %d"
                               % loglevel)
        log.loglevel = loglevel               # set the config option
        log.log("<config>LOGLEVEL(): loglevel set to %d" % (log.loglevel), 8)


# ADMIN - email address of Boris administrator
# currently only supports 1 email address
class ADMIN(ConfigOption):
    def __init__(self, colist, typecolist):
        super(ADMIN, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['ADMIN', '=', <str>] then
        # raise an error
        if len(colist) != 3:
            raise ParseFailure("ADMIN definition has %d tokens when expecting 3"
                               % len(colist))

        # ok, value is 3rd colist element
        log.adminemail = utils.stripquote(colist[2])                # set the config option
        log.log("<config>ADMIN(): admin set to '%s'." % (log.adminemail), 8)


# ADMINLEVEL - how much logging to send to admin
class ADMINLEVEL(ConfigOption):
    def __init__(self, colist, typecolist):
        super(ADMINLEVEL, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['ADMINLEVEL', '=', <val>] then
        # raise an error
        if len(colist) != 3:
            raise ParseFailure("ADMINLEVEL definition has %d tokens when expecting 3"
                               % len(colist))

        # ok, value is 3rd colist element
        log.adminlevel = int(colist[2])                # set the config option
        log.log("<config>ADMINLEVEL(): adminlevel set to '%d'."
                % (log.adminlevel), 8)


# ADMIN_NOTIFY - how often to send admin-logs to admin
class ADMIN_NOTIFY(ConfigOption):
    def __init__(self, colist, typecolist):
        super(ADMIN_NOTIFY, self).__init__(colist, typecolist)

        # if we don't have 3 or 4 elements ['ADMIN_NOTIFY', '=', <int>, [<char>,]] then raise an error
        if len(colist) < 3 or len(colist) > 4:
            raise ParseFailure("ADMIN_NOTIFY definition has %d tokens when expecting 3 or 4"
                               % len(colist))

        # ok, value is 3rd[+4th] colist element
        if len(colist) == 3:
            rawval = colist[2]
        else:
            rawval = str(colist[2]) + colist[3]

        value = utils.val2secs(rawval)                # convert value to seconds
        if value > 0:
            log.admin_notify = value                # set the config option
        log.log("<config>ADMIN_NOTIFY(): admin_notify set to %s (%d seconds)."
                % (rawval, log.admin_notify), 8)


# INTERPRETERS - define the colist of interpreters
class INTERPRETERS(ConfigOption):
    def __init__(self, colist, typecolist):
        super(INTERPRETERS, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['INTERPRETERS', '=', <str>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("INTERPRETERS definition has %d tokens when expecting 3"
                               % len(colist))

        value = utils.stripquote(colist[2])
        interpreters = value.split(',')

        # The interpreters colist is stored in the proc module for the current system
        # FIXME procobj = directive.data_modules.import_module('proc')
        # FIXME procobj.interpreters = interpreters

        log.log("<config>INTERPRETERS(): interpreters defined as '%s'." %
                (interpreters,), 8)


# CLASS - define a class
class CLASS(ConfigOption):
    def __init__(self, colist, typecolist):

        super(CLASS, self).__init__(colist, typecolist)
        # if we don't have at least 4 elements ['CLASS', <str>, '=', <str>, [',', <str>, ...] ]
        # then raise an error
        if len(colist) < 4:
            raise ParseFailure("CLASS definition has %d tokens when expecting 4"
                               % len(colist))

        self.name = colist[1]
        hosts = colist[3:]                     # pull hosts out
        hosts = ''.join(hosts)                 # join all arguments
        hosts = utils.stripquote(hosts)        # in case the arguments are in quotes (optional)
        self.hosts = hosts.split(',')          # finally, split into colist of hosts

        log.log("<config>CLASS(): class created %s:%s."
                % (self.name, self.hosts), 8)


# NUMTHREADS - limit thread creation
class NUMTHREADS(ConfigOption):
    def __init__(self, colist, typecolist):
        super(NUMTHREADS, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['NUMTHREADS', '=', <int>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("NUMTHREADS definition has %d tokens when expecting 3"
                               % len(colist))

        # ok, value is 3rd colist element
        global num_threads
        try:
            num_threads = int(colist[2])                # set the config option
        except ValueError:                             # must be integer
            raise ParseFailure("NUMTHREADS is not an integer, '%s'"
                               % (colist[2]))

        log.log("<config>NUMTHREADS: num_threads set to '%d'."
                % (num_threads), 8)


class CONSOLE_PORT(ConfigOption):
    """Set the tcp port to listen on for console connections"""

    def __init__(self, colist, typecolist):
        super(CONSOLE_PORT, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['CONSOLE_PORT', '=', <int>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("CONSOLE_PORT definition has %d tokens when expecting 3"
                               % len(colist))

        # ok, value is 3rd colist element
        global consport
        try:
            consport = int(colist[2])                # set the config option
        except ValueError:                        # must be integer
            raise ParseFailure("CONSOLE_PORT is not an integer, '%s'" % (colist[2]))

        if consport < 0:
            raise ParseFailure("CONSOLE_PORT must be a positive integer, %d" % (consport))

        log.log("<config>CONSOLE_PORT: consport set to '%d'." % (consport), 8)


class EMAIL_FROM(ConfigOption):
    """Set the From: address used by the email() action."""
    def __init__(self, colist, typecolist):
        super(EMAIL_FROM, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['EMAIL_FROM', '=', <string>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("EMAIL_FROM definition has %d tokens when expecting 3" %
                               len(colist))
        # set for sendmail function to use
        utils.EMAIL_FROM = utils.stripquote(colist[2])

        log.log("<config>EMAIL_FROM: email From: set to '%s'"
                % (utils.EMAIL_FROM), 8)


class EMAIL_REPLYTO(ConfigOption):
    """Set the From: address used by the email() action."""
    def __init__(self, colist, typecolist):
        super(EMAIL_REPLYTO, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['EMAIL_REPLYTO', '=', <string>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("EMAIL_REPLYTO definition has %d tokens when expecting 3"
                               % len(colist))
        # set for sendmail function to use
        utils.EMAIL_REPLYTO = utils.stripquote(colist[2])

        log.log("<config>EMAIL_REPLYTO: email From: set to '%s'"
                % (utils.EMAIL_REPLYTO), 8)


class SENDMAIL(ConfigOption):
    """Set the location of the sendmail binary."""

    def __init__(self, colist, typecolist):
        super(SENDMAIL, self).__init__(colist, typecolist)

        # if we don't have 3 elements ['SENDMAIL', '=', <string>] then raise an error
        if len(colist) != 3:
            raise ParseFailure("SENDMAIL definition has %d tokens when expecting 3" % len(colist))

        utils.SENDMAIL = utils.stripquote(colist[2])  # set for sendmail function to use
        utils.SENDMAIL_FUNCTION = "sendmail_bin"        # set sendmail binary as default method

        log.log("<config>SENDMAIL: set to '%s'" % (utils.SENDMAIL), 8)


class SMTP_SERVERS(ConfigOption):
    """Set the names of the SMTP servers."""

    def __init__(self, colist, typecolist):
        super(SMTP_SERVERS, self).__init__(colist, typecolist)

        # if we don't have at least 3 elements ['SMTP_SERVERS', '=', <str>, [',', <str>, ...] ]
        # then raise an error
        if len(colist) < 3:
            raise ParseFailure("SMTP_SERVERS definition has %d tokens when expecting at least 3" % len(colist))

        servers = ",".join(colist[2:])
        servers = utils.stripquote(servers)
        servcolist = servers.split(',')
        utils.SMTP_SERVERS = servcolist
        utils.SENDMAIL_FUNCTION = "sendmail_smtp"  # set smtp as default method

        log.log("<config>SMTP_SERVERS: set to %s" % (", ".join(servcolist)), 8)


class WORKDIR(ConfigOption):
    """Set the location of the temporary work directory."""

    def __init__(self, colist, typecolist):
        super(WORKDIR, self).__init__(colist, typecolist)

        self.workdir = None

        # if we don't have 3 elements ['WORKDIR', '=', <str> ]
        # then raise an error
        if len(colist) != 3:
            raise ParseFailure("WORKDIR definition has %d tokens when expecting only 3"
                               % len(colist))
        if colist[1] != '=':
            raise ParseFailure("WORKDIR statement invalid")
        workdir = utils.stripquote(colist[2])

        if os.path.isdir(workdir):
            self.workdir = workdir
        else:
            try:
                os.makedirs(workdir, 0o700)  # create all dirs - access by user only
            except OSError as err:
                log.log("<config>WORKDIR: cannot create '%s', %s"
                        % (workdir, err), 4)
            else:
                self.workdir = workdir
                log.log("<config>WORKDIR: created WORKDIR '%s'" % (workdir), 8)

        # set workdir location in utils module - utils.get_work_dir() is best way
        #  to retrieve this.  This isn't terribly elegant and needs to be re-written
        #  properly.
        utils.WORKDIR = self.workdir
        log.log("<config>WORKDIR: set to '%s'" % (self.workdir), 8)


class RESCANCONFIGS(ConfigOption):
    """Set the boolean indicating desire to constantly check for config file changes and reload."""

    def __init__(self, colist, typecolist):
        apply(ConfigOption.__init__, (self, colist, typecolist))

        # if we don't have 3 elements ['RESCANCONFIGS', '=', <val>] then
        # raise an error
        if len(colist) != 3:
            raise ParseFailure("RESCANCONFIGS definition has %d tokens when expecting 3" % len(colist))

        # ok, value is 3rd colist element
        global rescan_configs
        if str(colist[2]) == '1' or str(colist[2]).lower() == 'true' or str(colist[2]).lower() == 'on':
            rescan_configs = True
        elif str(colist[2]) == '0' or str(colist[2]).lower() == 'false' or str(colist[2]).lower() == 'off':
            rescan_configs = False
        else:
            raise ParseFailure("RESCANCONFIGS must be True [1/True/on] or False [0/False/off]: '%s'" % (colist[2]))

        log.log("<config>RESCANCONFIGS(): rescan_configs set to '%s'."
                % (rescan_configs), 8)


def loadExtraDirectives(directivedir):
    """Load extra directives from given directory.  Each file
    in this directory must be an importable (.py) Python module
    which contain directives (one or more) as classes."""

    import inspect
    oldsyspath = sys.path                        # save sys.path
    sys.path.insert(0, directivedir)        # restrict module path
    extradirectives = os.listdir(directivedir)
    for m in extradirectives:
        if m.endswith(".py") and not m.startswith('_'):
            mname = m[:-3]                          # get module name
            mod = __import__(mname)                 # import module
            mobjs = dir(mod)                        # list of module's objects
            for o in mobjs:                         # Cycle thru module's objects
                d = "mod.%s" % o
                # we only want class objects
                if eval("inspect.isclass(%s)" % d):
                    exec("directives[o] = %s" % (d))  # add to directives dict

    sys.path = oldsyspath                # restore module path

    directives.update(directives)        # add new directives to directives table


# This is a colist of known keywords we accept in Boris config/rules files

# Just the directives:
# These are added dynamically when the program begins.
directives = {}


# Just the definitions:
definitions = {
    "N": definition.N,
    "M": definition.M,
    "MSG": definition.MSG,
    "ALIAS": definition.ALIAS,
}

# Just the settings:
settings = {
    "SCANPERIOD": SCANPERIOD,
    "LOGFILE": LOGFILE,
    "LOGLEVEL": LOGLEVEL,
    "ADMIN": ADMIN,
    "ADMINLEVEL": ADMINLEVEL,
    "ADMIN_NOTIFY": ADMIN_NOTIFY,
    "INTERPRETERS": INTERPRETERS,
    "CLASS": CLASS,
    "NUMTHREADS": NUMTHREADS,
    "CONSOLE_PORT": CONSOLE_PORT,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_REPLYTO": EMAIL_REPLYTO,
    "SENDMAIL": SENDMAIL,
    "SMTP_SERVERS": SMTP_SERVERS,
    "WORKDIR": WORKDIR,
    "RESCANCONFIGS": RESCANCONFIGS,
}

# Join all the above dictionaries to make the total keywords dictionary
keywords = {}
#keywords.update(directives)
keywords.update(definitions)
keywords.update(settings)
