import logging

from typing import *

from parser.base_parser import TestCase
# logging.basicConfig(filename='log.log',
#                             filemode='a',
#                             format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
#                             datefmt='%H:%M:%S',
#                             level=logging.DEBUG)
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

if __name__ == '__main__':
    from utils.custom_argument_parser import CustomArgumentParser
    from api_manager.ES_manager import ESManager
    from api_manager.artifact_manager import ArtifactManager
    from parser.xml_parser import XMLParser
    from parser.generated_test_parser import GeneratedTestParser
    from utils.untested_generator import UntestedGenerator
    from version import __version__
    import os

    # region Parser
    parser = CustomArgumentParser(description='retrieve datas from artifact and process them')
    
    parser.add_argument('-v', '--version', action='version', help='display the current version in ./version.py', version=f'%(prog)s {__version__}')

    # Artifact Argument
    parser = ArtifactManager.add_arguments(parser)

    # Elastic Search Argument
    parser = ESManager.add_arguments(parser)
    
    # parser argument
    parser = XMLParser.add_arguments(parser)
    parser = GeneratedTestParser.add_arguments(parser)

    # test file argument
    parser = UntestedGenerator.add_arguments(parser)

    args = parser.parse_args()
    # endregion

    # region initialisation
    # create the ArtifactManager
    artifact_manager = ArtifactManager.create_from_args(args)
    # create ES manager
    es = ESManager.create_from_args(args)

    # test file
    test_file = UntestedGenerator.create_from_args(args)

    # parser
    generated_test_parser = GeneratedTestParser.create_from_args(args)
    xml_parser = XMLParser.create_from_args(args)

    settings = xml_parser.settings

    # endregion

    index_name = 'artifact'
    es.create_or_update_index(index_name, {
        'properties': {
            field: value for field, value in settings['default_test_data'].items()
        }
    })
    already_run_artifact = list(map(lambda bucket: bucket['key'] , es.aggregate(['artifact_name'])['aggregations']['artifact_name']['buckets']))

    testcase_generators: Iterable[Iterable[TestCase]] = artifact_manager.get_all_tests(xml_parser, already_run_artifact)
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
    for success, info in es.bulk_upload(index_name, testcase_generator):
        if not success:
            log.warning('failed to store: ', info)