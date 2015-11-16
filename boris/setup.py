# Copyright (c) 2015 Mark Rees
#
# See the file LICENSE for usage & copying permission

import os
from setuptools import setup, find_packages
from boristool.version import get_version


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="boristool",
    version=get_version(),
    description="A system and network monitoring, security, and performance analysis agent",
    author="Mark Rees",
    author_email='mark.john.rees@gmail.com',
    url="https://github.com/hexdump42/boris-tool",
    license='GPLv2',
    packages=find_packages(exclude=['tests']),
    long_description=read('README.rst'),
    include_package_data=True,
    platforms='all',
    install_requires=[
        'psutil'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: System :: Monitoring'
    ],
    entry_points = {
        'console_scripts': [
            'boris-agent = scripts.boris_agent:main',
        ]
    }
)
