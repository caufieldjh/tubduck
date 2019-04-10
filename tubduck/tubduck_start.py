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

'''
Now:
Check for duplicates before adding nodes or relation (i.e., add all as unique).
Add relations more intelligently.
Add more material to concept graph (Reactome pathways and constituent proteins).
Load and add baseline instance graph material (IntAct PPI).
'''

import os
import subprocess
import sys
import time
#import resource #for raising open file limits as per Neo4j

import ast

from urllib.request import urlopen
import urllib.error

from pathlib import Path
from tqdm import *

from neo4j import GraphDatabase

## Constants
TOTAL_KBS = 3 #The total count of knowledge bases we'll use
				#To be specified in more detail later
WORKING_PATH = Path('../working')
KB_PATH = Path('../working/kbs')
KB_PROC_PATH = Path('../working/kbs/processed')

KB_NAMES = {"do": "doid.obo",		#The set of all knowledge bases,
				"mo": "d2019.bin",  #with two-letter codes as keys.
				"sl": "LEXICON"}

## Functions
def setup_checks():
	'''Check to see which setup steps need to be completed.
		This is primarily based on what files already exist.
		Returns list of strings, where each item denotes a task to 
		be completed before proceeding.'''
		
	setup_list = []
	working_files = []

	#Check if working directory exists. If not, all tasks required.
	
	if WORKING_PATH.exists():
		working_files = [x for x in WORKING_PATH.iterdir()]
	else:
		setup_list.append("working directory")
	
	#Check on what we already have
	if KB_PATH.exists():
		kb_files = [x for x in KB_PATH.iterdir()]
		if len(kb_files) == 0:
			setup_list.append("retrieve all knowledge bases")
		elif len(kb_files) < TOTAL_KBS:
			setup_list.append("retrieve some knowledge bases")
	else:
		setup_list.append("retrieve all knowledge bases")
		
	if KB_PROC_PATH.exists():
		kb_proc_files = [x for x in KB_PROC_PATH.iterdir()]
		if len(kb_proc_files) == 0:
			setup_list.append("process all knowledge bases")
		elif len(kb_proc_files) < TOTAL_KBS:
			setup_list.append("process some knowledge bases")
	else:
		setup_list.append("process all knowledge bases")
	
	graph_exists = True
	if not graphdb_exists():
		setup_list.append("set up graph DB")
		setup_list.append("populate graph DB")
		graph_exists = False
	
	if graph_exists:
		gdb_vals = graphdb_stats()
		if gdb_vals["rel_count"] < 2:
			setup_list.append("populate graph DB")

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
		WORKING_PATH.mkdir(parents=True)
		setup_all = True
		
	if "retrieve all knowledge bases" in setup_to_do:
		KB_PATH.mkdir(parents=True)
		if not get_kbs(kb_codes,KB_PATH):
			print("Encountered errors while retrieving knowledge base files.")
			status = False
		
	if "retrieve some knowledge bases" in setup_to_do:
		kb_files = [x.stem for x in KB_PATH.iterdir()]
		need_kb_files = []
		if "doid" not in kb_files:
			need_kb_files.append("do")
		if "d2019" not in kb_files:
			need_kb_files.append("mo")
		if "LEXICON" not in kb_files:
			need_kb_files.append("sl")
		kb_codes = need_kb_files
		if not get_kbs(kb_codes,KB_PATH):
			print("Encountered errors while retrieving knowledge base files.")
			status = False
	
	if "process all knowledge bases" in setup_to_do:
		KB_PROC_PATH.mkdir(parents=True)
		if not process_kbs(kb_proc_codes,KB_PATH,KB_PROC_PATH):
			print("Encountered errors while processing knowledge base files.")
			status = False
	
	if "process some knowledge bases" in setup_to_do:
		kb_proc_files = [x.stem for x in KB_PROC_PATH.iterdir()]
		need_kb_proc_files = []
		if "doid-proc" not in kb_proc_files:
			need_kb_proc_files.append("do")
		if "d2019-proc" not in kb_proc_files:
			need_kb_proc_files.append("mo")
		if "LEXICON-proc" not in kb_proc_files:
			need_kb_proc_files.append("sl")
		kb_proc_codes = need_kb_proc_files
		if not process_kbs(kb_proc_codes,KB_PATH,KB_PROC_PATH):
			print("Encountered errors while processing knowledge base files.")
			status = False
		
	if "set up graph DB" in setup_to_do:
		if not create_graphdb():
			print("Encountered errors while setting up graph database.")
			status = False
	
	if "populate graph DB" in setup_to_do:
		if not populate_graphdb():
			print("Encountered errors while populating graph database.")
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
	
	status = True
	
	#Processing methods are KB-specific as formats vary
	for name in names:
		if name == "do":
			if process_do(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		if name == "mo":
			if process_mo(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		if name == "sl":
			if process_sl(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		else:
			pass
	
	return status

def process_do(infilename, inpath, outpath):
	'''Processes the Disease Ontology into relationship format.
	Takes input from process_kbs.'''
	
	status = True
	
	infilepath = inpath / infilename
	newfilename = (str(infilename.split(".")[0])) + "-proc"
	outfilepath = outpath / newfilename
	print("Processing %s." % infilename)
	try:
		pbar = tqdm(unit=" lines")
		with infilepath.open() as infile:
			with outfilepath.open("w") as outfile:
				entry = {}
				for line in infile:
					text = line.strip().split(":",1)
					if text == ["[Term]"]: #start new entry for term
						if len(entry.keys()) > 0: #If we have a previous entry, write it
							outfile.write(str(entry) + "\n")
						entry = {}
					if text[0] in ["id","name","alt_id","def","subset","synonym","xref","is_a"]:
						if text[0] in entry.keys(): #Have it already
							entry[text[0]].append(text[1].strip())
						else:
							entry[text[0]] = [text[1].strip()]
					if text == ["[Typedef]"]: #Don't do anything with these yet
						if len(entry.keys()) > 0: #Write the last entry
							outfile.write(str(entry) + "\n")
						entry = {}
					pbar.update(1)
				
		pbar.close()
	except IOError as e:
		print("Encountered an error while processing %s: %s" % (infilename, e))
		status = False

	return status

def process_mo(infilename, inpath, outpath):
	'''Processes MeSH into relationship format.
	Takes input from process_kbs.'''
	
	status = True
	
	infilepath = inpath / infilename
	newfilename = (str(infilename.split(".")[0])) + "-proc"
	outfilepath = outpath / newfilename
	print("Processing %s." % infilename)
	try:
		pbar = tqdm(unit=" lines")
		with infilepath.open() as infile:
			with outfilepath.open("w") as outfile:
				entry = {}
				for line in infile:
					text = line.strip().split("=",1)
					if text == ["*NEWRECORD"]: #start new entry for term
						if len(entry.keys()) > 0: #If we have a previous entry, write it
							outfile.write(str(entry) + "\n")
						entry = {}
					if text[0].strip() in ["RECTYPE","MH","AQ","ENTRY","MN","PA"]:
						if text[0].strip() in entry.keys(): #Have it already
							entry[text[0].strip()].append(text[1].strip())
						else:
							entry[text[0].strip()] = [text[1].strip()]
					pbar.update(1)
				if len(entry.keys()) > 0: #Write the last entry
					outfile.write(str(entry) + "\n")
					
		pbar.close()
	except IOError as e:
		print("Encountered an error while processing %s: %s" % (infilename, e))
		status = False

	return status
	
def process_sl(infilename, inpath, outpath):
	'''Processes Semantic Lexicon into relationship format.
	Takes input from process_kbs.'''
	
	status = True
	
	infilepath = inpath / infilename
	newfilename = (str(infilename.split(".")[0])) + "-proc"
	outfilepath = outpath / newfilename
	print("Processing %s." % infilename)
	try:
		pbar = tqdm(unit=" lines")
		with infilepath.open() as infile:
			with outfilepath.open("w") as outfile:
				entry = {}
				for line in infile:
					text = line.strip().split("=",1)
					if text[0] == "{base": #start new entry for term
						if len(entry.keys()) > 0: #If we have a previous entry, write it
							outfile.write(str(entry) + "\n")
						entry = {}
						entry["base"] = text[1]
					if text[0].strip() in ["entry","cat","variants"]:
						if text[0] in entry.keys(): #Have it already
							entry[text[0]].append(text[1].strip())
						else:
							entry[text[0]] = [text[1].strip()]
					pbar.update(1)
				if len(entry.keys()) > 0: #Write the last entry
					outfile.write(str(entry) + "\n")
		pbar.close()
	except IOError as e:
		print("Encountered an error while processing %s: %s" % (infilename, e))
		status = False

	return status

def create_graphdb():
	'''Sets up an empty Neo4j database through py2neo.
	Sets the initial password as Neo4j requires it.
	(Note - this needs to happen BEFORE starting Neo4j.)
	Populates the graph with initial nodes and relationships.
	Returns True if the graph DB is created successfully.'''
	
	status = False
	
	#Only really need to set password once, but before starting Neo4j the first time
	#So we need to restart its server
	subprocess.run(["sudo","neo4j-admin", "set-initial-password", "tubduck"])
	start_neo4j()
	#resource.setrlimit(resource.RLIMIT_NOFILE, (100000, 100000))
	
	#try:
	driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tubduck"))
	statement = "CREATE (a:Concept {name:{name}, source:{source}})"
	
	with driver.session() as session:
		tx = session.begin_transaction()
		tx.run("MATCH (n) DETACH DELETE n") #Clear anything that already exists
		
		tx.run(statement, {"name": "protein", "source": "NA"})
		tx.run(statement, {"name": "biomolecule", "source": "NA"})
		tx.run("MATCH (a:Concept),(b:Concept) "
				"WHERE a.name = 'protein' AND b.name = 'biomolecule' " 
				"CREATE (a)-[r:is_a]->(b)")
		tx.commit()

		print("Graph DB created: access at http://localhost:7474")
		status = True
		
	#print("Encountered an error in graph DB setup: could not create relation.")
		
	# except Exception as e:
		# print("**Encountered an error in Neo4j graph DB setup: %s" % e)
		# print("**Please try accessing the server at http://localhost:7474/")
		# print("**The default username is \"neo4j\" and the password is \"neo4j\".")
	
	return status
	
def graphdb_exists():
	'''Checks to see if the Neo4j database exists.
	It may be available for the local user or at the system level.
	Returns True if it exists, even if it's empty,
	because we don't do anything with the DB here.'''
	
	status = False
	
	ndb_home_path = Path.home() / "neo4j/data/databases"
	ndb_sys_path = Path("/var/lib/neo4j/data/databases")
	
	ndb_paths = [ndb_home_path, ndb_sys_path]
	
	for path in ndb_paths:
		if path.exists():
			ndb_files = [x for x in path.iterdir()]
			if len(ndb_files) > 0:
				print("Found existing Neo4j database at %s." % path)
				status = True
	if not status:
		print("Did not find existing Neo4j database.")
		
	return status
	
def graphdb_stats():
	'''Gets details about the Neo4j database.
	Returns a dict of values.'''
	
	graphdb_values = {}
	
	start_neo4j()
	
	driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tubduck"))
	
	with driver.session() as session:
		graph_data = session.run("MATCH ()-->() RETURN count(*)").data()
		
	rel_count = graph_data[0]["count(*)"]
	graphdb_values["rel_count"] = rel_count
	
	if rel_count < 2:
		print("Neo4j database requires population.")
	else:
		print("Neo4j database contains %s relations." % str(graphdb_values["rel_count"]))
	
	return graphdb_values

def start_neo4j():
	'''Checks if the Neo4j server is running, and if not, 
	starts it. If it's already running it gets restarted.
	Note that this is specifically whether the superuser is running
	the server, not a different user running it locally.
	Note this will fail completely if Neo4j is not installed!'''
	
	status = False
	
	process = subprocess.Popen(["sudo", "neo4j", "status"], stdout=subprocess.PIPE)
	out, err = process.communicate()
	if out.rstrip() == b"Neo4j is not running": #Start Neo4j
		print("Starting Neo4j.")
		subprocess.run(["sudo", "neo4j", "start"])
		time.sleep(5) #Take a few moments to let service start
		status = True
	elif out.rstrip() == b"sudo: neo4j: command not found": #Not installed
		print("Neo4j may not be installed on this system.")
		status = False
		sys.exit()
	elif (out.rstrip())[1:16] == b"Neo4j is running": #Try restarting it
		subprocess.run(["sudo", "neo4j", "restart"])
		time.sleep(5) #Take a few moments to let service start
		status = True
	else:
		status = True
		
	return status
	
def populate_graphdb():
	'''Loads entities and relations into graph DB from processed KBs.
	Most of these form the concept graph: they define conceptual
	relationships, including "is a" relationships.
	Initial contents of the instance graph are also included: these
	relationships correspond to reported events within text, e.g.,
	symptoms or diagnostics reported within clinical case reports.
	Returns True if all population activities complete without error.'''
	
	status = False
	
	driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tubduck"))
	
	print("Populating graph DB...")
	
	#Load each KB, then load its relations.
	#Note that not every dict entry is a valid relation.
	i = 0
	for kb in KB_NAMES:
		kb_rels = []
		infilename = KB_NAMES[kb].split(".")[0] + "-proc"
		print("Loading entries from %s..." % infilename)
		pbar = tqdm(unit=" entries")
		infilepath = KB_PROC_PATH / infilename
		with infilepath.open('r') as infile:
			for line in infile: #Go line-by-line to be careful
				kb_rels.append(ast.literal_eval(line.rstrip()))
				pbar.update(1)
		pbar.close()
		
		print("Loading relevant nodes and relations into graph DB...")
		# Now we do KB-specific parsing.
		if kb == "do":
			pbar = tqdm(unit=" added")
			statement = "CREATE (a:Disease {name:{name}, kb_id:{kb_id}, source:{source}})"
			with driver.session() as session:
				for entry in kb_rels:
					try:
						session.run(statement, {"name": entry["name"], "kb_id": entry["id"], "source": "Disease Ontology"})
						pbar.update(1)
					except KeyError: #Discard this entry
						pass
			pbar.close()
			
		# if kb == "mo":
			# pbar = tqdm(unit=" added")
			# for entry in kb_rels:
				# tx = graph.begin()
				# node1 = Node("Concept",name=entry["id"])
				# tx.create(node1)
				# tx.commit()
				# pbar.update(1)
			# pbar.close()
			
		# if kb == "sl":
			# pbar = tqdm(unit=" added")
			# for entry in kb_rels:
				# tx = graph.begin()
				# node1 = Node("Concept",name=entry["entry"])
				# tx.create(node1)
				# tx.commit()
				# pbar.update(1)
			# pbar.close()
		
		i = i+1
		if i == len(KB_NAMES):
			status = True
		
	return status
