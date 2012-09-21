#!/usr/bin/env python
from setuptools import setup, find_packages

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules'
]

KEYWORDS = 'snapbill api wrapper'


setup(name = 'snapbill',
    version = "0.2",
    description = """Wrapper for the SnapBill v1 API.""",
    author = "Josh Yudaken",
    url = "https://github.com/snapbill/snapbill-pyapi",
    packages = find_packages(),
    download_url = "http://pypi.python.org/pypi/snapbill/",
    install_requires=[
      "simplejson>=2.0.0"
    ],
    classifiers = CLASSIFIERS,
    keywords = KEYWORDS,
    zip_safe = True,
)
