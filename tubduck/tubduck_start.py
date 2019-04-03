#!/usr/bin/python
#tubduck_start.py
'''
Functions for TUBDUCK to construct all necessary databases and learning
modules. This includes accumulating training data and training the 
modules themselves. 
'''

'''
A. Information extraction modules
	1. Document categorization modules
		a. Clinical vs. experimental text categorization module
		b. Biomedical topic/domain categorization module
			i. CVD vs. non-CVD categorization module
				a. Using Flair
		c. ICD-10 code prediction
	2. Entity recognition (NER) modules
		a. Gene/Protein normalization submodule
			i. Start with GNormPlus (this is fairly limited though)
			ii. Train a new NER module using Flair embeddings trained on:
				a. BioCreative II gene normalization training set
		b. Disease normalization module
			i. Start with DNorm
			ii. Train a new NER module using Flair embeddings trained on:
				a. NCBI Disease Corpus
	3. Relation extraction (RE) modules
	4. Coreference modules
	5. Computational infrastructure
		a. Data aggregation
			i. Retrieving biomedical text documents and metadata
				a. Borrow code from HeartCases
				b. Try with PubRunner
			ii. Accepting and checking validity of documents not in text corpus
				a. Primarily checking data sanity
			iii. Retrieving structured data from KBs
				a. IMEx/IntAct (for PPIs)
					1. Borrow code from pining project
				b. Disease Ontology (for concept graph)
				c. Wikidata (for concept graph)
				d. ConceptNet (for concept graph)
		b. Data integration
			i. Standardization of document contents
			ii. Running text through doc categorization
			iii. Running text through NER
			iv. Running text through RE
			v. Running text through Coref
			vi. Fit results to schema
			vii. Prep results for formalization as case graph
B. Graph methods
	1. Computational infrastructure
		a. Setup of graph DB
	2. Assembly of case graphs
	3. Graph integration methods
		a. Conflict resolution
	4. Instance graph assembly
	5. Concept graph assembly
'''

import os

from urllib.request import urlopen
import urllib.error

from pathlib import Path
from tqdm import *

## Functions
def setup_checks():
	'''Check to see which setup steps need to be completed.
		This is primarily based on what files already exist.
		Returns list of strings, where each item denotes a task to 
		be completed before proceeding.'''
		
	setup_list = []
	working_files = []
	path = Path('../working')
	kb_path = Path('../working/kbs')
	kb_proc_path = Path('../working/kbs/processed')
	
	#Check if working directory exists. If not, all tasks required.
	
	if path.exists():
		working_files = [x for x in path.iterdir()]
	else:
		setup_list.append("working directory")
	
	#Check on what we already have
	if kb_path.exists():
		kb_files = [x for x in kb_path.iterdir()]
		if len(kb_files) == 0:
			setup_list.append("retrieve all knowledge bases")
		else:
			setup_list.append("retrieve some knowledge bases")
	else:
		setup_list.append("retrieve all knowledge bases")
	if kb_proc_path.exists():
		kb_proc_files = [x for x in kb_proc_path.iterdir()]
		if len(kb_proc_files) == 0:
			setup_list.append("process all knowledge bases")
		else:
			setup_list.append("process some knowledge bases")
	else:
		setup_list.append("process all knowledge bases")
	
	return setup_list
	
