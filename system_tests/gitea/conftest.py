import pytest
import giteamanager


@pytest.fixture(autouse=True)
def setup_gitea(teardown_gitea):
    giteamanager.setup()


@pytest.fixture(autouse=True)
def teardown_gitea():
    if giteamanager.gitea_is_running():
        giteamanager.teardown()


@pytest.fixture(autouse=True, scope="session")
def teardown_after():
    yield
    giteamanager.teardown()
