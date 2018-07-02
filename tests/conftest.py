"""Test setup."""
from unittest.mock import patch

# the git module must be imported with a mocked env variable
TOKEN = 'besttoken1337'
with patch('os.getenv', autospec=True, return_value=TOKEN):
    import gits_pet
    from gits_pet import git

assert TOKEN == gits_pet.git.OAUTH_TOKEN
