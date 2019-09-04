#!/usr/bin/python

import sys
from flask import Flask, escape, request, jsonify
#from ariadne import load_schema_from_path

#schema = load_schema_from_path("../../schemas/schema.graphql")

def create_app():
	app = Flask(__name__)
    
	@app.route('/')
	def home():
		text = "\U0001F6C1\U0001F986"
		return text
		
	@app.route('/test')
	def test():
		text = "test"
		return text
	
	@app.errorhandler(404)
	def page_not_found(e):
		return jsonify({'message': 'The requested URL was not found on the server.'}), 404

	return app
