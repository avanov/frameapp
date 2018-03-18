import os
from typing import List

from pathlib import Path
from setuptools import setup
from setuptools import find_packages


here = Path(os.path.abspath(os.path.dirname(__file__)))


def get_dependencies(path: Path) -> List[str]:
    with path.open() as f:
        rows = f.read().strip().split('\n')
        requires = []
        for row in rows:
            row = row.strip()
            if row and not (row.startswith('#') or row.startswith('http')):
                requires.append(row)
        return requires


with here.joinpath('README.rst').open() as f:
    README = f.read()


install_requires = get_dependencies(here / 'requirements' / 'default.txt')
install_requires.extend(get_dependencies(here / 'requirements' / 'django.txt'))


# Setup
# ----------------------------

setup(name='frameapp',
      version='0.0.1',
      description='Frameapp',
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
      url='https://github.com/avanov/frameapp',
      keywords='web',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='tests',
      tests_require=get_dependencies(here / 'requirements' / 'testing.txt'),
      install_requires=install_requires,
      entry_points={
      }
    )
