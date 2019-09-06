#!/usr/bin/python
#tubduck_start.py
'''
Functions for TUBDUCK to construct all necessary databases and learning
modules. This includes accumulating training data and training the 
modules themselves.
Does not start Neo4j - it must already be running (this is to allow for
a variety of use cases, including local or remote graph DBs).
Does not start the server as that must continue running to be
operational.
'''

import os
import random
import subprocess
import sys
import time
#import resource #for raising open file limits as per Neo4j

import ariadne
import graphql

import ast

from bs4 import BeautifulSoup

from urllib.request import urlopen
import urllib.error

from pathlib import Path
from tqdm import *

from neo4j import GraphDatabase
import neobolt.exceptions

from flask import Flask

import tubduck_helpers as thelp
import tubduck_settings as tsettings

## Constants
TOTAL_KBS = 4 #The total count of knowledge bases we'll use
				#To be specified in more detail later
WORKING_PATH = Path('../working')
KB_PATH = Path('../working/kbs')
KB_PROC_PATH = Path('../working/kbs/processed')
SCHEMA_PATH = Path('../schemas/schema.graphql')

SERVER_LOC = 'http://127.0.0.1:5000/'

KB_NAMES = {"don": "doid.obo",		
				#"m19": "d2019.bin",  
				"i10": "icd10cm_tabular_2019.xml",
				"i11": "simpletabulation.zip"
					}
'''
All knowledge bases to be (potentially) loaded,
with three-letter codes as keys,
and the original, in some cases compressed, files
as values.
'''

NEO4J_HOST=tsettings.NEO4J_HOST
NEO4J_PORT=tsettings.NEO4J_PORT
NEO4J_URI = "bolt://" + NEO4J_HOST + ":" + str(NEO4J_PORT)
NEO4J_USER=tsettings.NEO4J_USER
NEO4J_PASSWORD=tsettings.NEO4J_PASSWORD

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
		else:
			sys.exit("Can't find Neo4j DB or Neo4j not running. Exiting...")
	
	if graph_exists:
		gdb_vals = graphdb_stats()
		if "empty_db" in tasks:
			setup_list.append("empty graph DB")
		if "test_load_db" in tasks:
			print("Requested to load a test set but DB already populated.")
		if gdb_vals["rel_count"] < 2 and "empty_db" not in tasks:
			if "test_load_db" in tasks:
				setup_list.append("populate graph DB as test")
			else:
				setup_list.append("populate graph DB")
		
	setup_list.append("check data and query schema")
	
	setup_list.append("check Flask server")

	return setup_list
	
def setup(setup_to_do):
	'''Main setup function. Calls other functions for some other tasks.
		Takes list as input.
		Returns True if setup encounters no errors.'''
		
	setup_all = True #Default is to set up everything
	status = True
	kb_codes = KB_NAMES.keys() #Knowledge bases each get code
	kb_proc_codes = kb_codes
		
	if "check data and query schema" in setup_to_do:
		if not check_schema():
			print("Encountered errors while loading schema.")
			status = False
	
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
	
	if "empty graph DB" in setup_to_do:
		if not empty_graphdb():
			print("Encountered errors while emptying graph database.")
			status = False
	
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
			
	if "check Flask server" in setup_to_do:
		if not check_server():
			print("Encountered errors while checking on app server - it may not be running.")
			status = False
			
	return status
	
