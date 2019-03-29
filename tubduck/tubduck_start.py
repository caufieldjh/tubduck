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
