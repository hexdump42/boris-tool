
from __future__ import absolute_import

from . import utils
from . import log
from . import action

# Define exceptions
ParseFailure = 'ParseFailure'


class MsgDict(object):
    """The Message dictionary class."""

    def __init__(self):
        self.hash = {}                # Dictionary of M objects keyed by name

    def __add__(self, new):
        """Overload '+', eg: rules + directive_rule"""

        self.hash[new.name] = new        # Add M object to dictionary
        return(self)

    def __setitem__(self, name, new):
        """Overload '[]' for setting."""

        self.hash[name] = new                # Add M object to dictionary
        return(self)

    def __getitem__(self, name):
        """Overload '[]', eg: returns corresponding object for name."""
        try:
            return self.hash[name]
        except KeyError:
            return None

    def __str__(self):
        return "%s" % self.hash

    def keys(self):
        return list(self.hash.keys())

    def delete(self, name):
        del self.hash[name]

    # update this dictionary with adict as per dict.update() method
    def update(self, adict):
        for a in list(adict.keys()):
            self.hash[a] = adict[a]


class Definition:
    """The base definition class.  Derive all definition-types from
       this base class.
    """

    def __init__(self, list, typelist):
        self.basetype = 'Definition'        # the object can know its own basetype
        self.type = list[0]                # the definition type of this instance
        self.hastokenparser = 0                # no tokenparser() function by default


# DEFINITIONS
class MSG(Definition):
    """Message Definition."""

    def __init__(self, toklist, toktypes):
        Definition.__init__(*(self, toklist, toktypes))
        self.name = toklist[1]
        self.subject = None
        self.message = None
        self.hastokenparser = 1
        log.log("<definition>MSG: MSG created, name '%s'" % (self.name), 9)

    def tokenparser(self, toklist, toktypes, indent):

        for argline in toklist:
            for t in argline:
                if self.subject is None:
                    self.subject = utils.stripquote(t)
                elif self.message is None:
                    self.message = utils.stripquote(t)
                else:
                    # tokens left and subject/message already defined
                    raise ParseFailure("Parse error during MSG definition")

        log.log("<definition>MSG.tokenparser(): MSG parsed, subject:'%s' message:'%s'" %
                (self.subject, self.message), 8)

    def __str__(self):
        str = "<MSG %s>" % (self.name)
        return str


class M(Definition):
    """Message-list Definition."""

    def __init__(self, toklist, toktypes):
        Definition.__init__(*(self, toklist, toktypes))
        self.name = toklist[1]
        self.MDict = {}                        # Create dict of M's or MSG's
        log.log("<definition>M: M created, name '%s'" % (self.name), 8)

    def __str__(self):
        str = "<M %s:" % self.name
        for i in list(self.MDict.keys()):
            str = str + " %s" % self.MDict[i]
        str = str + ">"
        return str

    def __getitem__(self, item):
        return self.MDict[item]

    def give(self, obj):
        if obj.type == 'M':
            self.MDict[obj.name] = obj
        elif obj.type == 'MSG':
            self.MDict[obj.name] = obj
        else:
            raise SyntaxError("M can't take object of type %s" % obj.type)


class ALIAS(Definition):
    """ALIAS Definition - defines a variable which can appear anywhere
       in the config or as arguments to action calls, etc. eg:
        ALIAS ALERT_EMAIL='root'
        FS: fs='/' rule="capac>=90%" action="email(ALERT_EMAIL, 'fs nearly full')"

       or
        ALIAS FSRULE="capac>=90%"
        FS: fs='/' rule=FSRULE action=" ... "
    """

    def __init__(self, list, toktypes):
        Definition.__init__(*(self, list, toktypes))

        # if we don't have 4 elements ['ALIAS', <str>, '=', <value>] then
        # raise an error
        if len(list) != 4:
            raise ParseFailure("ALIAS definition has %d tokens when expecting 4" %
                               len(list))

        # OK, grab values
        self.name = list[1]                        # the name of this ALIAS
        self.value = list[3]                        # the value assigned to it
        # convert value to int, float or string without quotes, if necessary.
        if toktypes[3] == 'NUMBER':
            if string.find(self.value, '.') == -1:
                self.value = int(self.value)                # integer
            else:
                self.value = float(self.value)                # float
        elif toktypes[3] == 'STRING':
            self.value = utils.stripquote(self.value)        # the text that is assigned to it
        log.log("<definition>ALIAS: ALIAS created: %s=%s" %
                (self.name,self.value), 8)


