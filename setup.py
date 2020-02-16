from setuptools import setup, find_packages

__version__ = None
with open('drclip/__version__.py', 'r') as fh:
    exec(fh.readline())

install_requires = []
tests_require = []

with open('requirements.txt', 'r') as fh:
    for line in fh.read().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        elif line.endswith('# test'):
            tests_require.append(line)
        else:
            install_requires.append(line)


setup(
    name='drclip',
    version=__version__,
    packages=find_packages(),
    author='Jim Carreer',
    author_email='jim.carreer+drclip@gmail.com',
    description='A click based tool for working with remote docker registries',
    test_suite='tests',
    install_requires=install_requires,
    tests_require=tests_require,
    python_requires='>3.6.0',
    extras_require={'tests': tests_require},
    entry_points={
        'console_scripts': [
            'drclip=drclip:drclip'
        ]
    }
)