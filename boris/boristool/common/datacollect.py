
from __future__ import absolute_import

import time
import threading

from . import log


# Exceptions
class IndexError(Exception):
    """IndexError: a Data History index is out of range
    """
    pass


class DataFailure(Exception):
    """DataError: a problem occurred while trying to collect the data,
    (ie, while calling module.collectData()) which prevents this
    collector from continuing.
    """
    pass


class DataModuleError(Exception):
    pass


# Data collection management classes
class DataModules(object):
    """This class keeps track of which data collection modules are required
    (directives request data collection modules as they are created);
    makes sure appropriate modules are available;
    and creates data collection objects as required.
    """

    def __init__(self, osname, osver, osarch):
        bad_chars = ('.', '-')
        for c in bad_chars:
            osname = osname.replace(c, '_')
            osver = osver.replace(c, '_')
            osarch = osarch.replace(c, '_')

        osver = 'v' + osver         # can't start with digit

        self.osname = osname
        self.osver = osver
        self.osarch = osarch

        # most specific to least specific
        self.os_search_path = []
        if osname and osver and osarch:
            self.os_search_path.append('.'.join([osname, osver, osarch]))
            self.os_search_path.append('.'.join([osname, osarch, osver]))
        if osname and osver:
            self.os_search_path.append('.'.join([osname, osver]))
        if osname and osarch:
            self.os_search_path.append('.'.join([osname, osarch]))
        if osname:
            self.os_search_path.append(osname)

        self.collectors = {}                # dictionary of collectors and their associated objects

    def import_module(self, module):
        """Return a reference to the imported module, or none if the
        import failed.
        """
        modobj = None

        # first look for platform specific data collect module
        for ospath in self.os_search_path:
            try:
                modparent = __import__(
                    '.'.join(['boristool', 'arch', ospath]),
                    globals(),
                    locals(),
                    [module],
                )
                modobj = getattr(modparent, module)
                break
            except AttributeError:
                pass
            except ImportError:
                pass

        if modobj is None:
            # No platform specific module, look for generic module
            try:
                modparent = __import__(
                    '.'.join(['boristool', 'arch', 'generic']),
                    globals(),
                    locals(),
                    [module],
                )
                modobj = getattr(modparent, module)
            except AttributeError:
                pass
            except ImportError:
                pass

        return modobj

    def request(self, module, collector):
        """Directives request data collection objects and the modules they should
        be defined in.

        Return reference to collector object if successful;
        Return None if failed.
        """

        # if collector already initiated, return reference
        if collector in list(self.collectors.keys()):
            return self.collectors[collector]

        log.log("<datacollect>DataModules.request(): importing module '%s' for collector '%s'" %
                (module, collector), 8)

        modobj = self.import_module(module)

        if modobj is None:
            log.log("<datacollect>DataModules.request(): error, collector '%s'/module '%s' not found or not available, os_search_path=%s" %
                    (collector, module, self. os_search_path), 3)
            raise DataModuleError("Collector '%s', module '%s' not found or not available, os_search_path=%s" %
                                  (collector, module, self.os_search_path))

        # initialise new collector instance
        if hasattr(modobj, collector):
            self.collectors[collector] = getattr(modobj, collector)()

        else:
            log.log("<datacollect>DataModules.request(): error, no such collector '%s' in module '%s'" %
                    (collector, module), 3)
            raise DataModuleError("No such collector '%s' in module '%s'" %
                                  (collector, module))

        log.log("<datacollect>DataModules.request(): collector %s/%s initialised" %
                (module, collector), 7)

        return self.collectors[collector]


class Data(object):
    """An empty class to hold any data to be stored.
    Do not access this data without first acquiring DataCollect.data_semaphore
    for thread-safety.
    """

    pass


class DataHistory(object):
    """Store previous data, with up to max_level levels of history.
    Set max_level with setHistory() or else no data is kept.
    """

    def __init__(self):
        self.max_level = 0                # how many levels of data to keep
        self.historical_data = []        # list of historical data (newest to oldest)

    def setHistory(self, level):
        """Set how many levels of historical data to keep track of.
        By default no historical data will be kept.

        The history level is only changed if the level is greater than
        the current setting.  The history level is always set to the highest
        required by all directives.
        """

        if level > self.max_level:
            self.max_level = level

    def __getitem__(self, num):
        """Overloaded [] to return the historical data, num is the age of the data.
        num can be 0 which is the current data; 1 is the previous data, etc.
        e.g., d = history[5]
        would assign d the Data object from 5 'collection periods' ago.
        """

        try:
            data = self.historical_data[num]
        except IndexError:
            raise IndexError("DataHistory index out-of-range: index=%d" % (num))

        return data

    def update(self, data):
        """Update data history by adding new data object to history list
        and removing oldest data from list.

        If max_level is 0, no history is required, so nothing is done.
        """

        if self.max_level > 0:
            if len(self.historical_data) > self.max_level:
                # remove oldest data
                self.historical_data = self.historical_data[:-1]

            self.historical_data.insert(0, data)

    def length(self):
        """Returns the current length of the historical data list;
        i.e., how many samples have been collected and are stored in the list.
        """

        # Subtract 1 from len as the first sample in list is always the current sample
        return len(self.historical_data) - 1


