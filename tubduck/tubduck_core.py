#!/usr/bin/python
#tubduck_core.py
'''
This is the primary file for TUBDUCK.
It is intended to call all submethods as modules.

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

import nltk

import tubduck_helpers, tubduck_start
import tubduck_input, tubduck_process, tubduck_output

## Constants and Options

## Classes

## Functions

## Main
def main():
	must_setup = True
	
	print("*** TUBDUCK ***")
	
	print("Checking to see what setup may be required.")
	if must_setup:
		print("Performing intial setup.")
		#Run tubduck_start methods here
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

