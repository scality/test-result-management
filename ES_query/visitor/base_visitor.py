
class BaseVisitor:
    def __init__(self) -> None:
        self.tag_to_function = self.get_tag_to_function()
        self.is_first_node = True

    def get_tag_to_function(self):
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

    def parse(self, ast, data=None):
        try:
            return self.tag_to_function[type(ast).__name__.lower()](ast, data)
        except KeyError:
            raise

    def parse_variable(self, ast, data) -> dict:
        pass

    def parse_terms(self, ast, data):
        pass

    def parse_avg(self, ast, data):
        pass

    def parse_aggs(self, ast, data):
        pass

    def parse_range(self, ast, data):
        pass

    def parse_query(self, ast, data):
        pass

    def parse_bool(self, ast, data):
        pass

    def parse_must(self, ast, data):
        pass

    def parse_mustnot(self, ast, data):
        pass

    def parse_filterterms(self, ast, data):
        pass

    def parse_masternode(self, ast):
        pass

    def parse_filter(self, ast, data):
        pass

    def parse_bucketselector(self, ast, data):
        pass

    def parse_bucketpath(self, ast, data):
        pass

    def parse_script(self, ast, data):
        pass
