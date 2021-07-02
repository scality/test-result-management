from api_manager.ES_manager import ESManager
from api_manager.base_manager import BaseManager
from utils.untested_generator import UntestedGenerator
from unittest.mock import Mock, patch
from unittest import TestCase

class TestUntestedGenerator(TestCase):
    @patch('api_manager.ES_manager.ESManager')
    @patch('api_manager.base_manager.BaseManager')
    def setUp(self, mock_es_manager, base_manager):
        self.mocked_es_manager = mock_es_manager
        self.base_manager = base_manager
        BaseManager.auth = Mock(return_value=True)
        self.tests_tree = {
            'ring': {
                '8.5': {},
                '7.4': {},
            },
            'repo': {
                'version1': {},
                'version2': {}
            }
        }
        self.untested_generator = UntestedGenerator('http://fakeurl')
        self.untested_generator.aggregation_list = ['repo', 'version']
        self.untested_generator.aggregation_list_common_data_length = 1
        self.untested_generator.common_key = ['repo']
        self.untested_generator.key_to_generated_data = ['version']
        self.untested_generator.constant_keys= ['data_url']

        self.tests_tree = {
            'ring': {
                '8.5': {},
                '7.4': {},
            },
            'repo': {
                'version1': {},
                'version2': {}
            }
        }
        self.constant_data = {'data_url': 1}
    def test_recreating_test(self):
        missing_keys = ['repo', 'version']
        result_list = [
            ({'data_url': 1, 'repo': 'ring', 'version': '8.5'}, 1),
            ({'data_url': 1, 'repo': 'ring', 'version': '7.4'}, 1),
            ({'data_url': 1, 'repo': 'repo', 'version': 'version1'}, 1),
            ({'data_url': 1, 'repo': 'repo', 'version': 'version2'}, 1),
        ]
        self.assertCountEqual(list(self.untested_generator.recreate_test(self.tests_tree, self.constant_data, missing_keys)), result_list)
    def test_recreating_test_one_depth(self):
        tests_tree = self.tests_tree['ring']
        result_list = [
            ({'data_url': 1, 'repo': 'ring', 'version': '8.5'}, 1),
            ({'data_url': 1, 'repo': 'ring', 'version': '7.4'}, 1),
        ]
        constant_datas = {**self.constant_data, **{'repo': 'ring'}}
        missing_keys = ['version']
        self.assertCountEqual(list(self.untested_generator.recreate_test(tests_tree, constant_datas, missing_keys)), result_list)
    def test_find_tree_for_tuple(self):
        tuple = ('ring',)
        
        result = self.tests_tree['ring']
        self.assertDictEqual(self.untested_generator.find_tests_tree_for_tuple(self.tests_tree, tuple), result)

    def test_missing_test(self):
        tests_tree = {
            'repo2': {
                'version1': {},
                'version2': {}
            }
        }
        tests_tree.update(self.tests_tree)
        tuples = {('ring',),('repo',)}
        
        result_list = [
            ({'data_url': 1, 'repo': 'ring', 'version': '8.5'}, 1),
            ({'data_url': 1, 'repo': 'ring', 'version': '7.4'}, 1),
            ({'data_url': 1, 'repo': 'repo', 'version': 'version1'}, 1),
            ({'data_url': 1, 'repo': 'repo', 'version': 'version2'}, 1),
        ]
        self.assertCountEqual(list(self.untested_generator.missing_test(tuples, tests_tree, self.constant_data)), result_list)
    
    def test_decorate_with_missing_testcase(self):
        self.untested_generator.create_tests_tree = Mock(return_value={**self.tests_tree})
        def testcase_generator():
            yield {'data_url': 1, 'repo': 'ring', 'version': '8.5'}
            yield {'data_url': 1, 'repo': 'repo', 'version': 'version1'}
        class dummy_parser:
            def parse(self, data, data_url):
                return data
        
        result_list = [
            {'data_url': 1, 'repo': 'ring', 'version': '8.5'},
            {'data_url': 1, 'repo': 'ring', 'version': '7.4'},
            {'data_url': 1, 'repo': 'repo', 'version': 'version1'},
            {'data_url': 1, 'repo': 'repo', 'version': 'version2'},
        ]
        self.assertCountEqual(list(self.untested_generator.decorate_with_missing_testcase(testcase_generator(), dummy_parser())), result_list)
        
