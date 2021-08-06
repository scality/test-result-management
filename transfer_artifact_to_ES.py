from ES_query.AST import Aggs, MasterNode, Terms, Variable
import logging
import re
import importlib

from typing import *

from parser.base_parser import TestCase
# logging.basicConfig(filename='log.log',
#                             filemode='a',
#                             format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
#                             datefmt='%H:%M:%S',
#                             level=logging.DEBUG)
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def import_class(name: str) -> object:
    """
    import a class from another file, used to import custom parsers from settings files
    ex: import_class('parser.xml_parser.XMLParser') -> XMLParser object
    """
    components = name.split('.')
    mod = importlib.import_module('.'.join(components[:-1]))
    return getattr(mod, components[-1])

def main():
    from utils.custom_argument_parser import CustomArgumentParser
    from api_manager.ES_manager import ESManager
    from api_manager.artifact_manager import ArtifactManager
    from parser.base_parser import BaseParser
    from parser.generated_test_parser import GeneratedTestParser
    from utils.untested_generator import UntestedGenerator
    from version import __version__
    import os

    # region Parser
    parser = CustomArgumentParser(description='retrieve datas from artifact and process them')
    
    # custom argument
    parser.add_argument('--dry-run',
        help="When this option is set, no test will be send to elastic, only the retrievall of the test will be done",
        action='store_true', default=False
    )
    parser.add_argument('-v', '--version', action='version', help='display the current version in ./version.py', version=f'%(prog)s {__version__}')

    # Artifact Argument
    parser = ArtifactManager.add_arguments(parser)

    # Elastic Search Argument
    parser = ESManager.add_arguments(parser)
    
    # parser argument
    parser = BaseParser.add_arguments(parser)


    args = parser.parse_args()
    # endregion

    # region initialisation
    # create the ArtifactManager
    artifact_manager = ArtifactManager.create_from_args(args)

    # create ES manager
    es = ESManager.create_from_args(args)

    # generator parser
    generated_test_parser = GeneratedTestParser.create_from_args(args)

    settings = generated_test_parser.settings

    # instantiate all the requested parser rom settings file :
    parsers = {}
    for regexp, class_path in settings['parsers'].items():
        if regexp == '_comment':
            continue
        parsers[re.compile(regexp)] = import_class(class_path).create_from_args(args)

    # untested generator
    test_file = UntestedGenerator(es)

    # endregion

    # create or update 'artifact' index into ES
    index_name = 'artifact'
    es.create_or_update_index(index_name, {
        'properties': {
            field: value for field, value in settings['default_test_data'].items()
        }
    })

    if args.dry_run:
        # if we do a dry run, nothing is pushed to elastic so we can re-do already run artifact, it's a debug feature
        already_run_artifact = []
    else:
        # search all artifact already run to elastic
        already_run_artifact = list(es.search(MasterNode(
            Aggs(Variable('artifact_name', Terms('artifact_name')))
        ))['artifact_name'].keys())

    testcase_generators: Iterable[Iterable[TestCase]] = artifact_manager.get_all_tests(parsers, already_run_artifact)
    if os.environ.get('DEBUG'):
        testcase_generators_list: List[List[TestCase]] = [
            [testcase for testcase in testcase_generator]
            for testcase_generator in testcase_generators
        ]
        testcase_list: List[TestCase] = [testcase for testcase_generator_list in testcase_generators_list for testcase in testcase_generator_list]
        testcase_generators = testcase_generators_list
        log.info(f'tests automatically generated : {len(testcase_list)}')
        input('press any key to continue')

    testcase_generators_with_missing_test: Iterable[Iterable[TestCase]] = (generator for generator in (
        test_file.decorate_with_missing_testcase(testcase_generator, generated_test_parser)
        for testcase_generator in testcase_generators
    ))
    testcase_generator: Iterable[TestCase] = (
        testcase for generator in testcase_generators_with_missing_test
        for testcase in generator
    )
    if os.environ.get('DEBUG'):
        testcase_list = list(testcase_generator)
        testcase_generator = (testcase for testcase in testcase_list)
        log.info(f'tests automatically generated : {len(testcase_list)}')
        input('press any key to continue')

    if args.dry_run:
        from pprint import pprint
        testcase_found = list(testcase_generator)
        pprint(testcase_found[:10])
        pprint(len(testcase_found))
    else:
        for success, info in es.bulk_upload(index_name, testcase_generator):
            if not success:
                log.warning('failed to store: ', info)


if __name__ == '__main__':
    main()
