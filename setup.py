from setuptools import setup

setup(
    name = 'polytaxis-adventure',
    version = '0.0.1',
    author = 'Rendaw',
    author_email = 'spoo@zarbosoft.com',
    url = 'https://github.com/Rendaw/ptadventure',
    download_url = 'https://github.com/Rendaw/ptadventure/tarball/v0.0.1',
    license = 'BSD',
    description = 'A browser for the polytaxis-monitor index.',
    long_description = open('readme.md', 'r').read(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ],
    install_requires = [
        'appdirs',
        'patricia-trie',
    ],
    packages = [
        'polytaxis_adventure', 
    ],
    entry_points = {
        'console_scripts': [
            'polytaxis-adventure = polytaxis_adventure.main:main',
        ],
    },
    include_package_resources=True,
    package_data={
        '': ['data/*.png', 'data/*.json'],
    },
)
