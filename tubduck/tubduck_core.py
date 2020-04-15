#!/usr/bin/python
#tubduck_core.py
'''
This is the primary file for TUBDUCK.
It is intended to call all submethods as modules.

Requires Python 3.4 or above.
Uses Neo4j graph database. 
  This requires Java 8; see https://neo4j.com/docs/ for more info.

TUBDUCK is a system and accompanying platform for
Translating Unstructured Biomedical Data into Unified, Coherent 
Knowledgebases. It renders experimental and clinical text as graphs,
for integration into a knowledge graph. TUBDUCK is designed to be
domain-sensitive, particularly for cardiovascular disease research
and cardiovascular clinial case reports.
'''
__author__= "Harry Caufield"
__email__ = "jcaufield@mednet.ucla.edu"

import sys, argparse

#import nltk

import tubduck_helpers as thelp
import tubduck_start as tstart
import tubduck_input as tinput
import tubduck_process as tproc
import tubduck_output as toutput

## Constants and Options
parser = argparse.ArgumentParser()
parser.add_argument("--empty_db", help="empty the TUBDUCK Neo4j DB", 
					action="store_true")
parser.add_argument("--test_load_db", help="load only a testing set (100 entries each) of each data source into the DB", 
					action="store_true")
parser.add_argument("--get_pmid", help="retrieve one or more documents in MEDLINE format from PubMed based on PMID", 
					action="append", nargs='+')
parser.add_argument("--get_pmid_file", help="retrieve documents specified in a file containing one PMID per line",
					action="append")
args = parser.parse_args()

## Classes

## Functions

## Main
def main():
	
	pmids_to_get = []
	
	#Check to see if there are command line arguments first
	tasks = [] #All user-specified tasks will go here
	if args.empty_db:
		tasks.append("empty_db")
	if args.test_load_db:
		tasks.append("test_load_db")
	if args.get_pmid:
		for pmid in args.get_pmid[0]:
			pmids_to_get.append(pmid)
	if args.get_pmid_file:
		with open(args.get_pmid_file[0]) as pmid_file:
			for pmid in pmid_file:
				pmids_to_get.append(pmid)
	
	print("*** TUBDUCK ***")
	
	#A quick version check
	if sys.version_info[0] < 3:
		sys.exit("Not compatible with Python2 -- sorry!\n"
					"Exiting...")
	else:
		if sys.version_info[1] < 7:
			sys.exit("Python3.7 or more recent is required for proper operation.\n"
						"Exiting...")
	
	print("Checking to see what setup may be required.")
	setup_to_do = tstart.setup_checks(tasks)
	if len(setup_to_do) > 0:
		print("Performing intial setup for: \n* %s" % ("\n* ".join(setup_to_do)))
		if tstart.setup(setup_to_do):
			print("All setup complete.")
			if "empty_db" in tasks:
				sys.exit("Database empty, exiting.")
		else:
			sys.exit("Setup did not complete properly.")
	else:
		print("No setup required.")
		
	print("Getting input ready.")
	tinput.setup()

	if len(pmids_to_get) > 0 :
		newpmidfile = tinput.get_remote_docs(pmids_to_get)
	doc_file_index = tinput.get_local_docs()
	parsed_docs = {}
	for filetype in doc_file_index:
		filecount = len(doc_file_index[filetype])
		if filecount == 0:
			print("Found no local %s input files." % filetype)
		else:
			print("Found %s local %s input files." % (filecount, filetype))
	tinput.parse_docs(doc_file_index)
	
	print("Processing...")
	#Run tubduck_process methods
	
	print("Preparing output...")
	#Run tubduck_output methods
	
	print("Done.")

if __name__ == "__main__":
	sys.exit(main())

