import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    string_types = (str,)
    unichr = chr
    long = int
else:
    text_type = unicode
    string_types = (str, unicode)
    unichr = unichr
    long = long
