
#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv global "$PYTHON"
    python --version
    python -m pytest tests --cov=gits_pet
else
    pytest tests --cov=gits_pet
fi
