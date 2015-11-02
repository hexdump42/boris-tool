
__doc__ = """This is Boris data collector that collects disk usage
statistics with the psutil library.
"""

from boristool.common import datacollect, log, utils
from psutil import disk_io_counters


class DiskStatistics(datacollect.DataCollect):
        """Collects disk statistics using psutil.disk_io_counters()"""

        def __init__(self):
            super(DiskStatistics, self).__init__()

        def collectData(self):
            self.data.datahash = {}
            self.data.numdisks = 0

            disk_stats = disk_io_counters(True)
            for name in disk_stats:
                try:
                    # do we have an existing disk object
                    disk = self.data.datahash[name]
                except KeyError:
                    # create new Disk object if needed
                    disk = Disk(name)
                    self.data.datahash[name] = disk
                self.data.numdisks += 1

                for attrname in ['read_count', 'write_count',
                                 'read_bytes', 'write_bytes',
                                 'read_time', 'write_time']:
                    disk.set_stat(attrname, getattr(disk_stats[name], attrname))

            log.log("<diskdevice>DiskStatistics.collectData(): Collected stats for %d disks" %
                    (self.data.numdisks), 6)


class Disk:
    """Holds information about a raw disk.
    A raw disk could actually be an ODS metadevice or some other logical
    volume or RAID array (or even tape device).
    """

    def __init__(self, name):

        self.name = name                # eg, "sd100" or "disk0"
        self.stats = {}

    def set_stat(self, key, value):
        """Set a statistic named key to value."""

        self.stats[key] = int(value)

    def getHash(self):
        """Returns a dictionary of all the stats for this disk."""

        return self.stats.copy()
