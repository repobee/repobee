import re
import pathlib
import os
from setuptools import setup, find_packages

with open("README.md", mode="r", encoding="utf-8") as f:
    readme = f.read()

# parse the version instead of importing it to avoid dependency-related crashes
# the version of the core application is the same as that of the plugin system
with open("src/repobee_plug/__version.py", mode="r", encoding="utf-8") as f:
    line = f.readline()
    __version__ = line.split("=")[1].strip(" '\"\n")
    assert re.match(
        r"^\d+(\.\d+){2}(-(alpha|beta|rc|dev)(\.\d+)?)?$", __version__
    )

install_dir = os.getenv("REPOBEE_INSTALL_DIR")
if install_dir:  # install with RepoBee's install script
    pathlib.Path("src/_repobee/distinfo.py").write_text(
        f"""
import pathlib
DIST_INSTALL = True
INSTALL_DIR = pathlib.Path('{install_dir}')
"""
    )


dev_requirements = [
    "bandit",
    "black",
    "flake8>=3.8.3",
    "mypy>=0.902",
    "pylint",
    "pytest-cov>=2.6.1",
    "pytest-mock",
    "pytest>=6.0.0",
    "virtualenv",
    "responses>=0.18.0",
    # type stubs required for MyPy
    "types-pkg-resources",
    "types-requests",
    "types-tabulate",
    "types-toml",
    # requirements for docs
    "sphinx>=4.0.1",
    "sphinx-autodoc-typehints",
    "sphinx_rtd_theme",
    "sphinx-argparse",
]

testhelper_resources_dir = pathlib.Path("src/repobee_testhelpers/resources")
testhelper_resources = [
    p for p in testhelper_resources_dir.rglob("*") if p.is_file()
]

setup(
    name="repobee",
    version=__version__,
    description=(
        "A CLI tool for managing large amounts of GitHub repositories"
    ),
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Simon Larsén",
    author_email="slarse@kth.se",
    url="https://github.com/repobee/repobee",
    download_url=(
        "https://github.com/repobee/repobee/archive/v{}.tar.gz".format(
            __version__
        )
    ),
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=("tests", "docs")),
    data_files=[
        (str(testhelper_resources_dir), list(map(str, testhelper_resources)))
    ],
    py_modules=["repobee"],
    tests_require=dev_requirements,
    install_requires=[
        "appdirs>=1.4.4",
        "argcomplete>=1.12.0",
        "bullet>=2.2.0",
        "daiquiri>=3.0.1",
        "gitpython>=3.1.24",
        "more-itertools>=8.4.0",
        "pluggy>=0.13.1",
        "pygithub==1.57",
        "python-gitlab==3.11.0",
        "tabulate>=0.8.9",
        "tqdm>=4.48.2",
        "typing-extensions>=3.10.0.2",
        "yamliny>=0.0.2",
    ],
    extras_require=dict(DEV=dev_requirements),
    entry_points=dict(
        console_scripts="repobee = repobee:main",
        pytest11=["name_of_plugin = repobee_testhelpers.fixtures"],
    ),
    package_data={"repobee_plug": ["py.typed"]},
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
)
