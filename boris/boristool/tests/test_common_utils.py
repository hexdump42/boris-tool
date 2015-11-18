import unittest
from . import env

import boristool.common.log as log
import boristool.common.utils as utils


class ParseVarsTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_single_var_str_sub(self):
        d = {}
        d["z"] = "some string"
        self.assertEqual(utils.parse_vars("%(z)s", d), 'some string')

    def test_var_in_var_str_sub(self):
        d = {}
        d["x"] = "some string"
        d["y"] = "x is '%(x)s'"
        d["z"] = "y is '%(y)s'"
        self.assertEqual(utils.parse_vars("%(z)s", d),
                         "y is 'x is 'some string''")

    def test_single_var_str_format_sub(self):
        d = {}
        d['rbytes'] = 100000
        self.assertEqual(utils.parse_vars("rbytes={rbytes:fmt.bc}", d), "rbytes=97.7 K")

    def test_mix_str_and_format_sub(self):
        d = {}
        d['device'] = 'disk0'
        d['rbytes'] = 100000
        d['wbytes'] = 200000
        self.assertEqual(utils.parse_vars("{device} rbytes={rbytes:fmt.bc}, wbytes=%(wbytes)s", d), "disk0 rbytes=97.7 K, wbytes=200000")


class ByteConvertorTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_convert_to_B(self, ):
        self.assertEqual(utils.byte_convertor(100), '100.0 B')

    def test_convert_to_K(self, ):
        self.assertEqual(utils.byte_convertor(10000), '9.8 K')

    def test_convert_to_M(self, ):
        self.assertEqual(utils.byte_convertor(10000000), '9.5 M')

    def test_convert_to_G(self, ):
        self.assertEqual(utils.byte_convertor(10000000000), '9.3 G')

    def test_convert_to_T(self, ):
        self.assertEqual(utils.byte_convertor(10000000000000), '9.1 T')

    def test_convert_to_P(self, ):
        self.assertEqual(utils.byte_convertor(10000000000000000), '8.9 P')

    def test_convert_to_E(self, ):
        self.assertEqual(utils.byte_convertor(10000000000000000000), '8.7 E')

    def test_convert_to_Z(self, ):
        self.assertEqual(utils.byte_convertor(10000000000000000000000), '8.5 Z')

    def test_convert_to_Y(self, ):
        self.assertEqual(utils.byte_convertor(10000000000000000000000000), '8.3 Y')


class FormatWithCommasTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_no_commas(self):
        self.assertEqual(utils.format_with_commas(100), '100')

    def test_with_commas_100K(self):
        self.assertEqual(utils.format_with_commas(100000), '100,000')

    def test_with_commas_100M(self):
        self.assertEqual(utils.format_with_commas(100000000), '100,000,000')
