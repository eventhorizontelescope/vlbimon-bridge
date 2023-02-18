#!/usr/bin/env python

from setuptools import setup
from os import path

packages = [
    'vlbimon_bridge',
]

requires = ['pyyaml', 'requests', 'numpy']

test_requires = ['pytest', 'pytest-cov', 'pytest-sugar']

setup_requires = ['setuptools_scm']

extras_require = {
    'test': test_requires,  # setup no longer tests, so make them an extra that CI uses
}

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    description = f.read()

setup(
    name='vlbimon-bridge',
    use_scm_version=True,
    description='Tools to bridge vlbimon data to other database/graphing tools',
    long_description=description,
    long_description_content_type='text/markdown',
    author='Greg Lindahl',
    author_email='lindahl@pbm.com',
    url='https://github.com/wumpus/vlbimon-bridge',
    packages=packages,
    python_requires=">=3.6",
    extras_require=extras_require,
    include_package_data=True,
    setup_requires=setup_requires,
    install_requires=requires,
    entry_points='''
        [console_scripts]
        vlbimon_bridge = vlbimon_bridge.cli:main
    ''',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Natural Language :: English',
        'Programming Language :: Python',
        #'Programming Language :: Python :: 3.5',  # setuptools_scm now has f-strings
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
