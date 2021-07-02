

class Instantiable:
    instantiable_args = {
        'default': {'help': 'default argument'}
    }

    @classmethod
    def add_arguments(cls, parser):
        for arg, params in cls.instantiable_args.items():
            parser.add_argument(arg, **params)
        return parser

    @classmethod
    def create_from_args(cls, args):
        args = vars(args)
        params_dict = {}
        for arg, params in cls.instantiable_args.items():
            formatted_arg = arg.replace('-', '_').lstrip('_')
            given_value = args.get(formatted_arg, None)
            if given_value is None:
                if params.get('optionnal', False) or arg.startswith('--'):
                    continue
                else:
                    raise Exception(f'[Instantiable] argument : {arg} was not optionnal and not given')
            params_dict[formatted_arg] = given_value
        return cls(**params_dict)