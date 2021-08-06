# SETUP
The project is supposed to be build from the harbor registry, using a github action.

but you can run it locally, either with a working python3 and pip installation or with a working docker :
python3/pip :
```bash
# not mandatory but recommended, virtual env usage :
python3 -m venv venv
. venv/bin/activate

# installation of the dependency
pip install -r requirements.txt

# see ren_script_example.py or --help for information about how to run the script
```
Docker :
```bash
# building the docker image
docker build . --tag test

# running the container
docker run test --help
```    

# FEATURES
- Transfer tests from artifact to elasticsearch
- Generate possibly missing tests that should've run
- Can try to fail softly when parsing tests
- Have an option to test what will be sent to elastic before actually sending it

# MODULES

## api manager
Contains the 'manager' for interaction with API, like artifact or ES.

## test parsers
Allow the parsing of the testcase and returning tests in a defined format : cf 'default test data' in setting file


## ES Query
Create and read request / response from ES by creating an AST and, imho, simplifying the reading of the queries

## UTILS - untested generator
Handle the creation of untested testcase
it get all previously run testcase from ES (last 15 days and with a status) and then create them from the test present in artifact

## UTILS - Instanciable
Every object that inherit from this class is supposed to be instantiable from command line

## transfer artifact to es.py
the actual main of the program, will initialize the different modules with command lines arguments
and run them in order to get the tests from artifact and then transfer them to ES (including un-tested testcase)

    - arguments parser
    - download from artifact
    - add test from unntested generator
    - upload all test to ES

# New project to be uploaded to elastic

Depending on how the tests in the project are generated,
It can be as easy as creating a setting file from example_setting.json
Or creating a custom parsing class to be able to parse the testfiles.

if the tests are formatted in an already parsed format (junit for example) it should be straight forward :
- create a setting file from `example_setting.json`
- file in how it should parse the url, the different section, maybe blacklist some file (in ring, there is some symlink)
- setup wich file contain tests and wich parser to be used for them (using regexp, trying to be specific since testfile can be parsed multiple time if regexp overlaps)
- test with a dry-run option to avoid sending test to elastic, it should display an exemple of what tests are found and how it's going to be sent to ES

if the tests aren't in an already parsed format or some datas aren't beiing picked up.
it will require creating a new parser on the BaseParser class.
In theory it should implement `parse_file` method, it is the method called by managers to parse any given file.
And this `parse_file` method should yield what is returned by `parse` method.
It ensure all fields are present and add test_date, upload date and other generated field.

What might go wrong :
- every field in default_test_data should be in every tests sent to elastic, if there is one missing, the parser will output what is missing and skip the test
- to have more debug information, you can change the logging level to INFO

# Improvement
- have multiple elasticsearch index
- the default_test_data must stay the same accross all indexes, so it should not be in the config file, or at least not in this config file per repo since it should be the same accross all repos (or have different indexes per repo)
- maybe be a little more flexible about what datas are sent to elastic (instead of undefined when there is no OS, maybe just accept a tests without OS ? for example)

