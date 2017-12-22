import os

from pathlib import Path
from setuptools import setup
from setuptools import find_packages


here = Path(os.path.abspath(os.path.dirname(__file__)))

with here.joinpath('README.rst').open() as f:
    README = f.read()

with here.joinpath('requirements.txt').open() as f:
    rows = f.read().strip().split('\n')
    requires = []
    for row in rows:
        row = row.strip()
        if row and not (row.startswith('#') or row.startswith('http')):
            requires.append(row)


# Setup
# ----------------------------

setup(name='metaframe',
      version='0.0.1',
      description='Metaframe',
      long_description=README,
      classifiers=[
          'Development Status :: 1 - Planning',
          'Intended Audience :: Developers',
          'License :: OSI Approved',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Operating System :: POSIX',
          'Topic :: Internet :: WWW/HTTP',
      ],
      author='Maxim Avanov',
      author_email='maxim.avanov@gmail.com',
      url='https://github.com/avanov',
      keywords='web',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tests',
      tests_require=['pytest', 'coverage'],
      install_requires=requires,
      entry_points={
      }
    )
