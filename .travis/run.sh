
#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv global "$PYTHON"
    python --version
    python -m pytest tests --cov=repomate
else
    pytest tests --cov=repomate
fi
