#!/usr/bin/python
#tubduck_input.py
'''
Input handling functions for TUBDUCK.

This includes obtaining local documents and retrieving from remote locations,
primarily PubMed. Local files are obtained in either raw (i.e., text only)
or in MEDLINE format, in their respective directories within the "input"
directory. They are then stored in an SQLite database.
'''

from datetime import datetime
from pathlib import Path
from tqdm import *
import urllib
from urllib.parse import urlencode
from urllib.request import urlopen

import sqlite3

from Bio import Medline

## Constants
INPUT_PATH = Path('../input')
MEDLINE_PATH = Path('../input/medline')
RAW_PATH = Path('../input/raw')
DB_PATH = Path('../input/db.sqlite')

## Functions
def get_local_docs():
	'''Retrieve locally stored documents.
	These may be in MEDLINE format or raw format.
	In MEDLINE format, a file may contain >1 document.'''
	
	doc_file_index = {}
	
	medline_file_list = [x for x in MEDLINE_PATH.iterdir()]
	raw_file_list  = [x for x in RAW_PATH.iterdir()]
	
	doc_file_index["medline"] = medline_file_list
	doc_file_index["raw"] = raw_file_list
	
	return doc_file_index
	
def get_remote_docs(pmids):
	'''Retrieve documents from PubMed, given one or more PMIDs.
	Input is a list. Returns a dict.'''
	
	success = False
	
	datetimestring = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
	outfilename = datetimestring + "_MEDLINE.txt"
	outfilepath = MEDLINE_PATH / outfilename
	baseURL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
	epost = "epost.fcgi"
	efetch = "efetch.fcgi"
	options = "&usehistory=y&retmode=text&rettype=medline"
	
	out_file = open(outfilepath, "w+b")
	
	print("Retrieving %s record(s) from PubMed." % len(pmids))
	
	#POST using epost first, with all PMIDs
	idstring = ",".join(pmids)
	queryURL = baseURL + epost
	args = urlencode({"db":"pubmed","id":idstring}).encode('utf-8')
	response = urlopen(queryURL, args)
	
	response_text = (response.read()).splitlines()
	webenv_value = (response_text[3].strip())[8:-9]
	webenv = "&WebEnv=" + str(webenv_value)
	querykey_value = (response_text[2].strip())[10:-11]
	querykey = "&query_key=" + str(querykey_value)
	
	batch_size = 1000 #This can, in theory, be up to 100,000
							#before batches should be iterated through
							#by increasing the retstart value.
	i = 0
	
	try:
		#Now retrieve entries
		pbar = tqdm(unit="Mb")
		while i <= len(pmids):
			queryURL = baseURL + efetch 
			args = urlencode({"db":"pubmed","query_key":querykey_value,"WebEnv":webenv_value,
								"retstart":str(i),"retmax":str(batch_size),
								"usehistory":"y","retmode":"text","rettype":"medline"}).encode('utf-8')
			response = urlopen(queryURL, args)
			
			out_file = open(outfilepath, "a")
			chunk = 1048576
			while 1:
				data = (response.read(chunk)) #Read one Mb at a time
				out_file.write(str(data, 'utf-8'))
				if not data:
					break
				pbar.update(1)
			i = i + batch_size
		pbar.close()
		out_file.close()
		
		success = True
		
	except urllib.error.HTTPError as e:
		print("Encountered error while retrieving PubMed entries: %s" % e)
	
	if success:
		print("Retrieved PubMed entries and wrote to %s" % outfilepath)
	else:
		print("Could not retrieve PubMed entries.")
		
	return outfilepath

def parse_docs(doc_file_index):
	'''Parses input documents. This varies based on their filetype,
	which may be 'medline' or 'raw'. In the first case, each entry is
	named based on its PMID and populated with MEDLINE format fields.
	For raw documents, they will be identified based on their filenames.
	Takes a dictionary as input, as produced by the get_local_docs()
	method. Loads contents into input database.'''
	
	dbcon = input_db_connect()
	cur = dbcon.cursor()
	
	doc_id = 0
	
	for filetype in doc_file_index:
		if filetype == "medline": #Need to parse further
			for doc_file_path in doc_file_index[filetype]:
				with open(doc_file_path) as handle:
					records = Medline.parse(handle)
					for record in records:
						
						record["id"] = doc_id
						if "IS" in record.keys(): #Incompatible with SQL
							del record["IS"]
						
						newrecord = {} #Need to flatten some lists
						for datatype in record:
							if type(record[datatype]) is list:
								newrecord[datatype] = "|".join(record[datatype])
							else:
								newrecord[datatype] = record[datatype]
						record = newrecord
									
						columns = ', '.join(record.keys())
						placeholders = ':'+', :'.join(record.keys())
						sql = """INSERT INTO documents(%s)
									VALUES(%s)""" % (columns, placeholders)
									
						try:
							cur.execute(sql, record)
						except sqlite3.OperationalError as e:
							print(e)
							pass		#Note this will NOT load the entry
						
						doc_id = doc_id +1
				
		# if filetype == "raw": #Not much to parse yet
			# for doc_file_path in doc_file_index[filetype]:
				# filename = doc_file_path.stem
				# parsed_docs[filename] = {}
				# parsed_docs[filename]['text'] = []
				# with open(doc_file_path) as raw_doc:
					# for line in raw_doc:
						# parsed_docs[filename]['text'].append(line)
				# doc_id = doc_id +1
	
	print("Loaded %s documents." % int(cur.rowcount +1))
	#sql = "SELECT * FROM documents"
	#cur.execute(sql)
	#sample = cur.fetchall()
	#print([description[0] for description in cur.description])
	#print(sample)
	
def input_db_connect(db_path=DB_PATH):
	dbcon = sqlite3.connect(DB_PATH)
	return dbcon
	
def setup():
	'''Create directories if they do not yet exist.'''
	INPUT_PATH.mkdir(exist_ok=True)
	MEDLINE_PATH.mkdir(exist_ok=True)
	RAW_PATH.mkdir(exist_ok=True)
	
	'''Setup document database. Defines most fields upon initial parsing.'''
	dbcon = sqlite3.connect(DB_PATH)
	cur = dbcon.cursor()
	setup_sql = """CREATE TABLE IF NOT EXISTS documents (
				id integer PRIMARY KEY,
				AB text, 
				AD text,
				AID text,
				AU text,
				AUID text,
				CI text,
				CIN text,
				CN text,
				CON text,
				COIS text,
				CRDT text,
				CRF text,
				CRI text,
				DCOM text,
				DEP text,
				DP text,
				EDAT text,
				EIN text,
				FAU text,
				FIR text,
				FPS text,
				GN text,
				GR text,
				GS text,
				IP text,
				IR text,
				IRAD text,
				JID text,
				JT text,
				LA text,
				LID text,
				LR text,
				MH text,
				MHDA text,
				MID text,
				OAB text,
				OABL text,
				OT text,
				OTO text,
				OWN text,
				PG text,
				PHST text,
				PL text,
				PMC text,
				PMCR text,
				PMID text,
				PS text,
				PST text,
				PT text,
				RF text,
				RIN text,
				RN text,
				RPI text,
				SB text,
				SI text,
				SO text,
				STAT text,
				TA text,
				TI text,
				TT text,
				VI text)"""
	cur.execute(setup_sql)
