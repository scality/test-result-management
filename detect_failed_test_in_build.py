from ES_query.visitor.interprete_response import ReadData

from api_manager.ES_manager import ESManager
from ES_query.AST import *
from ES_query.visitor.ast_to_query import CreateDictionnary

def create_aggregation_from(base_aggregation, aggregation_list):
    for agg in aggregation_list[::-1]:
        base_aggregation = Variable(agg, Terms(agg), base_aggregation)
        if agg != aggregation_list[0]:
            base_aggregation = Aggs(base_aggregation)
    return base_aggregation

def get_depth(dict_, depth):
    if depth == 0:
        return set(dict_.keys())
    values = set()
    for key, value in dict_.items():
        values = set.union(values, get_depth(value, depth - 1))
    return values


class ESSeeker(ESManager):
    def __init__(self, url: str):
        super().__init__(url)
    
    def analyse_build(self, build_id):
        from pprint import pprint
        # average for the build and get the date of the build
        build_id = '0' * (8 - len(build_id)) + build_id
        # get_avg = create_aggregation_from(get_avg, aggregation_list)
        aggregation_list = ['section', 'operating_system', 'merge_step', 'classname', "testname"]
        aggregation_list = ['testname']
        filter_unique_doc = Filter("just_one_name",
                                        BucketSelector(
                                            BucketPath(
                                                "doc_count", "_count"),
                                            Script(
                                                "params.doc_count == 1")
                                        )
                                        )
        filter_failed_test = Filter("avg_equal_0",
                                    BucketSelector(
                                        BucketPath(
                                            "avg_status_value", "status_value"),
                                        Script(
                                            "params.avg_status_value == 0")
                                    )
                                    )
        get_avg = Aggs(Variable("status_value",
                                         Avg("status_value")),
                                filter_unique_doc,
                                filter_failed_test)

        get_avg_of_testname = Variable("testname", Terms("testname"), get_avg)
        test_date_variable = Variable("test_date", Terms("test_date"))

        query_ast = MasterNode(
            Aggs(get_avg_of_testname, test_date_variable),
            Query(Bool(Must(FilterTerms("build_id", build_id))))
        )

        aggregate = self.get('_search', data=
                             CreateDictionnary().parse(
                                 query_ast
                             )).json()

        pprint(aggregate)
        parsed_data = ReadData().parse(query_ast, aggregate)
        pprint(parsed_data)
        testnames_for_build = parsed_data['testname']
        # get testnames and date to be querried
        test_date_buckets = parsed_data['test_date']
        if len(test_date_buckets.keys()) != 1:
            raise Exception('multiple date where found')
        test_date = test_date_buckets.popitem()[0] / 1000
        # repo_buckets = parsed_data['repo']
        # if len(repo_buckets.keys()) != 1:
        #     raise Exception('multiple repo where found')
        # repo = repo_buckets.popitem()[0]

        from datetime import datetime, timedelta
        test_date = datetime.fromtimestamp(test_date)
        testnames = list(parsed_data['testname'].keys())

        # average all testname that are in this build and in the 15 days date range
        filter_gt_4 = Filter("avg_sup_4",
                                    BucketSelector(
                                        BucketPath(
                                            "avg_status_value", "avg_status_value"),
                                        Script(
                                            "params.avg_status_value > 4")
                                    )
                                    )
        get_avg = Aggs(Variable("avg_status_value",
                                         Avg("status_value")),
                                filter_gt_4)
        get_avg_of_testname = Variable("testname", Terms("testname"), get_avg)

        query_ast = MasterNode(
            Aggs(get_avg_of_testname),
            Query(Bool(Must(Range("test_date", test_date - timedelta(days=15), test_date),
                            FilterTerms("testname", testnames)
                            ),
                       MustNot(FilterTerms("build_id", build_id))))
        )
        aggregate = self.get('_search', data=
                             CreateDictionnary().parse(
                                 query_ast
                             )).json()

        parsed_data = ReadData().parse(query_ast, aggregate)
        print('average for the testname (5 mean success, 0 mean failure):')
        print()
        for test, value in parsed_data.get('testname').items():
            print(test)
            print('\t', value['avg_status_value']['value'])
        print("===============================================================")
        print(f'status of build {build_id} (5 mean success, 0 mean failure): ')
        print()
        for test, value in testnames_for_build.items():
            print(test)
            print('\t', value['status_value']['value'])
        exit(0)
        aggregation_list = ['section', 'operating_system', 'merge_step', 'classname', "testname"]
        base_aggregation = Aggs(
            Variable('section', 
                     Terms('section'),
                     Aggs(
                         Variable("operating_system",
                         Terms("operating_system"),
                         FilterTerms("operating_system", get_depth(parsed_data, 3)),
                         Aggs(
                             Variable("merge_step",
                                Terms("merge_step"),
                                Aggs(
                                    Variable("classname",
                                        Terms("classname")),
                                        Variable("testname",
                                            Terms("testname"),
                                            Aggs(
                                                Variable("avg_status_value", Avg("status_value")),
                                                Filter("avg_greater_than_4",
                                                       BucketSelector(
                                                           BucketPath(
                                                               "avg_status_value", "avg_status_value"),
                                                           Script(
                                                               "params.avg_status_value > 4")
                                                       ))
                                            )))
                         )
                                    )))))
        get_avg = Aggs(Variable("avg_status_value",
                                Avg("status_value")),
                       Filter("avg_greater_than_4",
                              BucketSelector(
                                  BucketPath(
                                      "avg_status_value", "avg_status_value"),
                                  Script(
                                      "params.avg_status_value > 4")
                              )
                              )
                       )
        get_avg = create_aggregation_from(get_avg, aggregation_list)
        query_ast = MasterNode(
            Aggs(get_avg),
            Query(Bool(Must(Range("test_date", begin_date, test_date),
                            FilterTerms("repo", repo))))
        )
        aggregate = self.get('_search', data=
                             CreateDictionnary().parse(query_ast)
                             ).json()
        parsed_data_all = ReadData().parse(query_ast, aggregate)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    # ESSeeker.add_arguments(parser)
    parser.add_argument('build_id')
    args = parser.parse_args()
    url = "http://10.200.5.24:9200/"
    ESSeeker(url).analyse_build(args.build_id)
