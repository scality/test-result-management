import re
import datetime
import logging
from utils.instantiable import Instantiable
from bs4 import BeautifulSoup

from typing import *
from typing import Pattern

from api_manager.base_manager import BaseManager
from parser.base_parser import BaseParser, TestCase


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

    def get_test_from_files(self, files: List[str], parser: BaseParser) -> Iterable[TestCase]:
        processed_element = False
        for file_ in files:
            if any(blacklisted_file for blacklisted_file in parser.settings['file']['black_list'] if blacklisted_file in file_):
                continue
            log.info(f'getting : {self.url}/{file_}')
            file_response = self.get(file_)
            processed_element = True
            yield from parser.parse_file(file_response.content, f'{self.url}/{file_}')
        if not processed_element:
            log.info('no testfile found in artifact')

    def get_test_from_one_artifact(self, artifact: str, parsers: Dict[Pattern[str], BaseParser]) -> Iterable[TestCase]:
        """
        will retrieve all the report.xml in artifact and return all the testcase it can find in them
        params: 
                artifact : The artifact where the tests are stored
                parser : The parser to be used (for ring it's xml_parser.XMLParser but can create new parser if tests are not correctly retrieve)
        return: generator of testcase
        """
        log.info(f'getting artifact {artifact}')
        # list all files in artifact
        artifact_files = list(self.list_artifact(artifact))
        
        # final_status for the date
        try:
            test_date = datetime.datetime.strptime(self.get(f'{artifact}/.final_status').headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z') 
        except:
            test_date = datetime.datetime.now()
            log.warning('test date not found')

        # find wich parser to use for wich files
        for regexp, parser in parsers.items():
            files = filter(lambda artifact_file: regexp.match(artifact_file) is not None,
                                    artifact_files)
            parser.test_date = test_date
            yield from self.get_test_from_files(files, parser)

    def get_all_tests(self, parsers: Dict[Pattern[str], BaseParser], black_list: List[str]=[]) -> Iterable[Iterable[TestCase]]:
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
            yield self.get_test_from_one_artifact(artifact, parsers)

if __name__ == '__main__':
    from parser.xml_parser import JunitParser
    import utils.custom_argument_parser
    parser = utils.custom_argument_parser.CustomArgumentParser(description='retrieve datas from artifact and print them')
    parser = ArtifactManager.add_arguments(parser)
    parser = JunitParser.add_arguments(parser)
    args = parser.parse_args()

    # create the ArtifactManager
    artifact_manager = ArtifactManager(**ArtifactManager.create_from_args(args))
    xml_parser= JunitParser(**JunitParser.create_from_args(args))
    for item in artifact_manager.get_all_tests(xml_parser):
        print(item)
