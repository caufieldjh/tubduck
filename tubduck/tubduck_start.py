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
import urllib2

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
	
	#Check if working directory exists. If not, all tasks required.
	
	if path.exists():
		working_files = [x for x in path.iterdir()]
	else:
		setup_list.append("working directory")
	
	#Check on what we already have
	if kb_path.exists():
		kb_files = [x for x in path.iterdir()]
		if len(kb_files) == 0:
			setup_list.append("knowledge bases")
	else:
		setup_list.append("knowledge bases")
	
	return setup_list
	
def setup(setup_to_do):
	'''Main setup function. Calls other functions for some other tasks.
		Takes list as input.
		Returns True if setup encounters no errors.'''
		
	setup_all = True #Default is to set up everything
		
	if "working directory" in setup_to_do:
		path = Path('../working')
		path.mkdir(parents=True)
		setup_all = True
		
	if "knowledge bases" in setup_to_do:
		kb_path = Path('../working/kbs')
		kb_path.mkdir(parents=True)
		get_kbs(["do"],kb_path) #Just one for now
		
	return True
	
def get_kbs(names, path):
	'''
	Retrieves knowledge bases in their full form from various remote 
	locations. 
	Takes a list of two-letter codes as input.
	Also requires a Path where they will be written to. 
	Retrieves one or more of the following:
	 Disease Ontology database (do)
	 2018 MeSH term file from NLM (mo)
	 2017 SPECIALIST Lexicon from NLM (sl).
	The last of these requires decompression and returns a directory.
	The others return a filename.
	'''
	
	data_locations = {"do": ("http://ontologies.berkeleybop.org/","doid.obo"),
					"mo": ("ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/asciimesh/","d2018.bin"), #Need to update
					"sl": ("https://lexsrv3.nlm.nih.gov/LexSysGroup/Projects/lexicon/2017/release/LEX/", "LEXICON")} #Need to update
	
	filenames = []
	
	for name in names:
		baseURL, filename = data_locations[name]
		filepath = baseURL + filename
		outfilepath = path / filename
		
		print("Downloading from %s" % filepath)
		try:
			response = urllib2.urlopen(filepath)
			out_file = outfilepath.open("w+b")
			chunk = 1048576
			pbar = tqdm(unit="Mb")
			while 1:
				data = (response.read(chunk)) #Read one Mb at a time
				out_file.write(data)
				if not data:
					pbar.close()
					print("\n%s file download complete." % filename)
					out_file.close()
					break
				pbar.update(1)
		except urllib2.URLError as e:
			sys.exit("Encountered an error while downloading %s: %s" % (filename, e))
		filenames.append(filename)
	
	return filenames
		
