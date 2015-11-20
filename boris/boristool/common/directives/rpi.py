__doc__ = """Raspberry Pi sensor directives"""

from boristool.common import directive, log, utils


class RPI(directive.Directive):
    """RPI provides access to sensors connected to a raspberry pi.

    It requires the 'DHTData' class from the 'rpi' data-collection module.

    Example:

        RPI temp_rpi:
            sensor='DHT'
            sensortype='2302'
            gpiopin='4'
            scanperiod='1m'
            rule='True'        # always perform action
            action=spreadrrd('sensor-%(h)s', 'temperature=%(temperature)s,humidity=%(humidity)s')
    """

    def __init__(self, toklist):
        self.need_collectors = (('rpi', 'DHTData'),)
        super(RPI, self).__init__(toklist)

    def tokenparser(self, toklist, toktypes, indent):
        """Parse directive arguments."""
        super(RPI, self).tokenparser(toklist, toktypes, indent)

        try:
            self.args.sensor
        except AttributeError:
            raise directive.ParseFailure('Sensor not specified')
        try:
            self.args.sensortype
        except AttributeError:
            raise directive.ParseFailure('Sensor type not specified')
        if self.args.sensor == 'DHT':
            try:
                self.args.gpiopin
                self.defaultVarDict['gpiopin'] = self.args.sensor
            except AttributeError:
                raise directive.ParseFailure('GPIO pin not specified')
        try:
            self.args.rule
        except AttributeError:
            raise directive.ParseFailure('Rule not specified')

        self.defaultVarDict['sensor'] = self.args.sensor
        self.defaultVarDict['sensortype'] = self.args.sensortype
        self.defaultVarDict['rule'] = self.args.rule

        # define unique ID
        if self.ID is None:
            self.ID = '%s.RPI.%s' % (log.hostname, self.args.sensor)
        self.state.ID = self.ID

        log.log("<disk>RPI.tokenparser(): ID '%s' sensor '%s' rule '%s'" %
                (self.state.ID, self.args.sensor, self.args.rule), 8)

    def getData(self):
        """Called by Directive docheck() method to fetch the data required for
        evaluating the directive rule.
        """

        sensorid = "%s-%s" % (self.args.sensor, self.args.gpiopin)
        sensor = self.data_collectors['rpi.DHTData'][sensorid]
        if sensor is None:
            log.log("<sensor>RPI.docheck(): Error, sensor not found '%s'" %
                    (sensorid), 4)
            return None
        else:
            return sensor.getHash()
