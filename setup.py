#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['asyncio',
                'durable_rules',
                'pyparsing',
                'redis',
                'dpath',
                'ansible-runner']

test_requirements = ['pytest>=3',
                     'pytest-asyncio']

setup(
    author="Ben Thomasson",
    author_email='ben.thomasson@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Event driven automation for Ansible",
    entry_points={
        'console_scripts': [
            'ansible-events=ansible_events.cli:entry_point',
        ],
    },
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ansible_events',
    name='ansible_events',
    packages=find_packages(include=['ansible_events', 'ansible_events.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/benthomasson/ansible-events',
    version='0.1.1',
    zip_safe=False,
)
