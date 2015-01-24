__author__ = 'Noah Peeters'

from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='mathexpressions',
      version='0.3',
      description='Python library for parsing and solving math expressions. Example Usage: ' +
                  'https://github.com/NoahPeeters/pymathexpressions/blob/master/example.py ' +
                  'Documentation is coming soon.',
      url='https://github.com/NoahPeeters/pymathexpressions',
      author='Noah Peeters',
      author_email='noah.peeters@icloud.com',
      license='MIT',
      packages=['mathexpressions'],
      zip_safe=False)