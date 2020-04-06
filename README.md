# TUBDUCK

TUBDUCK is a system and accompanying platform for Translating Unstructured Biomedical Data into Unified, Coherent 
Knowledgebases. 

It renders experimental and clinical text as graphs, for integration into a knowledge graph. 

TUBDUCK is designed to be domain-sensitive, particularly for cardiovascular disease research and cardiovascular clinial case reports.

TUBDUCK is a work in progress.

TUBDUCK is designed for Linux only at this time.

## Requirements

1. Install all requirements first as:

    `pip3 install -r requirements.txt`

2. Set up a Neo4j server. This can be done locally or remotely (option *a* or option *b*).

    *a)* Install Neo4j - Community Server works well.  See https://neo4j.com/download-center/#community for distribution-specific instructions. Note that Neo4j requires one of the following Java runtimes: Oracle(R) Java 8, OpenJDK, or IBM J9. On Ubuntu and other Debian distributions, Neo4j installation goes like this:

    `wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -`

    `echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list`

    `sudo apt-get update`

    `sudo apt-get install neo4j`

    Once installation is complete, start the Neo4j server:
    
    `sudo systemctl start neo4j`

    Set the username and password through the browser (usually accessible at http://localhost:7474/) beforehand: login the first time with "neo4j" and "neo4j", as username and password, respectively. Keep the username as "neo4j" but specify a new password. Then specify the password though its environment variable by running this:

    `export NEO4J_PASSWORD="admin"`

    *b)* Set up a remote Neo4j database instance. 
    
    This can be done through the Neo4j Sandbox (https://neo4j.com/sandbox-v2). Once you've signed in and started a blank sandbox, set the following environment variables on the client (i.e., the machine you are running TUBDUCK on):

    `export NEO4J_PASSWORD="some-random-password"`

    `export NEO4J_HOST="ip.address.goes.here"`

    `export NEO4J_PORT=12345` - note the lack of quotes
    
    Amazon Web Services also provides Amazon Machine Images (AMIs) for Neo4j Community Edition: see https://aws.amazon.com/marketplace/pp/Neo4j-Neo4j-Graph-Database-Community-Edition/B071P26C9D
    
    Or, if you would prefer to use the Google Cloud Platform, there are instructions for that here: https://neo4j.com/developer/neo4j-cloud-google-image/
    
    Irrespective of the remote platform used, environment variables will need to be specified as above so TUBDUCK knows how to connect to the database.

## Running the first time

Run TUBDUCK as follows from its root directory:

`./tubduck.sh`

## Troubleshooting

### Neo4j authentication issues

When setting up the Neo4j database, it may raise an error like *Neo.ClientError.Security.Unauthorized: The client is unauthorized due to authentication failure.* Ensure you've set up the initial password as described above. Otherwsie, stop the server and remove any previously existing database(s) as follows:

`sudo systemctl stop neo4j`

`sudo rm -rf /var/lib/neo4j/data/`

Then restart the Neo4j server as above.

🛁🦆
