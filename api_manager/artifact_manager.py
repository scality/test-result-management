import re
import datetime
import logging
from xml.etree.ElementTree import XML
from utils.instantiable import Instantiable
from bs4 import BeautifulSoup

from typing import *

from api_manager.base_manager import BaseManager
from parser.base_parser import TestCase
from parser.xml_parser import XMLParser


log = logging.getLogger(__name__)

class ArtifactManager(BaseManager, Instantiable):
    """
    Create and manage a crawler for artifact
    removing the need to have a recursive wget to download all of the artifact in one go
    """
    instantiable_args = {
        'artifact_url': {'help': 'artifact url (ex: https://eve.devsca.com/github/scality/ring/artifacts/builds/)'},
        '--artifact-username': {'help': 'username for artifact'},
        '--artifact-password': {'help': 'password for artifact'},
        '--artifact': {'help': 'the artifact to retrieve, will be interpreted as a regexp, if empty, will do all artifact (might be big)'}
    }
    def __init__(self, artifact_url: str,
        artifact_username: Optional[str]=None,
        artifact_password: Optional[str]=None,
        artifact: Optional[str]=None):
        """
            artifact_url: the base url of the service (ex :https://eve.devsca.com/github/scality/ring/artifacts/builds)
            username: the username  to login (ex: admin) (optionnal)
            password: the password to login (ex: admin) (optionnal)
            artifact : the artifacts to retrieve, it's a regexp to allow maximum range of use
        """
        self.artifact_regexp = re.compile(artifact.replace(':', '%3A')) if artifact is not None else re.compile('.*')
        super().__init__('ARTIFACT', artifact_url, artifact_username, artifact_password)

    def list_artifacts(self) -> Iterable[str]:
        """
        get the artifacts name and return a list from artifact_url
        return : List<String> : list of artifact retrieved in url (ex: ['github%3Ascality%3Aring%3Astaging-8.5.0.0.r210218164005.17bd3cf.post-merge.00112703/', ...])
        """
        page = self.get()
        soup = BeautifulSoup(page.text, 'html.parser')
        artifacts = (node['href'][2:] for node in soup.find_all('a', href=True))
        return artifacts

    def list_artifact(self, artifact: str) -> Iterable[str]:
        """
        List all the files in artifact
        ex: ['{artifact}/.final_status', '{artifact}/test/report.json'
        """
        listing_response = self.get(artifact + '/', format='txt')
        return map(lambda _file: f'{artifact}/{_file}', listing_response.text.split('\n'))

    def get_test_from_one_artifact(self, artifact: str, parser: XMLParser) -> Iterable[TestCase]:
        """
        will retrieve all the report.xml in artifact and return all the testcase it can find in them
        params: 
                artifact : The artifact where the tests are stored
                parser : The parser to be used (for ring it's xml_parser.XMLParser but can create new parser if tests are not correctly retrieve)
        return: generator of testcase
        """
        log.info(f'getting artifact {artifact}')
        # list all files in artifact
        artifact_files = self.list_artifact(artifact)
        
        # final_status for the date
        try:
            parser.test_date = datetime.datetime.strptime(self.get(f'{artifact}/.final_status').headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z') 
        except:
            parser.test_date = datetime.datetime.now()
            log.warning('test date not found')

        # select only xml file
        regexp_xml = re.compile(r'.*/(xunit_){0,1}report\.xml')
        xml_files = filter(lambda artifact_file: regexp_xml.match(artifact_file) is not None,
                                artifact_files)
        processed_element = False
        for xml_file in xml_files:
            if any(blacklisted_file for blacklisted_file in parser.settings['file']['black_list'] if blacklisted_file in xml_file):
                continue
            log.info(f'getting : {self.url}/{xml_file}')
            xml_file_response = self.get(xml_file)
            processed_element = True
            yield from parser.parse_xml_file(xml_file_response.content, f'{self.url}/{xml_file}')
        if not processed_element:
            log.info('no testfile found in artifact')

    def get_all_tests(self, parser: XMLParser, black_list: List[str]=[]) -> Iterable[Iterable[TestCase]]:
        """
        params:
                parser: a parser to format the testcase, might be XMLParser
                black_list: list of fullversionname to remove from the parsing (already processed)
        return : a generator of generator of testcase
            the first iterator is for each artifact
            the second iterator is all testcase in the current artifact
        """
        artifacts_list = self.list_artifacts()
        if self.artifact_regexp is not None:
            artifacts_list = filter(lambda artifact: self.artifact_regexp.match(artifact) is not None,
                                    artifacts_list)

        artifacts_list = filter(lambda artifact: artifact not in black_list, artifacts_list)

        # region debug print
        artifacts_list = list(artifacts_list)
        try:
            import pprint
            pprint.pprint(artifacts_list)
        except:
            print(artifacts_list)
        print(f"yielding {len(artifacts_list)} artifacts")
        # endregion

        for artifact in artifacts_list:
            yield self.get_test_from_one_artifact(artifact, parser)

if __name__ == '__main__':
    import utils.custom_argument_parser
    parser = utils.custom_argument_parser.CustomArgumentParser(description='retrieve datas from artifact and print them')
    parser = ArtifactManager.add_arguments(parser)
    parser = XMLParser.add_arguments(parser)
    args = parser.parse_args()

    # create the ArtifactManager
    artifact_manager = ArtifactManager(**ArtifactManager.create_from_args(args))
    xml_parser= XMLParser(**XMLParser.create_from_args(args))
    for item in artifact_manager.get_all_tests(xml_parser):
        print(item)
