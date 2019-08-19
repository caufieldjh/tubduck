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
TBD:
Add test loading mode, as loading even DO+MeSH+ICD10 takes most of an hour.
  Some of this may just require some optimization.
  I've already fought with that for a bit,
  but it seems like preparing nodes as a list and then using UNWIND
  is more efficient than single operations.

Then, cross-link the ontologies where possible to find identical terms (via xlinks, like those in DO).
Finally, load at least one CCR into the DB and attempt to link it to the concept graph.
Add more material to concept graph (Reactome pathways and constituent proteins).
Load and add baseline instance graph material (IntAct PPI).
Make it accessible! As a prototype.
'''

import os
import random
import subprocess
import sys
import time
#import resource #for raising open file limits as per Neo4j

import ast

from bs4 import BeautifulSoup

from urllib.request import urlopen
import urllib.error

from pathlib import Path
from tqdm import *

from neo4j import GraphDatabase
import neobolt.exceptions

## Constants
TOTAL_KBS = 4 #The total count of knowledge bases we'll use
				#To be specified in more detail later
WORKING_PATH = Path('../working')
KB_PATH = Path('../working/kbs')
KB_PROC_PATH = Path('../working/kbs/processed')

KB_NAMES = {"don": "doid.obo",		#The set of all knowledge bases,
				"m19": "d2019.bin",  #with three-letter codes as keys.
				"i10": "icd10cm_tabular_2019.xml",
				"i11": "simpletabulation.xlsx"
					}

## Functions
def setup_checks(tasks):
	'''Check to see which setup steps need to be completed.
		This is primarily based on what files already exist.
		Returns list of strings, where each item denotes a task to 
		be completed before proceeding.
		The user may have specified some additional tasks to complete.'''
		
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
		if "empty_db" in tasks:
			sys.exit("Empty database requested but DB does not exist. Exiting...")
		setup_list.append("set up graph DB")
		if "test_load_db" in tasks:
			setup_list.append("populate graph DB as test")
		else:
			setup_list.append("populate graph DB")
		graph_exists = False
	
	if graph_exists:
		gdb_vals = graphdb_stats()
		if "test_load_db" in tasks:
			print("Requested to load a test set but DB already populated.")
		if gdb_vals["rel_count"] < 2:
			if "test_load_db" in tasks:
				setup_list.append("populate graph DB as test")
			else:
				setup_list.append("populate graph DB")
		if "empty_db" in tasks:
			setup_list.append("empty graph DB")

	return setup_list
	
def setup(setup_to_do):
	'''Main setup function. Calls other functions for some other tasks.
		Takes list as input.
		Returns True if setup encounters no errors.'''
		
	setup_all = True #Default is to set up everything
	status = True
	kb_codes = KB_NAMES.keys() #Knowledge bases each get code
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
		for kb in kb_codes:
			if KB_NAMES[kb] not in kb_files:
				need_kb_files.append(kb)
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
		for kb in KB_NAMES:
			filename = KB_NAMES[kb]
			newfilename = (str(filename.split(".")[0])) + "-proc"
			if newfilename not in kb_proc_files:
				need_kb_proc_files.append(kb)
		kb_proc_codes = need_kb_proc_files
		if not process_kbs(kb_proc_codes,KB_PATH,KB_PROC_PATH):
			print("Encountered errors while processing knowledge base files.")
			status = False
		
	if "set up graph DB" in setup_to_do:
		if not create_graphdb():
			print("Encountered errors while setting up graph database.")
			sys.exit() #Shouldn't continue in this case
	
	if "populate graph DB" in setup_to_do or "populate graph DB as test" in setup_to_do:
		if "populate graph DB as test" in setup_to_do:
			test_only = True
		else:
			test_only = False
		if not populate_graphdb(test_only):
			print("Encountered errors while populating graph database.")
			status = False
		if not crosslink_graphdb():
			print("Encountered errors while adding cross-links to graph database.")
			status = False
	
	if "empty graph DB" in setup_to_do:
		if not empty_graphdb():
			print("Encountered errors while emptying graph database.")
			status = False
			
	return status
	
def get_kbs(names, path):
	'''Retrieves knowledge bases in their full form from various remote 
	locations. 
	Takes a list of two-letter codes as input.
	Also requires a Path where they will be written to.'''
	
	data_locations = {"don": ("http://ontologies.berkeleybop.org/","doid.obo"),
					"m19": ("ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/asciimesh/","d2019.bin"), 
					"i10": ("ftp://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2019/", "icd10cm_tabular_2019.xml"),
					"i11": ("https://icd.who.int/browse11/Downloads/", "Download?fileName=simpletabulation.zip")
					}
	
	filenames = []
	status = True #Becomes False upon encountering error
	
	for name in names:
		baseURL, filename = data_locations[name]
		filepath = baseURL + filename
		if name in ["i11"]:	#ICD-11 has a specific access procedure for now
			outfilepath = path / (filename.split("="))[1]
		else:
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
	Takes a list of kb codes as input.
	Also requires a Path to the folder where they are AND where they
	should go once processed.'''
	
	status = True
	
	#Processing methods are KB-specific as formats vary
	for name in names:
		if name == "don":
			if process_diseaseontology(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		if name == "m19":
			if process_mesh(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		if name == "i10":
			if process_icd10cm(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		if name == "i11":
			if process_icd11mms(KB_NAMES[name], inpath, outpath):
				pass
			else:
				status = False
		else:
			pass
	
	return status

def process_diseaseontology(infilename, inpath, outpath):
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

def process_mesh(infilename, inpath, outpath):
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
					if text[0].strip() in ["RECTYPE","MH","AQ","ENTRY","MN","PA","UI"]:
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
	
def process_icd10cm(infilename, inpath, outpath):
	'''Processes 2019 release of ICD-10-CM into relationship format.
	Takes input from process_kbs.
	The input file is the "tabular" version in XML format.
	Uses the hierarchy to form is_a relations.
	It's a bit messy as that involves lookback.
	Doesn't assign chapter membership yet.'''
	
	status = True
	
	infilepath = inpath / infilename
	newfilename = (str(infilename.split(".")[0])) + "-proc"
	outfilepath = outpath / newfilename
	print("Processing %s." % infilename)
	try:
		pbar = tqdm(unit=" entries")
		with infilepath.open() as infile:
			contents = infile.read()
			soup = BeautifulSoup(contents,'xml')
			diags = soup.find_all('diag')
			with outfilepath.open("w") as outfile: 
				for diag in diags:
					cont = diag.contents
					name = cont[1].contents
					desc = cont[3].contents
					
					parent_diag = diag.parent
					parent_cont = parent_diag.contents
					parent_name = parent_cont[1].contents
					
					entry = {'id':name, 'name':desc, 'is_a':parent_name}
					outfile.write(str(entry) + "\n")
					pbar.update(1)
		pbar.close()
	except IOError as e:
		print("Encountered an error while processing %s: %s" % (infilename, e))
		status = False

	return status
	
def process_icd11mms(infilename, inpath, outpath):
	'''Processes 2019 release of ICD-11-MMS into relationship format.
	Takes input from process_kbs.
	The input file is a ZIP-compressed XLSX file.
	Uses the hierarchy to form is_a relations.
	
	Next steps - 
	1. Unzip (helper)
	2. Convert from XLSX to TSV (helper)
	3. Process (see other script)
	'''
	
	status = True
	
	infilepath = inpath / infilename
	newfilename = (str(infilename.split(".")[0])) + "-proc"
	outfilepath = outpath / newfilename
	print("Processing %s." % infilename)
	try:
		pbar = tqdm(unit=" entries")
		with infilepath.open() as infile:
			contents = infile.read()
			soup = BeautifulSoup(contents,'xml')
			diags = soup.find_all('diag')
			with outfilepath.open("w") as outfile: 
				for diag in diags:
					cont = diag.contents
					name = cont[1].contents
					desc = cont[3].contents
					
					parent_diag = diag.parent
					parent_cont = parent_diag.contents
					parent_name = parent_cont[1].contents
					
					entry = {'id':name, 'name':desc, 'is_a':parent_name}
					outfile.write(str(entry) + "\n")
					pbar.update(1)
		pbar.close()
	except IOError as e:
		print("Encountered an error while processing %s: %s" % (infilename, e))
		status = False

	return status

def create_graphdb():
	'''Sets up an empty Neo4j database.
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
	
	try:
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
		
	except (neobolt.exceptions.DatabaseError, neobolt.exceptions.AuthError) as e:
		print("**Encountered an error in Neo4j graph DB setup: %s" % e)
		print("**Please try accessing the server at http://localhost:7474/")
		print("**The default username is \"neo4j\" and the password is \"neo4j\".")
	
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
	
def populate_graphdb(test_only):
	'''Loads entities and relations into graph DB from processed KBs.
	Most of these form the concept graph: they define conceptual
	relationships, including "is a" relationships.
	Initial contents of the instance graph are also included: these
	relationships correspond to reported events within text, e.g.,
	symptoms or diagnostics reported within clinical case reports.
	The input variable test_only is a boolean; if True, a maximum of 100
	nodes will be populated from each source.
	Returns True if all population activities complete without error.'''
	
	status = False
	
	driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tubduck"))
	
	max_node_count = 1000000 #The total number of nodes to create based on a single KB source.
	if test_only:
		max_node_count = 100
	
	print("Populating graph DB...")
	
	#Load each KB as nodes/relations.
	#Note that not every dict entry includes a valid relation.
	j = 0
	for kb in KB_NAMES:
		kb_rels = []
		infilename = KB_NAMES[kb].split(".")[0] + "-proc"
		print("Loading entries from %s..." % infilename)
		infilepath = KB_PROC_PATH / infilename
		with infilepath.open('r') as infile:
			
			for count, line in enumerate(infile): #Get linecount first
				pass
			linecount = count + 1
			print("File contains %s items." % linecount)
			infile.seek(0)
			
			i = 0
			if test_only:	#Jump ahead randomly if testing
				try:
					for _ in range(random.randint(1,linecount-100)):
						next(infile)
				except StopIteration as e:
					break
				pbar = tqdm(unit=" entries", total = max_node_count)
			else:
				pbar = tqdm(unit=" entries", total = linecount)
			for line in infile: #Go line-by-line to be careful
				kb_rels.append(ast.literal_eval(line.rstrip()))
				i = i+1
				pbar.update(1)
				if i == max_node_count:
					break
		pbar.close()
		
		print("Loading relevant nodes and relations into graph DB...")
		# Now we do KB-specific parsing.
		if kb == "don":
			pbar = tqdm(unit=" nodes added")
			statement = "MERGE (a:Disease {name:{name}, kb_id:{kb_id}, source:{source}})"
			with driver.session() as session:
				i = 0
				for entry in kb_rels:
					try:
						name1 = entry["name"][0]
						kb_id1 = entry["id"][0]
						session.run(statement, {"name": name1, "kb_id": kb_id1, "source": "Disease Ontology"})
						if "is_a" in entry.keys():
							targets = entry["is_a"] #May be multiple relationships
							for target in targets:
								kb_id2 = (target.split("!")[0]).strip()
								session.run("MATCH (a:Disease {kb_id: $kb_id1}), (b:Disease {kb_id: $kb_id2}) "
										"MERGE (a)-[r:is_a]->(b)", kb_id1=kb_id1, kb_id2=kb_id2)
						i = i+1
						pbar.update(1)
						if i == max_node_count:
							break
					except KeyError: #Discard this entry
						pass
			pbar.close()
			
		if kb == "m19":
			'''Some nodes are added more than once if they have multiple
			MN codes (this means they occupy multiple places in the
			MeSH tree. Is_a relations are based on MN as well, 
			as we don't always know the corresponding entry.'''
			pbar = tqdm(unit=" entries added")
			statement = "MERGE (a:Concept {name:{name}, kb_id:{kb_id}, mesh_tree_number:{mesh_tree_number}, source:{source}})"
			with driver.session() as session:
				i = 0
				for entry in kb_rels:
					try:						
						name1 = entry["MH"][0]
						kb_id1 = entry["UI"][0]
						if "MN" in entry.keys():
							for item in entry["MN"]: #Position in the MeSH tree - may have >1
								session.run(statement, {"name": name1, "kb_id": kb_id1 , "mesh_tree_number": item ,"source": "MeSH 2019"})
								mn_split = item.split(".")
								if len(mn_split) >1: #If this isn't a parent term/code already
									mn_parent = ".".join(mn_split[:-1])
									session.run("MATCH (a:Concept {mesh_tree_number: $mn1}), (b:Concept {mesh_tree_number: $mn2}) "
										"MERGE (a)-[r:is_a]->(b)", mn1=item, mn2=mn_parent)
						if "PA" in entry.keys():
							for item in entry["PA"]: #Pharmacologic Action - only present for subset
								name2 = item
								session.run("MATCH (a:Concept {name: $name1}), (b:Concept {name: $name2}) "
										"MERGE (a)-[r:has_pharmacologic_action]->(b)", name1=name1, name2=name2)
						i = i+1
						pbar.update(1)
						if i == max_node_count:
							break
					except KeyError: #Discard this entry
						pass
			pbar.close()
			
		if kb == "i10":
			pbar = tqdm(unit=" nodes added")
			statement = "MERGE (a:Disease {name:{name}, kb_id:{kb_id}, source:{source}})"
			with driver.session() as session:
				i = 0
				for entry in kb_rels:
					try:
						name1 = entry["name"][0]
						kb_id1 = entry["id"][0]
						session.run(statement, {"name": name1, "kb_id": kb_id1, "source": "ICD-10-CM 2019"})
						if "is_a" in entry.keys(): #All codes have one parent at most
							kb_id2 = entry["is_a"][0]
							session.run("MATCH (a:Disease {kb_id: $kb_id1}), (b:Disease {kb_id: $kb_id2}) "
										"MERGE (a)-[r:is_a]->(b)", kb_id1=kb_id1, kb_id2=kb_id2)
						i = i+1
						pbar.update(1)
						if i == max_node_count:
							break
					except KeyError: #Discard this entry
						pass
			pbar.close()
		
		j = j+1
		if j == len(KB_NAMES):
			status = True
		
	return status

def crosslink_graphdb():
	'''Adds cross-link relations to the graph DB.
	Needs to happen after population as cross-link targets may not
	exist yet otherwise.
	Returns True if completed without errors.'''
	status = False
	
	driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tubduck"))
	
	print("Adding cross-links to graph DB...") #Doesn't do anything yet
	status = True 
	
	return status

def empty_graphdb():
	'''Clears all entities and relations from the graph DB.
	Returns True if it completes without error.'''
	
	status = False
	
	driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tubduck"))
	
	print("Will empty all contents from graph DB.")
	print("Please note that the database can be removed entirely by "
			"stopping Neo4j and deleting the graph.db file.")
	print("Clearing all contents from graph DB...")
	
	with driver.session() as session:
		session.run("MATCH ()-[r]-() DELETE r")
		session.run("MATCH (n) DELETE n ")
	
	print("Complete.")
	status = True
		
	return status
