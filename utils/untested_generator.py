from ES_query.visitor.interprete_response import ReadData
from ES_query.visitor.ast_to_query import CreateDictionnary
from datetime import timedelta, datetime
from ES_query.AST import Aggs, Bool, FilterTerms, MasterNode, Must, MustNot, Query, Range, Terms, Variable
import logging

from typing import *

from api_manager.ES_manager import ESManager
from parser.base_parser import BaseParser, TestCase
log = logging.getLogger(__name__)
TestTree = dict
class UntestedGenerator(ESManager):
    def __init__(self, elastic_url):
        """
        initialize UntestedGenerator
        """
        super().__init__(elastic_url)
        # the aggregation to do in the tests_tree
        self.aggregation_list = ['repo', 'milestone', 'merge_step', 'section', 'operating_system', 'test_step','classname', 'testname']

        # number of key in tests_tree that are common between tests
        self.aggregation_list_common_data_length = 4

        # the constant keys between each test
        self.constant_keys = [
            "data_url",
            "artifact_name",
            "full_version_name",
            "full_version",
            "commit_date",
            "commit_sha",
            "build_id",
            "buildbot_url",
            "test_date",
            "upload_date",
        ]

        self.common_key = self.aggregation_list[:self.aggregation_list_common_data_length]
        self.key_to_generated_data = self.aggregation_list[self.aggregation_list_common_data_length:]
        
    def create_tests_tree(self, test) -> TestTree:
        aggregation_common_key = ['repo', 'milestone', 'merge_step']
        query = Bool(
            Must(
                Range("test_date", datetime.now() - timedelta(days=15), datetime.now()),
                *[
                    FilterTerms(key, test[key]) for key in aggregation_common_key if key in test
                ]
            ),
            MustNot(
                FilterTerms("status_value", -1)
            )
        )
        ast = MasterNode(
            self._create_aggregation(self.aggregation_list),
            Query(query)
        )
        response = self.search(ast)
        response_without_variable_name = self.remove_variable_name(response)
        return response_without_variable_name

    def remove_variable_name(self, response):
        if response == {}:
            return {}
        ans = {}
        key = list(response.keys())[0]
        for item, value in response[key].items():
            ans[item] = self.remove_variable_name(value)
        return ans
            

    def remove_test(self, test: TestCase, tests_tree: TestTree):
        """
        remove the test from test_tree
        """
        last_aggregation = tests_tree
        for aggregate in self.aggregation_list:
            last_aggregation = tests_tree
            try:
                tests_tree = tests_tree[test[aggregate]]
            except KeyError:
                log.warning(f'TESTFILE: test {test[aggregate]} was not in elastic database')
                return
        else:
            del last_aggregation[test[aggregate]]

    def recreate_test(self, selected_tests_tree: TestTree, test_data: dict, missing_key: List[str]) -> Iterable[Tuple[dict, str]]:
        """
        yield a dict to be parsed into a TestCase with the url of the data
        recursively find leaf in TestTree for missing key and yield each of them with test_data
        """
        if len(missing_key) == 0:
            yield ({**test_data}, test_data['data_url'])
            return None

        for test in selected_tests_tree:
            test_data[missing_key[0]] = test
            yield from self.recreate_test(selected_tests_tree[test], test_data, missing_key[1:])

    def find_tests_tree_for_tuple(self, tests_tree, tuple):
        current_tests_tree: dict = tests_tree
        # follow every paths in set for common keys in test_tree
        for key in tuple:
            current_tests_tree = current_tests_tree[key]
        return current_tests_tree

    def missing_test(self, given_data: Set[Tuple[str,...]], tests_tree: TestTree, constant_data):
        """
        each tuple in gicen_data set translate into a 'path' in the tests_tree
        all leaf of the tests tree, following the path in sets, are considered valid test to be sent
        """
        for tuple in given_data:
            # save common key
            test_data = {
                key: value
                for key, value in zip(self.common_key, tuple)
            }
            # add constant data
            test_data.update(constant_data)
            try:
                current_tests_tree = self.find_tests_tree_for_tuple(tests_tree, tuple)
                yield from self.recreate_test(current_tests_tree, test_data, self.key_to_generated_data)
            except KeyError:
                continue

    def decorate_with_missing_testcase(self, generator: Iterable[TestCase], parser: BaseParser) -> Iterable[TestCase]:
        current_generator_tests_tree: TestTree = None
        given_data: Set[Tuple[str,...]] = set()
        constant_data = {}
        first_test = True
        for testcase in generator:
            if first_test:
                current_generator_tests_tree = self.create_tests_tree(testcase)
                first_test = False

            self.remove_test(testcase, current_generator_tests_tree)
            
            yield testcase
            given_data.add(tuple(testcase[key] for key in self.common_key))
            constant_data = {key: testcase[key] for key in self.constant_keys}

        try:
            missing_tests = list(self.missing_test(given_data, current_generator_tests_tree, constant_data))
        except Exception as e:
            log.error(e)
            raise
        for missing_test, data_url in missing_tests:
            generated_testcase = parser.parse(missing_test, data_url)
            if generated_testcase is None:
                continue
            yield generated_testcase

    def decorate_multiple_generators(self, generators: Iterable[Iterable[TestCase]], parser) -> Iterable[TestCase]:
        for generator in generators:
            yield from self.decorate_with_missing_testcase(generator, parser)

if __name__ == '__main__':
    import datetime
    import custom_argument_parser
    from pprint import pprint
    import json
    from parser.generated_test_parser import GeneratedTestParser

    parser = custom_argument_parser.CustomArgumentParser()
    parser = UntestedGenerator.add_arguments(parser)
    parser = GeneratedTestParser.add_arguments(parser)

    args = parser.parse_args()

    test_file = UntestedGenerator(**UntestedGenerator.create_from_args(args))

    generated_parser = GeneratedTestParser(**GeneratedTestParser.create_from_args(args))
    testcase = {'data_url': 'github:scality:ring:staging-6.4.6.7.r210330072702.27726a5.pre-merge.00115589//robot_framework_others/xunit_report.xml',
            'milestone': '6.4',
            'full_version_name': '6.4.6.7.r210330072702.27726a5', 
            'repo': 'ring',
            'date': datetime.datetime(2021, 3, 30, 7, 27, 2),
            'classname': 'RING.Dewpoint.Ext Batch Delete  Opt  Fs Batch Prefetch',
            'testname': 'dewpoint_batch_delete_invalid',
            'duration': 2.0,
            'section': 'dewpoint',
            'operating_system': 'premerge',
            'test_step': 'premerge',
            'merge_step': 'pre-merge',
            'status_testcase': 'passed',
            'status_value': 5,
            'message': '',
            'text': ''
        }
    def test():
        yield testcase
    for test_ in test_file.decorate_with_missing_testcase(test(), generated_parser):
        pprint(test_)


