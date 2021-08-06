from typing import *

from parser.base_parser import BaseParser, TestCase, TestCaseCandidate


class GeneratedTestParser(BaseParser):
    """
    Parser for generated testcase
    """
    class GeneratedTestParserException(Exception):
        def __str__(self):
            return '[GeneratedTestParser] ' + super().__str__()

    def parse(self, data: TestCaseCandidate, data_url: str) -> Optional[TestCase]:
        """
        the testcse candidate already have almost all the right information
        just need to add 'testresult' for a not run test
        """
        data['status_testcase'] = 'untested'
        data['duration'] = 0
        data['message'] = ''
        data['text'] = ''
        return super().parse(data, data_url)