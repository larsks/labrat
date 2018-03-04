from setuptools import setup, find_packages

setup(
    name='labrat',
    version='0.1',
    author='Lars Kellogg-Stedman',
    author_email='lars@oddbit.com',
    url='https://github.com/larsks/labrat',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'git-lab = labrat.main:cli',
        ],
    }
)
