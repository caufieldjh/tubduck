#!/usr/bin/python
#tubduck_input.py
'''
Input handling functions for TUBDUCK.

This includes obtaining local documents and retrieving from remote locations,
primarily PubMed. Local files are stored in either raw (i.e., text only)
or in MEDLINE format, in their respective directories within the "input"
directory.
'''

from pathlib import Path

## Constants
INPUT_PATH = Path('../input')
MEDLINE_PATH = Path('../input/medline')
RAW_PATH = Path('../input/raw')

## Functions
def get_local_docs():
	'''Retrieve locally stored documents.
	These may be in MEDLINE format or raw format.
	In MEDLINE format, a file may contain >1 document.'''
	
	doc_file_index = {}
	
	medline_file_list = [x for x in MEDLINE_PATH.iterdir()]
	raw_file_list  = [x for x in RAW_PATH.iterdir()]
	
	doc_file_index["MEDLINE"] = medline_file_list
	doc_file_index["raw"] = raw_file_list
	
	return doc_file_index
	
def setup():
	'''Create directories if they don't yet exist.'''
	INPUT_PATH.mkdir(exist_ok=True)
	MEDLINE_PATH.mkdir(exist_ok=True)
	RAW_PATH.mkdir(exist_ok=True)
	
