# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='tubduck',
    version='001',
    description='TUBDUCK is a system and accompanying platform for Translating Unstructured Biomedical Data into Unified, Coherent Knowledgebases. It renders experimental and clinical text as graphs, for integration into a knowledge graph. TUBDUCK is designed to be domain-sensitive, particularly for cardiovascular disease research and cardiovascular clinial case reports.',
    long_description=readme,
    author='Harry Caufield',
    author_email='jcaufield@mednet.ucla.edu',
    url='',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
