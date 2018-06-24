"""Some general utility functions."""


def validate_non_empty(**kwargs) -> None:
    r"""Validate that arguments are not empty. Raise ValueError if any argument
    is empty.

    Args:
        **kwargs: Mapping on the form {param_name: argument} where param_name
        is the name of the parameter and argument is the value passed in.
    """
    for param_name, argument in kwargs.items():
        if not argument:
            raise ValueError("{} must not be empty".format(param_name))


def validate_types(**kwargs) -> None:
    r"""Validate argument types. Raise TypeError if there is a mismatch.
    
    Args:
        **kwargs: Mapping on the form {param_name: (argument, expected_type)},
        where param_name is the name of the parameter, argument is the passed
        in value and expected type is either a single type, or a tuple of
        types.
    """
    for param_name, (argument, expected_types) in kwargs.items():
        if not isinstance(argument, expected_types):
            if isinstance(expected_types, tuple):
                exp_type_str = " or ".join(
                    [t.__name__ for t in expected_types])
            else:
                exp_type_str = expected_types.__name__
            raise TypeError(
                "{} is of type {.__class__.__name__}, expected {}".format(
                    param_name, argument, exp_type_str))
