import os

from setuptools import find_packages, setup

from collector import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='watcheye-collector',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    description='A Django application to collect monitoring data samples '
                'through HTTP or SNMP GET interface.',
    long_description=README,
    url='https://github.com/watcheye/watcheye-collector',
    author='Andrzej Mateja',
    author_email='mateja.and@gmail.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: '
        'GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP'
    ],
    install_requires=[
        'celery[redis]>=4.2.0',
        'django>=2.0.0',
        'influxdb>=5.2.0',
        'pyasn1',
        'pysnmp'
    ]
)
