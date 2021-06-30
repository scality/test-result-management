# SETUP
This require a working docker engine :
- build the image using the Dockerfile
- use docker run <image_name> --help to have an overview of the program

# FEATURES
- Transfer the test from artifact to ES
- Create a file containing all tests already transfered in order to mark un-runned test in ES and keep track of them
- Upload all the tests from artifact + tests that have been run previously in ES as untested

# MODULES

every modules is supposed to be self contained and have usecase in the ' if __name__ == "__main__" ' 
some class are supposed to be initialized from the cli and thus, have static helper to add the arguments to argparse
and have a way to be initialized from thoses arguments

## api manager
Contains the 'manager' for interacting with API, like artifact or ES.

## test parser
Allow the parsing of the testcase and returning tests in a defined format : cf 'default test data' in setting file

## untested generator
Handle the creation and of untested testcase
it get all previously run testcase from ES (last 15 days and with a status) and then create them from what test are in artifact

## custom argument parser.py
Allow to keep track of the arguments between the modules and their dependencies
for exemple, test file.py have to create an ESManager to get the testcases and thus, need the argument to create an ESManager
    but if you also need an ESManager to interact with ES, their will be 2 elastic search command line parameter
    thus, the custom_argument_parser prevent from having the same argument twice.

## transfer artifact to es.py
the actual main of the program, will initialize the different modules with command lines arguments
and run them in order to get the tests from artifact and then transfer them to ES (including un-tested testcase)

    - arguments parser
    - download from artifact
    - add test from unntested generator
    - upload all test to ES

