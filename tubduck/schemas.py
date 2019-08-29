#!/usr/bin/python
#schemas.py
'''
This is the schemas file for TUBDUCK.
Uses graphene package.

'''
__author__= "Harry Caufield"
__email__ = "jcaufield@mednet.ucla.edu"

import graphene


'''
CONCEPT SCHEMAS
'''

#All knowledgebase entries are Concept by default
class Concept(graphene.ObjectType): 
	kb_id = graphene.String()
	name = graphene.String()
	code = graphene.String()

'''
INSTANCE SCHEMAS
'''