def setup(setup_to_do):
	'''Main setup function. Calls other functions for some other tasks.
		Takes list as input.
		Returns True if setup encounters no errors.'''
		
	setup_all = True #Default is to set up everything
	status = True
	kb_codes = ["do","mo","sl"] #Knowledge bases each get two-char code
	kb_proc_codes = kb_codes
		
	if "working directory" in setup_to_do:
		path = Path('../working')
		path.mkdir(parents=True)
		setup_all = True
		
	if "retrieve all knowledge bases" in setup_to_do:
		kb_path = Path('../working/kbs')
		kb_path.mkdir(parents=True)
		
	if "retrieve some knowledge bases" in setup_to_do:
		kb_path = Path('../working/kbs')
		kb_files = [x.stem for x in kb_path.iterdir()]
		need_kb_files = []
		if "doid" not in kb_files:
			need_kb_files.append("do")
		if "d2019" not in kb_files:
			need_kb_files.append("mo")
		if "LEXICON" not in kb_files:
			need_kb_files.append("sl")
		kb_codes = need_kb_files
		
	if not get_kbs(kb_codes,kb_path):
		print("Encountered errors while retrieving knowledge base files.")
		status = False
	
	if "process all knowledge bases" in setup_to_do:
		kb_proc_path = Path('../working/kbs/processed')
		kb_proc_path.mkdir(parents=True)
	
	if "process some knowledge bases" in setup_to_do:
		kb_proc_path = Path('../working/kbs/processed')
		kb_proc_files = [x.stem for x in kb_proc_path.iterdir()]
		need_kb_proc_files = []
		if "doid-proc" not in kb_files:
			need_kb_files.append("do")
		if "d2019-proc" not in kb_files:
			need_kb_files.append("mo")
		if "LEXICON-proc" not in kb_files:
			need_kb_files.append("sl")
		kb_proc_codes = need_kb_proc_files
		
	if not process_kbs(kb_proc_codes,kb_path,kb_proc_path):
		print("Encountered errors while processing knowledge base files.")
		status = False
			
	return status
	
def get_kbs(names, path):
	'''Retrieves knowledge bases in their full form from various remote 
	locations. 
	Takes a list of two-letter codes as input.
	Also requires a Path where they will be written to. 
	Retrieves one or more of the following:
	 Disease Ontology (do)
	 2018 MeSH term file from NLM (mo)
	 2019 SPECIALIST Lexicon from NLM (sl).'''
	
	data_locations = {"do": ("http://ontologies.berkeleybop.org/","doid.obo"),
					"mo": ("ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/asciimesh/","d2019.bin"), 
					"sl": ("https://lsg3.nlm.nih.gov/LexSysGroup/Projects/lexicon/2019/release/LEX/", "LEXICON")}
	
	filenames = []
	status = True #Becomes False upon encountering error
	
	for name in names:
		baseURL, filename = data_locations[name]
		filepath = baseURL + filename
		outfilepath = path / filename
		
		print("Downloading from %s" % filepath)
		try:
			response = urlopen(filepath)
			out_file = outfilepath.open("w+b")
			chunk = 1048576
			pbar = tqdm(unit="Mb")
			while 1:
				data = (response.read(chunk)) #Read one Mb at a time
				out_file.write(data)
				if not data:
					pbar.close()
					#print("\n%s file download complete." % filename)
					out_file.close()
					break
				pbar.update(1)
		except urllib.error.URLError as e:
			print("Encountered an error while downloading %s: %s" % (filename, e))
			status = False
			
	return status
	
def process_kbs(names, inpath, outpath):
	'''Loads knowledge bases into memory.
	Takes a list of two-letter codes as input.
	Also requires a Path to the folder where they are AND where they
	should go once processed.'''
	
	#Just copies files for now as placeholder
	
	status = True
	
	kb_names = {"do": "doid.obo",
					"mo": "d2019.bin", 
					"sl": "LEXICON"}
	
	for name in names:
		infilename = kb_names[name]
		infilepath = inpath / infilename
		newfilename = (str(infilename.split(".")[0])) + "-proc"
		outfilepath = outpath / newfilename
		print("Processing %s." % infilename)
		try:
			pbar = tqdm()
			with infilepath.open() as infile:
				with outfilepath.open("w") as outfile:
					for line in infile:
						#print(line)
						outfile.write(line)
						pbar.update(1)
			pbar.close()
		except IOError as e:
			print("Encountered an error while processing %s: %s" % (infilename, e))
	
	return status
		
