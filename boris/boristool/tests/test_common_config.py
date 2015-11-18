import unittest
from . import env

import boristool.common.config as config
import boristool.common.config
import boristool.common.log as log
import boristool.common.utils as utils


class ConfigOptionTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_scanperiod(self):
        colist = ['SCANPERIOD', '=', '1h']
        typecolist = 'SCANPERIOD'
        co = config.SCANPERIOD(colist, typecolist)
        self.assertEqual(boristool.common.config.scanperiodraw, '1h')
        # 1h is converted to 60 *60
        self.assertEqual(boristool.common.config.scanperiod, 60 * 60)
        # colist can have 3  or 4 elements
        colist = ['SCANPERIOD', '=', 1, 'h']
        co = config.ADMIN_NOTIFY(colist, typecolist)
        self.assertEqual(boristool.common.config.scanperiodraw, '1h')
        self.assertEqual(boristool.common.config.scanperiod, 60 * 60)
        with self.assertRaises(config.ParseFailure):
            colist = ['SCANPERIOD', '=', 1, "m", "dummy"]
            co = config.SCANPERIOD(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['SCANPERIOD', '1m']
            co = config.SCANPERIOD(colist, typecolist)

    def test_logfile(self):
        colist = ['LOGFILE', '=', '"/var/log/boris.log"']
        co = config.LOGFILE(colist, 'LOGFILE')
        self.assertEqual(log.logfile, '/var/log/boris.log')
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['LOGFILE', '=', '"/var/log/boris.log"', "dummy"]
            co = config.LOGFILE(colist, 'LOGFILE')
        with self.assertRaises(config.ParseFailure):
            colist = ['LOGFILE', '"/var/log/boris.log"']
            co = config.LOGFILE(colist, 'LOGFILE')

    def test_loglevel(self):
        colist = ['LOGLEVEL', '=', 5]
        typecolist = 'LOGLEVEL'
        co = config.LOGLEVEL(colist, typecolist)
        self.assertEqual(log.loglevel, 5)
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['LOGLEVEL', '=', 5, "dummy"]
            co = config.LOGLEVEL(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['LOGLEVEL', 5]
            co = config.LOGLEVEL(colist, typecolist)
        # loglevel must be in range 0 - 9
        with self.assertRaises(config.ParseFailure):
            colist = ['LOGLEVEL', -1]
            co = config.LOGLEVEL(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['LOGLEVEL', 10]
            co = config.LOGLEVEL(colist, typecolist)

    def test_admin(self):
        colist = ['ADMIN', '=', 'boris@nospam.com']
        typecolist = 'ADMIN'
        co = config.ADMIN(colist, typecolist)
        self.assertEqual(log.adminemail, 'boris@nospam.com')
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['ADMIN', '=', 'boris@nospam.com', "dummy"]
            co = config.ADMIN(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['ADMIN', 'boris@nospam.com']
            co = config.ADMIN(colist, typecolist)

    def test_adminlevel(self):
        colist = ['ADMINLEVEL', '=', 3]
        typecolist = 'ADMINLEVEL'
        co = config.ADMINLEVEL(colist, typecolist)
        self.assertEqual(log.adminlevel, 3)
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['ADMINLEVEL', '=', 3, "dummy"]
            co = config.ADMINLEVEL(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['ADMINLEVEL', 3]
            co = config.ADMINLEVEL(colist, typecolist)

    def test_admin_notify(self):
        colist = ['ADMIN_NOTIFY', '=', '1m']
        typecolist = 'ADMIN_NOTIFY'
        co = config.ADMIN_NOTIFY(colist, typecolist)
        # 1m is converted to 60s
        self.assertEqual(log.admin_notify, 60)
        # colist can have 3  or 4 elements
        colist = ['ADMIN_NOTIFY', '=', 1, 'm']
        co = config.ADMIN_NOTIFY(colist, typecolist)
        self.assertEqual(log.admin_notify, 60)
        with self.assertRaises(config.ParseFailure):
            colist = ['ADMIN_NOTIFY', '=', 1, "m", "dummy"]
            co = config.ADMIN_NOTIFY(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['ADMIN_NOTIFY', '1m']
            co = config.ADMIN_NOTIFY(colist, typecolist)

    def test_interpreters(self):
        colist = ['INTERPRETERS', '=', "'sh,bash,perl,python'"]
        typecolist = 'INTERPRETERS'
        co = config.INTERPRETERS(colist, typecolist)

    def test_class(self):
        colist = ['CLASS', 'linux', '=', "host1"]
        typecolist = 'CLASS'
        co = config.CLASS(colist, typecolist)
        self.assertEqual(co.name, 'linux')
        self.assertEqual(co.hosts, ['host1'])
        # a CLASS can have multiple hosts
        colist = ['CLASS', 'linux', '=', "host1,host2"]
        typecolist = 'CLASS'
        co = config.CLASS(colist, typecolist)
        self.assertEqual(co.name, 'linux')
        self.assertEqual(co.hosts, ['host1', 'host2'])
        # There must be at least 4 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['CLASS', 'linux', '=']
            co = config.CLASS(colist, typecolist)

    def test_numthreads(self):
        colist = ['NUMTHREADS', '=', 7]
        typecolist = 'NUMTHREADS'
        co = config.NUMTHREADS(colist, typecolist)
        self.assertEqual(boristool.common.config.num_threads, 7)
        # num of threads setting must be integer
        with self.assertRaises(config.ParseFailure):
            colist = ['NUMTHREADS', '=', 'X']
            co = config.NUMTHREADS(colist, typecolist)
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['NUMTHREADS', '=', '7', 'X']
            co = config.NUMTHREADS(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['NUMTHREADS', '=']
            co = config.NUMTHREADS(colist, typecolist)

    def test_console_port(self):
        colist = ['CONSOLE_PORT', '=', 5678]
        typecolist = 'CONSOLE_PORT'
        co = config.CONSOLE_PORT(colist, typecolist)
        self.assertEqual(boristool.common.config.consport, 5678)
        # num of threads setting must be postive integer
        with self.assertRaises(config.ParseFailure):
            colist = ['CONSOLE_PORT', '=', -1]
            co = config.CONSOLE_PORT(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['CONSOLE_PORT', '=', 'X']
            co = config.CONSOLE_PORT(colist, typecolist)
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['CONSOLE_PORT', '=', 5678, 'X']
            co = config.CONSOLE_PORT(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['CONSOLE_PORT', '=']
            co = config.CONSOLE_PORT(colist, typecolist)

    def test_email_from(self):
        colist = ['EMAIL_FROM', '=', 'boris@nospam.com']
        typecolist = 'EMAIL_FROM'
        co = config.EMAIL_FROM(colist, typecolist)
        self.assertEqual(utils.EMAIL_FROM, 'boris@nospam.com')
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['EMAIL_FROM', '=', 'boris@nospam.com', 'X']
            co = config.EMAIL_FROM(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['EMAIL_FROM', '=']
            co = config.EMAIL_FROM(colist, typecolist)

    def test_email_replyto(self):
        colist = ['EMAIL_REPLYTO', '=', 'boris@nospam.com']
        typecolist = 'EMAIL_REPLYTO'
        co = config.EMAIL_REPLYTO(colist, typecolist)
        self.assertEqual(utils.EMAIL_REPLYTO, 'boris@nospam.com')
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['EMAIL_REPLYTO', '=', 'boris@nospam.com', 'X']
            co = config.EMAIL_REPLYTO(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['EMAIL_REPLYTO', '=']
            co = config.EMAIL_REPLYTO(colist, typecolist)

    def test_sendmail(self):
        colist = ['SENDMAIL', '=', '/bin/sendmailer']
        typecolist = 'SENDMAIL'
        co = config.SENDMAIL(colist, typecolist)
        self.assertEqual(utils.SENDMAIL, '/bin/sendmailer')
        self.assertEqual(utils.SENDMAIL_FUNCTION, 'sendmail_bin')
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['SENDMAIL', '=', '/bin/sendmailer', 'X']
            co = config.SENDMAIL(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['SENDMAIL', '=']
            co = config.SENDMAIL(colist, typecolist)

    def test_smtp_servers(self):
        colist = ['SMTP_SERVERS', '=', 'mail.nospam.com']
        typecolist = 'SMTP_SERVERS'
        co = config.SMTP_SERVERS(colist, typecolist)
        self.assertEqual(utils.SMTP_SERVERS, ['mail.nospam.com'])
        self.assertEqual(utils.SENDMAIL_FUNCTION, 'sendmail_smtp')
        # multiple smtp servers in a comma sep list
        colist = ['SMTP_SERVERS', '=', 'mail.nospam.com,mail.boris.com']
        co = config.SMTP_SERVERS(colist, typecolist)
        self.assertEqual(utils.SMTP_SERVERS, ['mail.nospam.com','mail.boris.com'])
        self.assertEqual(utils.SENDMAIL_FUNCTION, 'sendmail_smtp')
        # colist must have 3+ elements
        with self.assertRaises(config.ParseFailure):
            colist = ['SMTP_SERVERS', '=']
            co = config.SMTP_SERVERS(colist, typecolist)

    def test_workdir(self):
        workdir = '/tmp/test_boris_workdir'
        colist = ['WORKDIR', '=', workdir]
        typecolist = 'WORKDIR'
        co = config.WORKDIR(colist, typecolist)
        self.assertEqual(co.workdir, workdir)
        self.assertEqual(utils.WORKDIR, workdir)
        # colist must only have 3 elements
        with self.assertRaises(config.ParseFailure):
            colist = ['WORKDIR', '=', workdir, 'X']
            co = config.WORKDIR(colist, typecolist)
        with self.assertRaises(config.ParseFailure):
            colist = ['WORKDIR', '=']
            co = config.WORKDIR(colist, typecolist)
        # TODO Remove test workdir created

if __name__ == '__main__':
    unittest.main()