class DataCollect(object):
    """Provides a data collection and store class with automatic
    caching and refreshing of data in the cache.  Public functions
    are fully thread-safe as they can be called from many directive
    threads simultaneously.

    Data is cached for 55 seconds by default.  Assign self.refresh_rate
    to change this.  A collectData() function must be supplied by any
    child class of DataCollect.  This function should get data by
    whatever means and assign it to variables in self.data.

    Historical data will be automatically kept by calling setHistory(n)
    with n>0.  n levels of historical data will then be automatically
    kept.  If setHistory() is called multiple times, the highest n will
    stay in effect.

    Public functions are:
     getHash()        - return a copy of a data dictionary
     getList()        - return a copy of a data list
     hashKeys()        - return list of data dictionary keys
     __getitem__() - use DataCollect object like a dictionary to fetch data
     refresh()        - force a cache refresh
     setHistory(n) - set max level (n) of data history to automatically keep
    """

    def __init__(self):
        self.refresh_rate = 55        # amount of time current information will be
                                      # cached before being refreshed (in seconds)
        self.refresh_time = 0        # information must be refreshed at first request

        self.history_level = 0        # how many levels of historical data to keep
        self.history = DataHistory()        # historical data
        self.data_semaphore = threading.Semaphore()    # lock before accessing self.data/refresh_time

    # Public, thread-safe, methods
    def getHash(self, hash='datahash'):
        """Return a copy of the specified data hash, datahash by default.
        Specify an alternate variable name to fetch it instead.

        TODO: it might be better to use the 'copy' module to make sure
         a full deep copy is made of the date...
        """

        self._checkCache()              # refresh data if necessary
        dh = {}
        self.data_semaphore.acquire()        # thread-safe access to self.data
        exec('dh.update(self.data.%s)' % (hash))        # copy data hash
        self.data_semaphore.release()

        return(dh)

    def hashKeys(self):
        """Return the list of datahash keys.
        """

        self._checkCache()              # refresh data if necessary
        self.data_semaphore.acquire()        # thread-safe access to self.data
        k = list(self.data.datahash.keys())
        self.data_semaphore.release()

        return(k)

    def getList(self, listname):
        """Return a copy of the specified data list.
        The function is thread-safe and supports the built-in data caching.

        TODO: it might be better to use the 'copy' module to make sure
         a full deep copy is made of the date...
        """

        self._checkCache()              # refresh data if necessary
        self.data_semaphore.acquire()        # thread-safe access to self.data
        exec('list_copy = self.data.%s[:]' % (listname))  # copy data list
        self.data_semaphore.release()

        return(list_copy)

    def __getitem__(self, key):
        """Overload '[]', eg: returns corresponding data object for given key.

        TODO: it might be better to use the 'copy' module to make sure
         a full deep copy is made of the date...
        """

        self._checkCache()              # refresh data if necessary

        self.data_semaphore.acquire()        # thread-safe access to self.data
        try:
            r = self.data.datahash[key]
        except KeyError:
            self.data_semaphore.release()
            raise KeyError("Key %s not found in data hash" % (key))
        self.data_semaphore.release()

        return r

    def refresh(self):
        """Refresh data.

        This function can be called publically to force a refresh.
        """

        self.data_semaphore.acquire()        # thread-safe access to self.data
        log.log("<datacollect>DataCollect.refresh(): forcing data refresh", 7)
        self._refresh()
        self.data_semaphore.release()

    def setHistory(self, level):
        """Set how many levels of historical data to keep track of.
        By default no historical data will be kept.

        The history level is only changed if the level is greater than
        the current setting.  The history level is always set to the highest
        required by all directives.
        """

        self.history.setHistory(level)

    # Private methods.  Thread safety not guaranteed if not using public methods.
    def _checkCache(self):
        """Check if cached data is invalid, ie: refresh_time has been exceeded.
        """

        self.data_semaphore.acquire()                # thread-safe access to self.refresh_time and self._refresh()
        if time.time() > self.refresh_time:
            log.log("<datacollect>DataCollect._checkCache(): refreshing data", 7)
            self._refresh()
        else:
            log.log("<datacollect>DataCollect._checkCache(): using cached data", 7)
        self.data_semaphore.release()

    def _refresh(self):
        """Refresh data by calling _fetchData() and increasing refresh_time.

        This function must be called between data_semaphore locks. It is
        not thread-safe on its own.
        """

        self._fetchData()

        # new refresh time is current time + refresh rate (seconds)
        self.refresh_time = time.time() + self.refresh_rate

    def _fetchData(self):
        """Initialise a new data collection by first resetting the current data,
        then calling self.collectData() - a user-supplied function, see below -
        then storing historical data if necessary.

        Derivatives of this base class must define a collectData() method which
        should collect any data by whatever means and store that data in the
        self.data object.  It can be assumed all appropriate thread-locks are
        in place so access to self.data will be safe.
        """

        self.data = Data()                # new, empty data-store

        try:
            self.collectData()          # user-supplied function to collect some data
                                        # and store in self.data
        except DataFailure as err:
            log.log("<datacollect>DataCollect._fetchData(): DataFailure, %s" %
                    (err), 5)
            # TODO: need to tell the Directive that things have gone wrong?
        else:
            self.history.update(self.data)        # add collected data to history
