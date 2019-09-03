#!/usr/bin/python

from flask import Flask, jsonify
from flask_graphql import GraphQLView
from ariadne import load_schema_from_path

schema = load_schema_from_path("schema.graphql")

def create_app():
    app = Flask(__name__)
    app.add_url_rule('/graphql', view_func=GraphQLView.as_view(
        'graphql', schema=schema, graphiql=True))

    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({'message': 'The requested URL was not found on the server.'}), 404

    return app
