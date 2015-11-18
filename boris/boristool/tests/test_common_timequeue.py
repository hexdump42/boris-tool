import unittest
from . import env
try:
    from queue import Empty
except:
    from Queue import Empty

import boristool.common.timequeue as timequeue


class TimeQueueTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_create(self):
        tq = timequeue.TimeQueue()
        self.assertEqual(tq.maxsize, 0)

    def test_put(self):
        tq = timequeue.TimeQueue(0)
        item = ('a', 0)
        tq.put(item)
        self.assertEqual(tq.head(), item)

    def test_get(self):
        tq = timequeue.TimeQueue(0)
        item = ('a', 0)
        tq.put(item)
        self.assertEqual(tq.get(block=False), item)
        with self.assertRaises(Empty):
            tq.get(block=False)

    def test_head(self):
        tq = timequeue.TimeQueue(0)
        item = ('a', 0)
        tq.put(item)
        self.assertEqual(tq.head(), item)
        # head shouldn't remove item from the Q, so no exception should be raised
        tq.get(block=False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
