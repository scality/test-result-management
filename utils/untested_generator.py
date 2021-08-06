from datetime import timedelta, datetime
from parser.generated_test_parser import GeneratedTestParser
from ES_query.AST import Aggs, Bool, FilterTerms, MasterNode, Must, MustNot, Query, Range, Terms, Variable, AST
import logging

from typing import *

from api_manager.ES_manager import ESManager
from parser.base_parser import TestCase, TestCaseCandidate
log = logging.getLogger(__name__)
TestTree = dict
class UntestedGenerator:
    def __init__(self, elastic_manager: ESManager):
        """
        initialize UntestedGenerator
        """
        self.elastic_manager = elastic_manager

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
        
    def _create_aggregation(self, aggregation_list: List[str]) -> AST:
        """
        create ES aggregation recursively to group tests together
        params: aggregation_list: list of string that match the field in the elastic base
        return : dictionnary matching elastic syntax to have imbricated aggregation 
        ex : aggregation_list==['a', 'b']
            return Aggs(Variable('a', Terms('a'),
                        Aggs(Variable('b', Terms('b'))
        """
        field = aggregation_list[0]
        if len(aggregation_list) > 1:
            return Aggs(Variable(field, Terms(field), self._create_aggregation(aggregation_list[1:])))
        else:
            return Aggs(Variable(field, Terms(field)))

    def create_tests_tree(self, test) -> TestTree:
        """
        retrieve from elasticSearch the tests with the same repo, milestone and merge_step as the given test
        return a testtree like that :
        test == {'repo': 'ring', 'milestone': '8.5', 'merge_step': 'post-merge', ....}
        self.aggregation_list == repo, milestone, merge-step, section....
        return {
            'ring': {
                '8.5': {
                    'post-merge': {
                        'section1': {
                            ...
                        },
                        'section2': {
                            ...
                        }
                        'section3': {
                            ....
                        }
                    }
                }
            }
        }
        with an aggregation of tests following the aggregation list
        """
        aggregation_common_key = ['repo', 'milestone', 'merge_step']
        query = Bool(
            Must( # have the same repo, milestone, merge_step and be less than 15 days old
                Range("test_date", datetime.now() - timedelta(days=15), datetime.now()),
                *[
                    FilterTerms(key, test[key]) for key in aggregation_common_key if key in test
                ]
            ),
            MustNot( # be a untested test
                FilterTerms("status_value", -1)
            )
        )
        ast = MasterNode(
            self._create_aggregation(self.aggregation_list),
            Query(query)
        )
        response = self.elastic_manager.search(ast)
        response_without_variable_name = self.remove_variable_name(response)
        return response_without_variable_name

    def remove_variable_name(self, response):
        """
        remove the name of the variable from the response (take 1 key every 2 dictionnary)
        input == {'varname1': {
            'ring':{
                'varname2': {
                    '8.5':{...},
                    '7.4':{...},
                },
            'cloudserver': {...}
        }}
        return {
            'ring': {
                '8.5':{...},
                '7.4':{...}
            },
            'cloudserver': {...}
        }
        """
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
        since it's run, we don't have to upload it as an untested test
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

    def recreate_test(self, selected_tests_tree: TestTree, test_data: dict, missing_key: List[str]) -> Iterable[TestCaseCandidate]:
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
        """
        find the sub test tree for a give tuple
        tests_tree == {
            'ring': {'8.5': {'section1': {...}, 'section2': {...}}, '7.4': {...}},
            'cloudserver': {...}
        }
        tuple == ('ring', '8.5')
        return {
            'section1': {...},
            'section2': {...}
        }
        """
        current_tests_tree: dict = tests_tree
        # follow every paths in set for common keys in test_tree
        for key in tuple:
            current_tests_tree = current_tests_tree[key]
        return current_tests_tree

    def missing_test(self, given_data: Set[Tuple[str,...]], tests_tree: TestTree, constant_data: dict) -> Iterable[TestCaseCandidate]:
        """
        find all missing test by searching through the teststree the given data path
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

    def decorate_with_missing_testcase(self, generator: Iterable[TestCase], parser: GeneratedTestParser) -> Iterable[TestCase]:
        """
        take an iterable and return an iterable with the test hat should've run but havn't
        """
        current_generator_tests_tree: TestTree = None
        given_data: Set[Tuple[str,...]] = set()
        constant_data = {}
        first_test = True
        for testcase in generator:
            if first_test:
                # generate the teststree only once
                current_generator_tests_tree = self.create_tests_tree(testcase)
                first_test = False
            # remove the test from the teststree
            self.remove_test(testcase, current_generator_tests_tree)
            
            yield testcase

            # add the test to given data, it's the path that will be followed by missing_test to recreate them
            given_data.add(tuple(testcase[key] for key in self.common_key))

            # populate constant_data with the constant key of the tests
            constant_data = {key: testcase[key] for key in self.constant_keys}

        try:
            # recreate the missing test
            missing_tests = list(self.missing_test(given_data, current_generator_tests_tree, constant_data))
        except Exception as e:
            # if their is an exception we display it but don't break since it's the untested generator and we must sent all tests really run
            log.error(e)
            raise
        for missing_test, data_url in missing_tests:
            generated_testcase = parser.parse(missing_test, data_url)
            if generated_testcase is None:
                continue
            yield generated_testcase

    def decorate_multiple_generators(self, generators: Iterable[Iterable[TestCase]], parser: GeneratedTestParser) -> Iterable[TestCase]:
        for generator in generators:
            yield from self.decorate_with_missing_testcase(generator, parser)

if __name__ == '__main__':
    import datetime
    import custom_argument_parser
    from pprint import pprint
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


