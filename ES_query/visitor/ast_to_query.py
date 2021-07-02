
from ES_query.visitor.base_visitor import BaseVisitor


class CreateDictionnary(BaseVisitor):
    def parse_variable(self, ast, data) -> dict:
        values = {}
        for value in ast.values:
            values = {**values, **self.parse(value)}
        return {ast.name: values}

    def parse_terms(self, ast, data):
        return {"terms": {"field": ast.field, "size": ast.size}}

    def parse_avg(self, ast, data):
        return {"avg": {"field": ast.field}}

    def parse_aggs(self, ast, data):
        variables = {}
        for variable in ast.variables:
            variables = {**variables, **self.parse(variable)}
        return {"aggs": variables}

    def parse_range(self, ast, data):
        return {
            "range":
            {
                ast.field: {
                    "gte": ast.from_.isoformat(),
                    "lt": ast.to_.isoformat()
                }
            }
        }
    def parse_query(self, ast, data):
        return {
            "query": self.parse(ast.value)
        }
    def parse_bool(self, ast, data):
        values = {}
        for value in ast.values:
            values = {**values, **self.parse(value)}
        return {"bool": values}
    def parse_must(self, ast, data):
        return {
            "must": [
                self.parse(value) for value in ast.values
            ]
        }
    def parse_mustnot(self, ast, data):
        return {
            "must_not": [
                self.parse(value) for value in ast.values
            ]
        }
    def parse_filterterms(self, ast, data):
        if len(ast.values) == 1:
            return {"term": {ast.field: {'value': ast.values[0]}}}
        else:
            return {"terms": {ast.field: ast.values}}
    def parse_masternode(self, ast, data):
        asts = {}
        for ast_ in ast.asts:
            asts = {**asts, **self.parse(ast_)}
        return {'size': ast.size, **asts}
    def parse_filter(self, ast, data):
        return {
            ast.name: self.parse(ast.value)
        }
    def parse_bucketselector(self, ast, data):
        values = {}
        for value in ast.values:
            values = {**values, **self.parse(value)}
        return {"bucket_selector": {**values}}

    def parse_bucketpath(self, ast, data):
        return {
            "buckets_path": {ast.variable_name: ast.value}
        }
    def parse_script(self, ast, data):
        return {
            "script": ast.value
        }