from ES_query.visitor.base_visitor import BaseVisitor
from ES_query.AST import Variable


class ReadData(BaseVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.is_first_node = True

    def _parse_buckets(self, ast, data) -> dict:
        values = {}
        for item in data:
            parsed = {}
            for child in ast.values:
                parsed_child = self.parse(child, item)
                if not parsed_child:
                    continue
                parsed = {**parsed, **parsed_child}
            values[parsed['key']] = parsed
            del parsed['key']
        return values

    def parse_variable(self, ast, data) -> dict:
        data_to_parse = data[ast.name]
        if 'buckets' in data_to_parse:
            data_to_parse = data_to_parse['buckets']
            return {ast.name: self._parse_buckets(ast, data_to_parse)}
        values = {}
        for child in ast.values:
            parsed_data = self.parse(child, data_to_parse)
            if parsed_data is None:
                continue
            values = {**values, **parsed_data}
        return {ast.name: values}

    def parse_terms(self, ast, data):
        return {'key': data['key']}

    def parse_avg(self, ast, data):
        return {'value': data['value']}

    def parse_aggs(self, ast, data):
        self.is_aggs = True
        variables = {}
        if 'aggregations' in data:
            data = data['aggregations']

        for variable in ast.variables:
            parsed_ast = self.parse(variable, data)
            if parsed_ast is None or parsed_ast == {}:
                continue
            variables = {**variables, **parsed_ast}
        return variables

    def parse_masternode(self, ast, data):
        asts = {}
        for ast_ in ast.asts:
            parsed_ast = self.parse(ast_, data)
            if parsed_ast is None:
                continue
            asts = {**asts, **parsed_ast}
        return asts
