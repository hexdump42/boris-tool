
__doc__ = """This is Boris data collector that collects RPi sensor
data.

Currently only the Adafruit & duinotech DHT temperature sensor modules
are supported.

Limitations: currently hardcoded to sensor type 2302 on GPIO pin 4.
"""

from boristool.common import datacollect, log, utils
import Adafruit_DHT

SENSORTYPES = {'11': Adafruit_DHT.DHT11,
               '22': Adafruit_DHT.DHT22,
               '2302': Adafruit_DHT.AM2302}


class DHTData(datacollect.DataCollect):
        """Collects temperature & humidity data using the
        Adafruit_DHT library
        https://github.com/adafruit/Adafruit_Python_DHT"""

        def __init__(self):
            super(DHTData, self).__init__()

        def collectData(self):
            self.data.datahash = {}
            sensortype = SENSORTYPES['2302']
            pin = '4'
            humidity, temperature = Adafruit_DHT.read_retry(sensortype, pin)
            if humidity is not None and temperature is not None:
                sensorid = 'DHT-4'
                sensor = DHT(sensorid)
                self.data.datahash[sensorid] = sensor
                sensor.set_data('humidity', humidity)
                sensor.set_data('temperature', temperature)

            log.log("<dhtsensor>DHTData.collectData(): Collected data")


class DHT:
    """Holds information about temperature & humidity sensor.
    """

    def __init__(self, name):

        self.name = name
        self.data = {}

    def set_data(self, key, value):
        """Set a data named key to value."""

        self.data[key] = value

    def getHash(self):
        """Returns a dictionary of all the data for this sensor."""

        return self.data.copy()
