from ES_query.visitor.interprete_response import ReadData
from ES_query.visitor.ast_to_query import CreateDictionnary
from ES_query.AST import AST, Aggs, Terms, Variable
from utils.instantiable import Instantiable
import api_manager.base_manager
import elasticsearch
import logging

from typing import *

from elasticsearch.helpers import streaming_bulk

log = logging.getLogger(__name__)

class ESManager(api_manager.base_manager.BaseManager, Instantiable):
    """
    handle ES
    based on basemanager but don't use it since there is a python API for ES
    """
    instantiable_args = {
        'elastic_url':{
                'help': 'elastic API url to push data into (ex: https://elasticsearch.devsca.com:9200/)'
                },
        '--elastic-username':{
                'help': 'basic-auth username'
                },
        '--elastic-password':{
                'help': 'basic-auth password',
                }
    }
    def __init__(self, elastic_url: str, elastic_username: Optional[str]=None, elastic_password: Optional[str]=None):
        """
        initialise the ES python module with 1 url (one node), might need multiple node depending if performance require it
        params: url : one of the ES node
        """
        self.es = elasticsearch.Elasticsearch([elastic_url], http_auth=(elastic_username, elastic_password))
        super().__init__('ES', elastic_url, elastic_username, elastic_password)

    def create_or_update_index(self, index_name: str, mappings: dict) -> bool:
        """
        create a new index with a custom mapping
        params: index_name: the name of the index to create
                mappings: the mapping to apply to this index
        if the index already exist, will try to update it
        """
        try:
            self.es.indices.create(
                index=index_name,
                body={
                    'settings': {'number_of_shards': 1}, 
                    'mappings': mappings
                })
        except elasticsearch.exceptions.RequestError as e:
            # if the indice already exist or any other errors occured
            self.es.indices.put_mapping(mappings, index=index_name)
    
    def bulk_upload(self, index_name: str, generator: Iterable[dict]) -> Iterable[Tuple[bool, str]]:
        """
        wrapper arround streaming bulk upload with already given data
        params: index_name: the index where to store the items
                generator: stream of items to store in the ES
        yield : success, info: if the item has been stored in the DB and info in case of failure
        """
        return streaming_bulk(client=self.es, index=index_name, actions=generator)
    
    def search(self, query: AST):
        """
        perform a search query with the given AST from ES Query
        """

        # convert AST to a query dict
        query_dict = CreateDictionnary().parse(query)
        # perform the request
        response = self.get('_search', data=query_dict).json()
        # read the response and format it nicely
        return ReadData().parse(query, response)
    
    def aggregate(self, aggregations: list, query: Optional[dict]=None) -> dict:
        """
        wrapper arround aggregation call
        params: aggregation: a list of terms to aggregate arround
                    ex: ['repo', 'merge_step', 'milestone']
                query: Top level filter for the aggregation
        return: the aggregation following elastic format
        """
        created_aggregations = self._create_aggregation(aggregations)
        created_aggregations = CreateDictionnary().parse(created_aggregations)
        if query is None:
            return self.get('_search', data={
                "size": 0,
                **created_aggregations,
            }).json()
        else:
            return self.get('_search', data={
                "size": 0,
                **created_aggregations,
                "query": query
            }).json()

