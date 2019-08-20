#!/usr/bin/python
#tubduck_helpers.py
'''
General purpose helper functions for TUBDUCK.
'''

from zipfile import ZipFile
import xlrd
import csv

def decompress(filepath, outpath):
	'''Takes a Path filename of a compressed file
		and the intended output path as input.
		Decompresses to same path.
		Doesn't have a return.
		Just for ZIP compression for now but will handle all
		necessary formats.'''
	
	with ZipFile(filepath, 'r') as zip_ref:
		zip_ref.extractall(outpath)
		
def convert_xlsx_to_tsv(filepath, tabfilepath):
	'''Converts an Excel spreadsheet file (XLSX) to TSV.
	No return here.
	Takes a Path filename of the input file
		and the intended output file path as input.'''
	
	with open(tabfilepath, 'w') as outfile:
		writer = csv.writer(outfile, delimiter="\t")
		xlsfile = xlrd.open_workbook(filepath)
		sheet = xlsfile.sheet_by_index(0)
		for rownum in range(sheet.nrows):
			writer.writerow(sheet.row_values(rownum))
	
