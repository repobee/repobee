from gits_pet import exception


def test_gits_pet_exception_repr():
    msg = "an exception message"
    expected_repr = "<GitsPetException(msg='{}')>".format(msg)
    exc = exception.GitsPetException(msg)

    assert repr(exc) == expected_repr
