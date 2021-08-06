import datetime
import logging
import re
import json

from utils.instantiable import Instantiable

from typing import *

log = logging.getLogger(__name__)

TestCase = dict # represent a finished testcase dictionnary
TestCaseCandidate = dict # represent a TestCase that is in construction

class BaseParser(Instantiable):
    instantiable_args = {
        'setting_file': {'help': 'the setting file to use when parsing the xml, contain section name, os....'},
        '--soft-fail': {'help': 'indicate wether or not the parsing will crash or just display errors message', 'action': 'store_true', 'default': False}
    }

    class BaseParserException(Exception):
        def __str__(self):
            return '[BaseParser] ' + super().__str__()

    def __init__(self, setting_file, soft_fail=False):
        if isinstance(setting_file, str):
            with open(setting_file, 'r') as setting_file:
                self.settings = json.load(setting_file)
        else:
            self.settings = setting_file

        self.soft_fail = soft_fail
        self.exceptions_list = []
        self.failed = False
        self.test_date = None

    def parse_file(self, file_content, file_url):
        """
        Virtual method for parsing a given file
        """
        pass
    
    def handle_exception(self, exception: Exception):
        """
        Handle the soft fail parameter and a failed state to return None instead of a half made testcase
        """
        if not self.soft_fail:
            raise exception
        log.error(exception)
        self.exceptions_list.append(exception)
        self.failed = True

    def cross_search(self, containers:List[str], elements:List[str]) -> Optional[str]:
        """
        search in each constainers if one elements is in the container and return this element
        ex:
        containers : ['test', 'thing', 'choose']
        elements : ['a', 'b', 'c']
        test doesn't contain 'a'nor 'b' nor 'c', same for thing
        same goes for thing
        but choose contain 'c' -> return 'c'

        params: containers: the list of string to be tested
        params: elements: the elements to look for in the string
        return: String: the found element (or None)
        """
        for element in elements:
            regexp = re.compile(element)
            for container in containers:
                if element in container:
                    return element
                match = regexp.match(container)
                if match is not None:
                    return match.group(1)
        return None

    def get_status(self, data: TestCaseCandidate) -> Tuple[str, int]:
        """
        get a number for a status in data
        take status_to_value in setting to do a mapping to [str, int]
        the resulting tuple is the status name and value
        """
        status = data.get('status_testcase', None)
        if status is None:
            exc: Exception = BaseParser.BaseParserException(f'key \'status_testcase\' not found in {data}')
            self.handle_exception(exc)
            return ("status_is_undefined", -100)
        status_value = self.settings['status_to_value'].get(status, None)
        if status_value is None:
            exc = BaseParser.BaseParserException(f'key \'{status}\' not found in settings status_to_value')
            self.handle_exception(exc)
            return ("status_is_undefined", -100)
        return status_value

    def parse(self, data: TestCaseCandidate, data_url: str) -> Optional[TestCase]:
        """
        default parsing of a dictionnary to be validated in a TestCase
        - make sure it follow the default testcase given in setting file
        - add status_value from setting file
        - if any error occured, doesn't return the testcase
        """
        log.info(f'parsing test from {data_url}')
        testcase_data: TestCase = {** self.settings['default_test_data']} # create a copy of default setting
        if 'upload_date' in testcase_data:
            data['upload_date'] = datetime.datetime.now()
        if 'test_date' in testcase_data and 'test_date' not in data:
            if self.test_date is None:
                self.handle_exception(BaseException('test_date not set in parser'))
            else:
                data['test_date'] = self.test_date
        if 'build_id' in data:
            data['buildbot_url'] = self.settings['buildbot_base_url'] + data['build_id']
        data['status_testcase'], data['status_value'] = self.get_status(data)
        for key in data:
            if not key in testcase_data:
                exc: Exception = BaseParser.BaseParserException(f'key \'{key}\' not found in settings default_test_data')
                self.handle_exception(exc)
            testcase_data[key] = data[key]

        for key in testcase_data:
            if not key in data:
                exc = BaseParser.BaseParserException(f'key \'{key}\' not found in data but is present in in settings default_test_data')
                self.handle_exception(exc)

        if self.failed:
            self.failed = False
            log.error('unable to retrieve all information for this testcase, skipping')
            log.debug(data)
            return None

        return testcase_data
