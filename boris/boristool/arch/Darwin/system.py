
__doc__ = '''
This is an Boris data collector.  It collects System data and statistics
on a Darwin system.

Data collectors provided by this module:
  - system: collects system stats.  See the class doc below for details
    of exactly which statistics are gathered and what they are called in
    the BORIS environment.
'''


# Python modules
import string
import re
# Boris modules
from boristool._compat import long
from boristool.common import datacollect, log, utils


class system(datacollect.DataCollect):
    """Gathers system statistics.

    Calls the following external commands to get stats from:
    /usr/bin/vm_stat: standard with OS X/Darwin 7.3.0
    /usr/bin/uptime: standard with OS X/Darwin 7.3.0

    The names of all the stats collected by the system class are:

    System stats from '/usr/bin/uptime':
        uptime          - time since last boot (string)
        users           - number of logged on users (int)
        loadavg1        - 1 minute load average (float)
        loadavg5        - 5 minute load average (float)
        loadavg15       - 15 minute load average (float)

    System counters from '/usr/bin/vm_stat' (see vm_stat(1)):
        pages_free                              - (long)
        pages_active                            - (long)
        pages_inactive                          - (long)
        pages_wired_down                        - (long)
        ctr_translation_faults                  - (long)
        ctr_pages_copyonwrite                   - (long)
        ctr_pages_zero_filled                   - (long)
        ctr_pages_reactivated                   - (long)
        ctr_pageins                             - (long)
        ctr_pageouts                            - (long)
    """

    def __init__(self):
        super(system, self).__init__()

    ##################################################################
    # Public, thread-safe, methods

    # none special to this class
    ##################################################################
    # Private methods.  No thread safety if not using public methods.

    def collectData(self):
        """Collect system statistics data.
        """

        self.data.datahash = {}                # dict of system data

        vmstat_dict = self._getvmstat()
        if vmstat_dict:
            self.data.datahash.update(vmstat_dict)

        uptime_dict = self._getuptime()
        if uptime_dict:
            self.data.datahash.update(uptime_dict)

        log.log("<system>system.collectData(): collected data for %d system statistics" %
                (len(self.data.datahash.keys())), 6)

    def _getvmstat(self):
        """Get system virtual memory statistics from the 'vm_stat' command.
        """

        vmstat_cmd = "/usr/bin/vm_stat"

        (retval, output) = utils.safe_getstatusoutput(vmstat_cmd)

        if retval != 0:
            log.log("<system>system._getvmstat(): error calling '%s'"%(vmstat_cmd), 5)
            return None

        vmstat_dict = {}

        for l in output.split('\n'):
            if l.find('Pages free:') != -1:
                vmstat_dict['pages_free'] = long(l.split()[-1][:-1])
            elif l.find('Pages active:') != -1:
                vmstat_dict['pages_active'] = long(l.split()[-1][:-1])
            elif l.find('Pages inactive:') != -1:
                vmstat_dict['pages_inactive'] = long(l.split()[-1][:-1])
            elif l.find('Pages wired down:') != -1:
                vmstat_dict['pages_wired_down'] = long(l.split()[-1][:-1])
            elif l.find('Translation faults') != -1:
                vmstat_dict['ctr_translation_faults'] = long(l.split()[-1][:-1])
            elif l.find('Pages copy-on-write:') != -1:
                vmstat_dict['ctr_pages_copyonwrite'] = long(l.split()[-1][:-1])
            elif l.find('Pages zero filled:') != -1:
                vmstat_dict['ctr_pages_zero_filled'] = long(l.split()[-1][:-1])
            elif l.find('Pages reactivated:') != -1:
                vmstat_dict['ctr_pages_reactivated'] = long(l.split()[-1][:-1])
            elif l.find('Pageins:') != -1:
                vmstat_dict['ctr_pageins'] = long(l.split()[-1][:-1])
            elif l.find('Pageouts:') != -1:
                vmstat_dict['ctr_pageouts'] = long(l.split()[-1][:-1])

        return vmstat_dict

    def _getuptime(self):
        """Get system statistics from the output of the 'uptime' command.
        """

        uptime_cmd = "/usr/bin/uptime"

        (retval, output) = utils.safe_getstatusoutput(uptime_cmd)

        if retval != 0:
            log.log("<system>system._getuptime(): error calling '%s'"%(uptime_cmd), 5)
            return None

        uptime_dict = {}

        uptime_re = ".+up (?P<uptime>.+), (?P<users>[0-9]+) users?, load averages: (?P<loadavg1>[0-9.]+) (?P<loadavg5>[0-9.]+) (?P<loadavg15>[0-9.]+)"
        inx = re.compile(uptime_re)
        sre = inx.search(output)
        if sre:
            uptime_dict = sre.groupdict()
        else:
            log.log("<system>system._getuptime(): could not parse uptime output '%s'" % (output), 5)
            return None

        # convert types
        uptime_dict['uptime'] = uptime_dict['uptime']
        uptime_dict['users'] = int(uptime_dict['users'])
        uptime_dict['loadavg1'] = float(uptime_dict['loadavg1'])
        uptime_dict['loadavg5'] = float(uptime_dict['loadavg5'])
        uptime_dict['loadavg15'] = float(uptime_dict['loadavg15'])

        return uptime_dict
