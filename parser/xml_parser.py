import json
import time
import datetime
import re
import logging

import xml.etree.ElementTree as ET

from typing import *

from .base_parser import BaseParser, TestCase, TestCaseCandidate

log = logging.getLogger(__name__)


class XMLParser(BaseParser):
    """
    Used in artifactManager to parse the data and yield dictionnary
    This particular parser is created for the ring, may work for other repo.

    use code reflection to retrieve what xml tags can be parsed
    every method that starts with parse_ while be added to the tag that can be parsed
    """
    class XMLParserException(Exception):
        def __str__(self):
            return '[XMLParser] ' + super().__str__()

    def __init__(self, setting_file, soft_fail=False):
        super().__init__(setting_file, soft_fail)
        self.tag_to_function = self.get_tag_to_function()

    def get_tag_to_function(self) -> Dict[str, Callable]:
        """
        use code reflection to retrieve what xml tags that can be parsed
        every method of the class that begin with parse_ will be retrieved and put in the return dictionnary
        return exemple : {
            'testsuite': self.parse_testsuite,
            'testsuites': self.parse_testsuites,
            'testcase': self.parse_testcase,
        }
        allow to insert new tag to be parsed without modifing the previous method
        """
        # get all attribute that start with parse_
        self_func = filter(lambda name: name.startswith('parse_'), dir(self))
        # only get the method
        self_func = filter(lambda name: callable(getattr(self, name)), self_func)
        # create a dictionnary from method parse_thingtoparse to {'thingtoparse': self.parse_thingtoparse}
        return {name[6:]: getattr(self, name) for name in self_func}

    def parse_file(self, xml_node: str, data_url: str) -> Iterable[TestCase]:
        if type(xml_node) != ET.Element:
            if len(xml_node) == 0:
                log.warning(f"error reading read {data_url}, may be because the xml is empty")
                return []
            try:
                xml_node = ET.fromstring(xml_node)
            except ET.ParseError:
                exc = XMLParser.XMLParserException(f"error reading read {data_url}")
                self.handle_exception(exc)
                return []
        try:
            return self.tag_to_function[xml_node.tag](xml_node, data_url)
        except KeyError:
            exc = XMLParser.XMLParserException(f'xml tag not recognised: {xml_node.tag} in file : {data_url}, possible tags : {self.tag_to_function.keys()}')
            self.handle_exception(exc)
            return []

    def get_test_step(self, melting_pot):
        test_step = self.cross_search(melting_pot, self.settings['test_steps'])
        if test_step is None:
            test_step = 'run_tests'
        return test_step

    def get_section(self, melting_pot):
        section = self.cross_search(melting_pot, self.settings['sections'])
        if section is None:
            exc = XMLParser.XMLParserException(f"can't find section for test '{melting_pot}' in {self.settings['sections']}")
            self.handle_exception(exc)
            return ''
        return section

    def get_operating_system(self, melting_pot):
        operating_system = self.cross_search(melting_pot, self.settings['operating_systems'])
        if operating_system is None:
            return 'undefined'
        return operating_system

    def parse_testcase(self, xml_node_testcase, data_url) -> Optional[TestCase]:
        
        # region data from url, not supposed to fail, should be stored elsewhere tho like in xml node
        artifact_url_match = re.match(self.settings['artifact_url_regexp'], data_url)
        if artifact_url_match is None:
            exc = XMLParser.XMLParserException(f"Failed to parse artifact url, {self.settings['artifact_url_regexp']} doesn't match {data_url}")
            self.handle_exception(exc)
            testcase_data = {}
        else:
            testcase_data: TestCaseCandidate = artifact_url_match.groupdict()
        if 'commit_date' in testcase_data:
            testcase_data['commit_date'] = datetime.datetime.strptime(testcase_data['commit_date'], '%y%m%d%H%M%S')
        # endregion

        # region data from testcase xml node
        testcase_data['classname'] = xml_node_testcase.get('classname', '')
        testcase_data['testname'] = xml_node_testcase.get('name', '')
        testcase_data['duration'] = float(xml_node_testcase.get('time', 0))
        if testcase_data['duration'] == 0:
            testcase_data['duration'] = float(xml_node_testcase.get('duration', 0))
        # endregion

        # region data that's might be in the testname, classname or the data_url
        # where the datas might be contained
        melting_pot = [testcase_data['testname'], testcase_data['classname'], data_url]

        testcase_data['section'] = self.get_section(melting_pot)
        testcase_data['test_step'] = self.get_test_step(melting_pot)
        testcase_data['operating_system'] = self.get_operating_system(melting_pot)

        # endregion
        
        # check all status from the testcase
        for test_result in xml_node_testcase:
            testcase_data['status_testcase'] = test_result.tag
            testcase_data['message'] = test_result.get('message', '')[1000:]
            testcase_data['text'] = test_result.get('text', '')[1000:]
            return self.parse(testcase_data, data_url)
        # the test is a success if there is no testresult
        testcase_data['status_testcase'] = 'passed'
        testcase_data['message'] = ''
        testcase_data['text'] = ''
        return self.parse(testcase_data, data_url)

    def parse_testsuite(self, xml_node_testsuite, data_url) -> Iterable[TestCase]:
        for testcase in xml_node_testsuite:
            testcase = self.parse_testcase(testcase, data_url)
            if testcase is None:
                continue
            yield testcase

    def parse_testsuites(self, xml_node_testsuites, data_url) -> Iterable[TestCase]:
        for testsuite in xml_node_testsuites:
            yield from self.parse_testsuite(testsuite, data_url)

if __name__ == '__main__':
    # this contraption allow to retrieve a sample dictionnary return
    import json
    from utils.custom_argument_parser import CustomArgumentParser

    parser = CustomArgumentParser()
    parser = XMLParser.add_arguments(parser)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)
    for data in XMLParser(**XMLParser.create_from_args(args)).parse_xml_file('<testcase></testcase>', ''):
        print(data)