class N(Definition):
    """
    N Definition - defines Notification configs.
    """

    defs={
        'notifyperiod': 'TIME',
        'escalperiod': 'TIME'
         }

    def __init__(self, list, toktypes):
        Definition.__init__(*(self,list, toktypes))

        # Need at least 3 tokens
        if len(list) < 3:
            raise ParseFailure("Not enough tokens for N definition")

        # 3rd token should be a ':'
        if list[2] != ':':
            raise ParseFailure("N definition missing ':'")

        # tokens are ok
        self.name = list[1]                # the name of this object
        self.lastNotify = 0                # time of last notify
        self.escalLevel = 0                # current level of escalation
        self.levels = {}                     # dict of notification levels

        # used during config parsing
        self.configLevel = -1
        self.configIndent = 0

        self.hastokenparser = 1

        # Get pointers to all the action functions
        self.actionFuncs = {}
        for a in dir(action.action):
            if a[0] != '_':
                exec("self.actionFuncs[a] = action.action.%s" % (a))

        log.log("<definition>N: N created, name '%s'" % (self.name), 9)

    def __str__(self):
        str = "<N name='%s' " % (self.name)
        for l in list(self.levels.keys()):
            str = str + " Level=%s:%s" % (l, self.levels[l])
        str = str + ">"
        return str

    def tokenparser(self, toklist, toktypes, indent):

        for argline in toklist:

            if argline[0] in ('Level', 'level', 'LEVEL'):
                if argline[2] != ':':
                    raise ParseFailure

                level = argline[1]
                self.addLevel(argline[1])        # Create level
                self.configLevel = argline[1]

            elif argline[0] in list(self.defs.keys()):
                # One of the defined assignments

                if argline[1] != '=':
                    raise ParseFailure('Expecting "=" after "%s", got "%s' % (argline[0], argline[1]))

                # assume number followed by letter at the moment...
                value = utils.stripquote(argline[2])
                if self.defs[argline[0]] == 'TIME':
                    # Convert time to seconds if required
                    value = utils.val2secs(value)

                assignment = 'self.%s=%d' % (argline[0],value)
                exec(assignment)

            else:
                # Must be a notification command (or list of commands)
                notiflist = self.getNotifList(argline)
                if len(notiflist) == 0:
                    raise ParseFailure("Notification list is empty")
                else:
                    if self.configLevel == -1:
                        # Error if no levels defined yet
                        raise ParseFailure("No notification levels have been defined yet")
                    self.addNotif(self.configLevel,indent,notiflist)

        # Need reference to M objects
        self.MDict = self.parent.MDict

        # Finished parsing tokens
        log.log("<definition>N.tokenparser(): '%s'" % (self), 8)

    # Create a notification level - error if level already exists
    def addLevel(self, level):
        if level in list(self.levels.keys()):
            raise ParseFailure("a: level %s already defined" % level)

        # Create notification level in levels dict
        self.levels[level] = []

    # Try and create a notification command list from tokens and return this
    # list.
    def getNotifList(self, list):
        nlist = []                # list of notification commands
        nstr = ''                # current notification command as string
        brackets = 0                # track brackets depth
        self.delcnt = 0                # temporary counter so main loop can delete objects from list

        for t in list:
            if t == 'Level':        # stop if new Level defn - poor code!
                break

            if t == '(':
                brackets = brackets + 1
            if t == ')':
                brackets = brackets - 1
                if brackets < 0:
                    raise ParseFailure("Too many close parentheses ')'")

            nstr = nstr + t

            self.delcnt = self.delcnt + 1

        if brackets != 0:
            raise ParseFailure("Parentheses not closed")

        if len(nstr) > 0:
                nlist.append(nstr)

        return nlist

    def addNotif(self, configLevel, indent, list):
        if len(self.levels[configLevel]) == 0:
            self.levels[configLevel] = list
            self.configIndent = indent
        else:
            depth = indent - self.configIndent
            if depth == 0:
                a = self.levels[configLevel]
                while type(a[-1]) == type([]):
                    a = a[-1]
                for l in list:
                    a.append(l)
            elif depth > 0:
                a = self.levels[configLevel]
                while type(a[-1]) == type([]):
                    a = a[-1]
                a.append(list)
            elif depth < 0:
                a = self.levels[configLevel]
                tmp = []                # temporary stack
                while type(a[-1]) == type([]):
                    tmp.append(a)
                    a = a[-1]
                a = tmp[depth]
                for l in list:
                    a.append(l)
            self.configIndent = indent

    def doAction(self, msg, level=0):
        """
        Execute the actions from the given level.
        """

        try:
            # TODO: level should be int (but isn't ...)
            actions = self.levels[str(level)]
        except KeyError:
            log.log("<definition>N.doAction(): error, invalid level %d" %
                    (level), 4)
            return None

        for acall in actions:
            evalenv = {}
            evalenv.update(self.actionFuncs)        # add action functions
            try:
                ret = eval(acall, {"__builtins__": {}}, evalenv)          # Call the Action
            except:
                # Handle any action evaluation exceptions neatly
                import sys, traceback
                e = sys.exc_info()
                tb = traceback.format_list(traceback.extract_tb(e[2]))
                log.log("<directive>N.doAction(): Error evaluating %s: %s, %s, %s" %
                        (acall, e[0], e[1], tb), 5)
                return None


def parseM(text, dict):
    """parseM(text, dict) - if text is in dict (assumed to be of type MsgDict)
       then (subj,body) list is returned, else empty list is returned.
    """

    try:
        # is text a key in dict ?
        body = dict[text]
    except KeyError:
        # if no, return empty list
        return ()
    if body is None:
        # not in dictionary, return empty list
        return ()
    return (dict.subj(text), body)