def get_kbs(names, path):
	'''Retrieves knowledge bases in their full form from various remote 
	locations. 
	Takes a list of two-letter codes as input.
	Also requires a Path where they will be written to.'''
	
	data_locations = {"don": ("http://ontologies.berkeleybop.org/","doid.obo"),
					#"m19": ("ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/asciimesh/","d2019.bin"), 
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
		# if name == "m19":
			# if process_mesh(KB_NAMES[name], inpath, outpath):
				# pass
			# else:
				# status = False
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

# def process_mesh(infilename, inpath, outpath):
	# '''Processes MeSH into relationship format.
	# Takes input from process_kbs.'''
	
	# status = True
	
	# infilepath = inpath / infilename
	# newfilename = (str(infilename.split(".")[0])) + "-proc"
	# outfilepath = outpath / newfilename
	# print("Processing %s." % infilename)
	# try:
		# pbar = tqdm(unit=" lines")
		# with infilepath.open() as infile:
			# with outfilepath.open("w") as outfile:
				# entry = {}
				# for line in infile:
					# text = line.strip().split("=",1)
					# if text == ["*NEWRECORD"]: #start new entry for term
						# if len(entry.keys()) > 0: #If we have a previous entry, write it
							# outfile.write(str(entry) + "\n")
						# entry = {}
					# if text[0].strip() in ["RECTYPE","MH","AQ","ENTRY","MN","PA","UI"]:
						# if text[0].strip() in entry.keys(): #Have it already
							# entry[text[0].strip()].append(text[1].strip())
						# else:
							# if text[0].strip() in ["UI"]: #Gotta add prefix for UI
								# entry[text[0].strip()] = ["MESH:" + text[1].strip()]
							# else:	
								# entry[text[0].strip()] = [text[1].strip()]
					# pbar.update(1)
				# if len(entry.keys()) > 0: #Write the last entry
					# outfile.write(str(entry) + "\n")
					
		# pbar.close()
	# except IOError as e:
		# print("Encountered an error while processing %s: %s" % (infilename, e))
		# status = False

	# return status
	
def process_icd10cm(infilename, inpath, outpath):
	'''Processes 2019 release of ICD-10-CM into relationship format.
	Takes input from process_kbs.
	The input file is the "tabular" version in XML format.
	Uses the hierarchy to form is_a relations.
	ICD-10 codes don't come with unique identifiers so we generate one,
	prefixed with the KB's code.'''
	
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
			
			uri_inc = 0
			all_nodes = {}
			
			for diag in diags:
				
				uri = "ICD10CM:" + str(uri_inc)
				uri_inc = uri_inc+1
				
				cont = diag.contents
				code = (cont[1].contents)[0]
				title = (cont[3].contents)[0]
				
				parent_diag = diag.parent
				parent_cont = parent_diag.contents
				parent_code = (parent_cont[1].contents)[0]
				
				#The parent may be a section heading rather than a code,
				#but we'd like to capture those, too, so we do that here
				#It is its own parent for convenience
				if len(parent_code) > 7: #Codes are < 7 chars in ICD-10
					uri = "i10-" + str(uri_inc)
					uri_inc = uri_inc+1
					
					all_nodes[parent_code] = {"uri":uri,"code":"NA","title":title,
										"parent":parent_code} #parent is a code
					
				
				all_nodes[code] = {"uri":uri,"code":code,"title":title,
										"parent":parent_code} #parent is a code
				
				pbar.update(1)
		
		#Now write
		with outfilepath.open("w") as outfile:
			for node in all_nodes:
				parent_id = all_nodes[node]["parent"]
				uriA = all_nodes[node]["uri"]
				codeA = all_nodes[node]["code"]
				titleA = all_nodes[node]["title"]
					
				if parent_id == "None":
					pass
				else:
					uriB = all_nodes[parent_id]["uri"]
					
					entry = {'id':uriA, 'name':titleA, 'code':codeA, 'is_a':uriB}
					outfile.write(str(entry) + "\n")
				
		pbar.close()
	except IOError as e:
		print("Encountered an error while processing %s: %s" % (infilename, e))
		status = False

	return status
	
def process_icd11mms(infilename, inpath, outpath):
	'''Processes 2019 release of ICD-11-MMS into relationship format.
	Takes input from process_kbs.
	The input file is a ZIP-compressed XLSX file.
	Converts to triple form.
	Uses the hierarchy to form is_a relations.
	'''
	
	status = True
	
	infilepath = inpath / infilename
	midfilename = (str(infilename.split(".")[0])) + ".xlsx"
	midfilepath = inpath / midfilename
	tabfilename = (str(infilename.split(".")[0])) + ".tsv"
	tabfilepath = inpath / tabfilename
	newfilename = (str(infilename.split(".")[0])) + "-proc"
	outfilepath = outpath / newfilename
	
	print("Decompressing %s." % infilename)
	thelp.decompress(infilepath, inpath)
	
	print("Processing %s." % midfilename)
	
	thelp.convert_xlsx_to_tsv(midfilepath, tabfilepath)
	
	try:
		with tabfilepath.open() as infile:
			pbar = tqdm(unit=" entries")
			infile.readline() #Skip the header
		
			all_nodes = {}
		
			node_count = -1
			previous_level = 0
			most_recent_id_at_level = {} #levels are keys, node_count is value
			
			for line in infile:
				node_count = node_count +1
				
				splitline = line.split("\t")
				
				uri = (splitline[1].split("/"))[-1]
				if uri in ["other","unspecified"]:
					cleanuri = (splitline[1].split("/"))[-2] + "/" + uri
				else:
					cleanuri = uri
					
				cleanuri = "ICD11MMS:" + cleanuri
				
				chapterno = splitline[9]
				code = splitline[2]
				title = splitline[4]
				
				cleantitle = ""			#The title indicates the level
				level = 0				#But we just want the text in the title
				counting = True
				
				for char in title:		#There are other ways to do this, yes
					if char == "-" and counting:
						level = level +1
					if char not in ["-"," "]:
						counting = False
					if not counting:
						cleantitle = cleantitle + char
						
				cleantitle = cleantitle.lstrip()
				code_and_title = [code,cleantitle]
				
				#Now let's figure out what the parent is.
				#Keep track of the node_count of the previous level was
				if level == 0:
					parent = "None"
				else:
					parent = most_recent_id_at_level[level - 1]
				
				all_nodes[node_count] = {"uri":cleanuri,"code":code,"title":cleantitle,
								"chapter":chapterno,"parent":parent} #parent is a node_count
				
				previous_level = level
				
				most_recent_id_at_level[level] = node_count
				
				pbar.update(1)
			
		#Now write
		with outfilepath.open("w") as outfile:
			for node in all_nodes:
				parent_id = all_nodes[node]["parent"]
				uriA = all_nodes[node]["uri"]
				codeA = all_nodes[node]["code"]
				titleA = all_nodes[node]["title"]
				chapterA = all_nodes[node]["chapter"]
					
				if parent_id == "None":
					pass
				else:
					uriB = all_nodes[parent_id]["uri"]
					codeB = all_nodes[parent_id]["code"]
					titleB = all_nodes[parent_id]["title"]
					chapterB = all_nodes[parent_id]["chapter"]
					
					if codeA == "":
						codeA = "NA"
					if codeB == "":
						codeB = "NA"
					
					#out_string = "%s\t%s\t%s\t%s\tis_a\t%s\t%s\t%s\t%s\t\n" % (uriA, codeA, 
					#												titleA, chapterA, uriB,
					#												codeB, titleB, chapterB)
					entry = {'id':uriA, 'name':titleA, 'code':codeA, 'is_a':uriB}
					outfile.write(str(entry) + "\n")

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
	'''Checks to see if the Neo4j database is available.
	Returns True if it appears to exist, even if it's empty,
	because we don't do anything with the DB here.'''
	
	status = False
	
	try:
		print("Connecting to Neo4j database at %s " % NEO4J_URI)
		driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
		print("Connected to Neo4j database successfully.")
		status = True
	except (neobolt.exceptions.DatabaseError, neobolt.exceptions.AuthError) as e:
		print("** Encountered an error with Neo4j graph DB: %s" % e)
		print("** Check the database password.")
		print("** If this is a new database, you may need to set the password first,")
		print("** then set it as an environment variable like the following:")
		print("** export NEO4J_PASSWORD=\"newpassword\"")
	except	neobolt.exceptions.ServiceUnavailable as e:
		print("** Encountered an error with Neo4j graph DB: %s" % e)
		print("** Please verify that Neo4j is running locally or remotely.")
		
	return status
	
def graphdb_stats():
	'''Gets details about the Neo4j database.
	Returns a dict of values.'''
	
	graphdb_values = {}
	
	driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
	
	with driver.session() as session:
		graph_data = session.run("MATCH ()-->() RETURN count(*)").data()
		
	rel_count = graph_data[0]["count(*)"]
	graphdb_values["rel_count"] = rel_count
	
	if rel_count < 1:
		print("Neo4j database is empty.")
	else:
		print("Neo4j database contains %s relations." % str(graphdb_values["rel_count"]))
	
	return graphdb_values

def check_server():
	'''Check on status of the Flask server.'''
	
	status = False
	
	try:
		urllib.request.urlopen(SERVER_LOC)
		status = True
	except urllib.error.URLError as e:
		print("Error when checking on server: " + str(e))
		status = False
		
	return status
	
def check_schema():
	'''Verifies the GraphQL-defined data and query type schema
	are accessible and formatted correctly.'''
	
	status = False
	
	try:
		schema = ariadne.load_schema_from_path(SCHEMA_PATH)
		status = True
		print("Schema are OK.")
	except (IOError, graphql.error.syntax_error.GraphQLSyntaxError, ariadne.exceptions.GraphQLFileSyntaxError) as e:
		print("Encountered an error while checking on schema: " + str(e))
		status = False
		
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
	
	driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
	
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
			pbar = tqdm(unit=" entries added")
			with driver.session() as session:
				i = 0
				session.run("CREATE CONSTRAINT ON (a:NamedThing) ASSERT a.id IS UNIQUE")
				for entry in kb_rels:
					try:
						name1 = entry["name"][0]
						kb_id1 = entry["id"][0]
						session.run("MERGE (a:NamedThing {id:$id}) "
									"ON CREATE SET a.name = $name, a.creationDate = date() "
									"ON MATCH SET a.name = $name, a.creationDate = date()",
									name=name1, id=kb_id1)
						if "is_a" in entry.keys():
							targets = entry["is_a"] #May be multiple relationships
							for target in targets:
								kb_id2 = (target.split("!")[0]).strip()
								session.run("MERGE (a:NamedThing {id: $id1}) "
										"MERGE (b:NamedThing {id: $id2}) "
										"MERGE (a)-[r:subclassOf {creationDate: date()}]->(b)", id1=kb_id1, id2=kb_id2)
						i = i+1
						pbar.update(1)
						if i == max_node_count:
							break
					except KeyError: #Discard this entry
						pass
			pbar.close()
			
		# if kb == "m19":
			# Not currently used
			# '''Some nodes are added more than once if they have multiple
			# MN codes (this means they occupy multiple places in the
			# MeSH tree. Is_a relations are based on MN as well, 
			# as we don't always know the corresponding entry.'''
			# pbar = tqdm(unit=" entries added")
			# with driver.session() as session:
				# i = 0
				# session.run("CREATE CONSTRAINT ON (a:NamedThing) ASSERT a.id IS UNIQUE")
				# for entry in kb_rels:
					# try:						
						# name1 = entry["MH"][0]
						# kb_id1 = entry["UI"][0]
						# if "MN" in entry.keys():
							# locs = str(entry["MN"])
							# session.run("MERGE (a:NamedThing {id:$id}) "
									# "ON CREATE SET a.name = $name, a.description = $description, a.creationDate = date() "
									# "ON MATCH SET a.name = $name, a.description = $description, a.creationDate = date()",
									# name=name1, id=kb_id1, description=locs)
							# for item in entry["MN"]: #Position in the MeSH tree - may have >1
								# session.run(statement, {"name": name1, "id": kb_id1 , "description": item})
								# mn_split = item.split(".")
								# if len(mn_split) >1: #If this isn't a parent term/code already
									# mn_parent = ".".join(mn_split[:-1])
									# session.run("MERGE (b:NamedThing {description:$mn2}) " #
										# "MERGE (a:NamedThing {description: $mn1})-[r:subclassOf {creationDate: date()}]->(b)", mn1=item, mn2=mn_parent)
						# if "PA" in entry.keys():
							# for item in entry["PA"]: #Pharmacologic Action - only present for subset
								# name2 = item
								# session.run("MERGE (b:NamedThing {name:$name2}) " #Data isn't sorted, so we create other node if needed 
										# "MERGE (a:NamedThing {name: $name1})-[r:subclassOf {creationDate: date()}]->(b)", name1=name1, name2=name2)
						# i = i+1
						# pbar.update(1)
						# if i == max_node_count:
							# break
					# except KeyError: #Discard this entry
						# pass
			# pbar.close()
			
		if kb == "i10":
			pbar = tqdm(unit=" entries added")
			with driver.session() as session:
				i = 0
				session.run("CREATE CONSTRAINT ON (a:NamedThing) ASSERT a.id IS UNIQUE")
				for entry in kb_rels:
					try:
						kb_id1 = entry["id"]
						name1 = entry["name"]
						code1 = entry["code"]
						session.run("MERGE (a:NamedThing {id:$id}) "
									"ON CREATE SET a.name = $name, a.description = $description, a.creationDate = date() "
									"ON MATCH SET a.name = $name, a.description = $description, a.creationDate = date()",
									name=name1, id=kb_id1, description=code1)
						if "is_a" in entry.keys(): #All codes have one parent at most
							kb_id2 = entry["is_a"]
							session.run("MERGE (a:NamedThing {id: $id1}) "
										"MERGE (b:NamedThing {id: $id2}) "
										"MERGE (a)-[r:subclassOf {creationDate: date()}]->(b)", id1=kb_id1, id2=kb_id2)
						i = i+1
						pbar.update(1)
						if i == max_node_count:
							break
					except KeyError: #Discard this entry
						pass
			pbar.close()
		
		if kb == "i11":
			pbar = tqdm(unit=" entries added")
			with driver.session() as session:
				i = 0
				session.run("CREATE CONSTRAINT ON (a:NamedThing) ASSERT a.id IS UNIQUE")
				for entry in kb_rels:
					try:
						kb_id1 = entry["id"]
						name1 = entry["name"]
						code1 = entry["code"]
						session.run("MERGE (a:NamedThing {id:$id}) "
									"ON CREATE SET a.name = $name, a.description = $description, a.creationDate = date() "
									"ON MATCH SET a.name = $name, a.description = $description, a.creationDate = date()",
									name=name1, id=kb_id1, description=code1)
						if "is_a" in entry.keys(): #All codes have one parent at most
							kb_id2 = entry["is_a"]
							session.run("MERGE (a:NamedThing {id: $id1}) "
										"MERGE (b:NamedThing {id: $id2}) "
										"MERGE (a)-[r:subclassOf {creationDate: date()}]->(b)", id1=kb_id1, id2=kb_id2)
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
	
	driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
	
	print("Adding cross-links to graph DB...") #Doesn't do anything yet
	status = True 
	
	return status

def empty_graphdb():
	'''Clears all entities and relations from the graph DB.
	Returns True if it completes without error.'''
	
	status = False
	
	driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
	
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
