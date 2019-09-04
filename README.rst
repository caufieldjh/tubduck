TUBDUCK
=======

TUBDUCK is a system and accompanying platform for Translating Unstructured Biomedical Data into Unified, Coherent 
Knowledgebases. 

It renders experimental and clinical text as graphs, for integration into a knowledge graph. 

TUBDUCK is designed to be domain-sensitive, particularly for cardiovascular disease research and cardiovascular clinial case reports.

TUBDUCK is a work in progress.

TUBDUCK is designed for Linux only at this time.

The graph database
-------- 
The primary requirement for this package is Neo4j (both the Python package providing the Bolt driver and the server itself - Community Edition works well).
Please see Neo4j install instructions for your system at https://neo4j.com/download-center/#community.

Note that Neo4j requires one of the following Java runtimes: Oracle(R) Java 8, OpenJDK, or IBM J9. 

Please start the Neo4j server before running TUBDUCK. For a local database, please set the password through the browser (usually accessible at http://localhost:7474/) beforehand, ideally to "admin". You can change the password though the environment variable, e.g. 
``export NEO4J_PASSWORD="admin"``

You can also try out a remote Neo4j database instance through the Neo4j Sandbox (https://neo4j.com/sandbox-v2). Once you've signed in and started a blank sandbox, set the following variables:

``export NEO4J_PASSWORD="some-random-password"``

``export NEO4J_HOST="ip.address.goes.here"``

``export NEO4J_PORT=12345`` - note the lack of quotes



🛁🦆
