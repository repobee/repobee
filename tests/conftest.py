"""Test setup."""
import sys
from unittest.mock import patch, MagicMock

# the git module must be imported with a mocked env variable
TOKEN = 'besttoken1337'
with patch('os.getenv', autospec=True, return_value=TOKEN):
    import gits_pet
    from gits_pet import git

# mock the PyGithub github module
sys.modules['github'] = MagicMock()


assert TOKEN == gits_pet.git.OAUTH_TOKEN
