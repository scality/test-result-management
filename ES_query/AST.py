
class AST:
    pass

class Variable(AST):
    def __init__(self, name, *values) -> None:
        self.name = name
        self.values = values

class Terms(AST):
    def __init__(self, field: str, size: int =100000) -> None:
        self.field = field
        self.size = size

class Avg(AST):
    def __init__(self, field: str) -> None:
        self.field = field

class Aggs(AST):
    def __init__(self, *variables) -> None:
        self.variables = variables


class Query(AST):
    def __init__(self, value) -> None:
        self.value = value

class Bool(AST):
    def __init__(self, *values) -> None:
        self.values = values

class Must(AST):
    def __init__(self, *values) -> None:
        self.values = values

class MustNot(AST):
    def __init__(self, *values) -> None:
        self.values = values

class FilterTerms(AST):
    def __init__(self, field, values) -> None:
        if type(values) is not list:
            values = [values]
        self.values = values
        self.field = field

class Range(AST):
    def __init__(self, field, from_, to_) -> None:
        self.field = field
        self.from_ = from_
        self.to_ = to_

class MasterNode(AST):
    def __init__(self, *asts, size=0) -> None:
        self.asts = asts
        self.size = size

class Filter(AST):
    def __init__(self, name, value) -> None:
        self.name = name
        self.value = value
class BucketSelector(AST):
    def __init__(self, *values) -> None:
        self.values = values
class BucketPath(AST):
    def __init__(self, variable_name, value) -> None:
        self.variable_name = variable_name
        self.value = value
class Script(AST):
    def __init__(self, value) -> None:
        self.value = value
