import os
print(os.path.abspath(__file__))
import sys
print(sys.path)
from . import env
print(sys.path)
