
__doc__ = '''
This is an Boris data collector.  It collects System data and statistics
using os & psutil modules. So it should work across platforms supported by
these modules.

Data collectors provided by this module:
  - system: collects system stats.  See the class doc below for details
    of exactly which statistics are gathered and what they are called in
    the BORIS environment.
'''


# Python modules
import os
import string
from datetime import datetime
from decimal import Decimal
import psutil
from resource import getpagesize
# Boris modules
from boristool._compat import long
from boristool.common import datacollect, log, utils


class system(datacollect.DataCollect):
    """Gathers system statistics.

    The names of all the stats collected by the system class are:

    System stats from psutil
        uptime          - time since last boot (string)
        users           - number of logged on users (int)
    Load avg stats from os.getloadavg()
        loadavg1        - 1 minute load average (float)
        loadavg5        - 5 minute load average (float)
        loadavg15       - 15 minute load average (float)

    System counters like vm_stat' (see vm_stat(1)):
        pages_free                              - (int)
        pages_active                            - (int)
        pages_inactive                          - (int)
        pages_wired_down                        - (int)
        pages_cached                            - (int)
        ctr_pageins                             - (int)
        ctr_pageouts                            - (int)
     todo
        ctr_translation_faults                  - (int)
        ctr_pages_copyonwrite                   - (int)
        ctr_pages_zero_filled                   - (int)
        ctr_pages_reactivated                   - (int)
      extra's
        pages_used                              - (int)
        pages_total                             - (int)
        pages_available                         - (int)
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
        """Get system virtual memory statistics.
        """

        vmstat_dict = {}

        ps = getpagesize()
        vm = psutil.virtual_memory()
        vmstat_dict['pages_free'] = vm.free//ps
        vmstat_dict['pages_used'] = vm.used//ps
        vmstat_dict['pages_total'] = vm.total//ps
        vmstat_dict['pages_available'] = vm.available//ps
        if hasattr(vm, 'active'):
            vmstat_dict['pages_active'] = vm.active//ps
        if hasattr(vm, 'inactive'):
            vmstat_dict['pages_inactive'] = vm.inactive//ps
        if hasattr(vm, 'wired'):
            vmstat_dict['pages_wired_down'] = vm.wired//ps
        if hasattr(vm, 'cached'):
            vmstat_dict['pages_cached'] = vm.cached//ps

        sm = psutil.swap_memory()
        vmstat_dict['ctr_pageins'] = sm.sin//ps
        vmstat_dict['ctr_pageouts'] = sm.sout//ps

        return vmstat_dict

    def _getuptime(self):
        """Get uptime statistics.
        """

        uptime_dict = {}

        loadavg = os.getloadavg()
        # convert types
        uptime_dict['uptime'] = str(datetime.now() - datetime.fromtimestamp(psutil.boot_time()))
        uptime_dict['users'] = len(psutil.users())
        uptime_dict['loadavg1'] = float(Decimal(loadavg[0]).quantize(Decimal('0.01')))
        uptime_dict['loadavg5'] = float(Decimal(loadavg[1]).quantize(Decimal('0.01')))
        uptime_dict['loadavg15'] = float(Decimal(loadavg[2]).quantize(Decimal('0.01')))

        return uptime_dict
