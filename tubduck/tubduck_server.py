#!/usr/bin/python
#tubduck_server.py
'''
Script to run the TUBDUCK webapp.
'''

from tubduck_app import create_app, settings

app = create_app()

if __name__ == '__main__':
    app.run(
        host=settings.BIND_HOST,
        port=settings.BIND_PORT,
        debug=settings.DEBUG,
    )
