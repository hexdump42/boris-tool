__doc__ = """Disk directives"""

from boristool.common import directive, log, utils


class DISK(directive.Directive):
    """DISK provides access to data & stats for disk devices.

    It requires the 'DiskStatistics' class from the 'diskdevice' data-collection module.

    Example:

        # /dev/disk0
        DISK disk0_thruput:
            device='disk0'
            scanperiod='5m'
            rule='True'        # always perform action
            action=notify('BORIS Disk Thruput', '%(device)s rbytes=%(read_bytes)s wbytes=%(write_bytes)s')
    """

    def __init__(self, toklist):
        self.need_collectors = (('diskdevice', 'DiskStatistics'),)
        super(DISK, self).__init__(toklist)

    def tokenparser(self, toklist, toktypes, indent):
        """Parse directive arguments."""
        super(DISK, self).tokenparser(toklist, toktypes, indent)

        try:
            self.args.device
        except AttributeError:
            raise directive.ParseFailure('Device not specified')
        try:
            self.args.rule
        except AttributeError:
            raise directive.ParseFailure('Rule not specified')

        self.defaultVarDict['device'] = self.args.device
        self.defaultVarDict['rule'] = self.args.rule

        # define unique ID
        if self.ID is None:
            self.ID = '%s.DISK.%s' % (log.hostname, self.args.device)
        self.state.ID = self.ID

        log.log("<disk>DISK.tokenparser(): ID '%s' device '%s' rule '%s'" %
                (self.state.ID, self.args.device, self.args.rule), 8)

    def getData(self):
        """Called by Directive docheck() method to fetch the data required for
        evaluating the directive rule.
        """

        disk = self.data_collectors['diskdevice.DiskStatistics'][self.args.device]
        if disk is None:
            log.log("<disk>DISK.docheck(): Error, device not found '%s'" %
                    (self.args.device), 4)
            return None
        else:
            return disk.getHash()