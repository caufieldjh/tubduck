#!/usr/bin/python
#tubduck_core.py
'''
This is the primary file for TUBDUCK.
It is intended to call all submethods as modules.

Requires Python 3.4 or above.

TUBDUCK is a system and accompanying platform for
Translating Unstructured Biomedical Data into Unified, Coherent 
Knowledgebases. It renders experimental and clinical text as graphs,
for integration into a knowledge graph. TUBDUCK is designed to be
domain-sensitive, particularly for cardiovascular disease research
and cardiovascular clinial case reports.
'''
__author__= "Harry Caufield"
__email__ = "jcaufield@mednet.ucla.edu"

import sys

#import nltk

import tubduck_helpers as thelp
import tubduck_start as tstart
import tubduck_input as tinput
import tubduck_process as tproc
import tubduck_output as toutput

## Constants and Options

## Classes

## Functions

## Main
def main():
	
	print("*** TUBDUCK ***")
	
	print("Checking to see what setup may be required.")
	setup_to_do = tstart.setup_checks()
	if len(setup_to_do) > 0:
		print("Performing intial setup for: \n%s" % ("\n".join(setup_to_do)))
		if tstart.setup(setup_to_do):
			print("All setup complete.")
		else:
			sys.exit("Setup did not complete properly.")
	else:
		print("No setup required.")
		
	print("Getting input methods ready.")
	#Run tubduck_input methods
	
	print("Processing...")
	#Run tubduck_process methods
	
	print("Preparing output...")
	#Run tubduck_output methods

if __name__ == "__main__":
	sys.exit(main())

