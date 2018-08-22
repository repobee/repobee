from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

test_requirements = [
    'appdirs', 'daiquiri', 'pytest>=3.1.1', 'pytest-cov>=2.5.1', 'pytest-mock',
    'codecov'
]
required = ['appdirs', 'daiquiri', 'pygithub', 'colored', 'pluggy']

setup(
    name='repomate',
    version='0.1.0',
    description=('A CLI tool for GitHub'),
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Simon Larsén',
    author_email='slarse@kth.se',
    url='https://github.com/slarse/repomate',
    download_url='https://github.com/slarse/repomate/archive/v0.1.0.tar.gz',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    tests_require=test_requirements,
    install_requires=required,
    extras_require=dict(TEST=test_requirements),
    scripts=['bin/repomate'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Beta',
        'Intended Audience :: Teachers',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Linux'
        'Operating System :: macOS',
    ])
