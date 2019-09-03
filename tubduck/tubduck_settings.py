#!/usr/bin/python
#tubduck_settings.py

'''
This is the TUBDUCK settings file.
It sets default environment variables, primarily for Neo4j.
Because these are environment variables, they may vary by environment.
It's all right there in the name. Fun, right?
'''
__author__= "Harry Caufield"
__email__ = "jcaufield@mednet.ucla.edu"

from environs import Env

env = Env()

DEBUG = env.bool('DEBUG', default=False)
BIND_HOST = env('BIND_HOST', default='127.0.0.1')
BIND_PORT = env.int('BIND_PORT', default=5000)
NEO4J_HOST = env('NEO4J_HOST', default='localhost')
NEO4J_PORT = env.int('NEO4J_PORT', default=7687)
NEO4J_USER = env('NEO4J_USER', default='neo4j')
NEO4J_PASSWORD = env('NEO4J_PASSWORD', default='admin')
