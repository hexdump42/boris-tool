import unittest
try:
    from unittest.mock import MagicMock, patch
except:
    from mock import MagicMock, patch
from . import env

import boristool.common.log as log
import boristool.common.utils as utils


def mock_adafruit_dht(cls):
    cls.adafruit_dht_mock = MagicMock()
    cls.adafruit_dht_mock.read_retry = read_retry
    modules = {
        'Adafruit_DHT': cls.adafruit_dht_mock
    }
    cls.module_patcher = patch.dict('sys.modules', modules)
    cls.module_patcher.start()
    

def read_retry(sensortype, pin):
    return (65.8, 24.5)


class DHTDataTest(unittest.TestCase):

    def setUp(self):
        mock_adafruit_dht(self)
        #self.adafruit_dht_mock = MagicMock()
        #self.adafruit_dht_mock.read_retry = read_retry
        #modules = {
        #    'Adafruit_DHT': self.adafruit_dht_mock
        #}
        #self.module_patcher = patch.dict('sys.modules', modules)
        #self.module_patcher.start()

    def tearDown(self):
        self.module_patcher.stop()

    def test_collectdata(self):
        from boristool.arch.Linux.rpi import DHTData
        dhtdata = DHTData()
        dhtdata.data = MagicMock()
        dhtdata.data.datahash = {}
        dhtdata.defaultVarDict = {}
        dhtdata.defaultVarDict['sensortype'] = '2302'
        dhtdata.defaultVarDict['gpiopin'] = '4'
        dhtdata.collectData()
        self.assertEqual(dhtdata.data.datahash['DHT-4'].data['humidity'], 65.8)
        self.assertEqual(dhtdata.data.datahash['DHT-4'].data['temperature'], 24.5)


class DHT(unittest.TestCase):

    def setUp(self):
        mock_adafruit_dht(self)

    def tearDown(self):
        self.module_patcher.stop()

    def test_create(self):
        from boristool.arch.Linux.rpi import DHT
        dht = DHT('dht')
        self.assertEqual(dht.name, 'dht')
        self.assertEqual(dht.data, {})
