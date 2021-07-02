import argparse

class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, *kargs, **kwargs):
        self.arguments = set()
        super().__init__(*kargs, **kwargs)

    def add_argument(self, name, *kargs, **kwargs):
        """
        ensure only one argument is asked for cli
        make sure to put required argument first to be optimal, otherwise, argument might be optionnal instead of required
        """
        custom_name = name
        if custom_name.startswith('--'):
            custom_name = name[2:]
        if custom_name in self.arguments:
            return
        self.arguments.add(custom_name)
        super().add_argument(name, *kargs, **kwargs)