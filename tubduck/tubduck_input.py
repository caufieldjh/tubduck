#!/usr/bin/python
#tubduck_input.py
'''
Input handling functions for TUBDUCK.
'''

'''
This includes obtaining local documents and retrieving from remote locations,
primarily PubMed.
'''

from pathlib import Path

## Constants
INPUT_PATH = Path('../input')

## Functions
def get_local_docs():
	'''Really a placeholder function for now'''
	
	doc_list = [x for x in INPUT_PATH.iterdir()]
	
	return doc_list
