import re
from setuptools import setup, find_packages

with open("README.md", mode="r", encoding="utf-8") as f:
    readme = f.read()

# parse the version instead of importing it to avoid dependency-related crashes
with open("repobee/__version.py", mode="r", encoding="utf-8") as f:
    line = f.readline()
    __version__ = line.split("=")[1].strip(" '\"\n")
    assert re.match(r"^\d+(\.\d+){2}$", __version__)

test_requirements = [
    "appdirs",
    "daiquiri",
    "pytest>=4.0.0",
    "pytest-cov>=2.6.1",
    "pytest-mock",
    "codecov",
]
required = [
    "appdirs",
    "daiquiri",
    "pygithub",
    "colored",
    "repobee-plug==0.6.0",
    "python-gitlab==1.8.0",
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
    packages=find_packages(exclude=("tests", "docs")),
    tests_require=test_requirements,
    install_requires=required,
    extras_require=dict(TEST=test_requirements),
    scripts=["bin/repobee"],
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
)
