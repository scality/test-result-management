
class AST:
    """
    The Ast allow the creation of query and reading of them easier
    It only contain the datas, the usage and algo is contained in a 'Visitor'
    This particuliar AST represent ElasticSearch Queries, it's not a 1 to 1 replicat since i've only done some of the ES query options    
    """
    pass

class Variable(AST):
    """
    represent a variable, have a variable name and possibly multiple values
    """
    def __init__(self, name, *values) -> None:
        self.name = name
        self.values = values

class Terms(AST):
    """
    represent 1 field / terms
    size=100000 is the number of instance to be retrieve
    """
    def __init__(self, field: str, size: int =100000) -> None:
        self.field = field
        self.size = size

class Avg(AST):
    """
    Allow the generation of the average in an aggregation
    """
    def __init__(self, field: str) -> None:
        self.field = field

class Aggs(AST):
    """
    Allow the creation of aggregations with multiple variable
    """
    def __init__(self, *variables) -> None:
        self.variables = variables


class Query(AST):
    """
    Query allow to use some filter in a global scope
    """
    def __init__(self, value) -> None:
        self.value = value

class Bool(AST):
    """
    create multiple condition logic
    """
    def __init__(self, *values) -> None:
        self.values = values

class Must(AST):
    """
    Every sub tree of a Must, must be True
    """
    def __init__(self, *values) -> None:
        self.values = values

class MustNot(AST):
    """
    Every sub tree of a MustNot, must be False
    """
    def __init__(self, *values) -> None:
        self.values = values

class FilterTerms(AST):
    """
    Allow a filter by terms
    """
    def __init__(self, field, values) -> None:
        if type(values) is not list:
            values = [values]
        self.values = values
        self.field = field

class Range(AST):
    """
    Allow a filter by range (date, number...)
    """
    def __init__(self, field, from_, to_) -> None:
        self.field = field
        self.from_ = from_
        self.to_ = to_

class MasterNode(AST):
    """
    Must be the root of the AST, it handle some elastic related things
    """
    def __init__(self, *asts, size=0) -> None:
        self.asts = asts
        self.size = size

class Filter(AST):
    """
    Filter but not in the global scope
    """
    def __init__(self, name, value) -> None:
        self.name = name
        self.value = value
class BucketSelector(AST):
    """
    create one or more bucket filters for the current bucket in an aggregation
    """
    def __init__(self, *values) -> None:
        self.values = values
class BucketPath(AST):
    """
    create usable in script variable from the current bucket
    """
    def __init__(self, variable_name, value) -> None:
        self.variable_name = variable_name
        self.value = value
class Script(AST):
    """
    a script that follow ElasticSearch syntaxe
    """
    def __init__(self, value) -> None:
        self.value = value
