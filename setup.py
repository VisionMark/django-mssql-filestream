import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-mssql-filestream',
    version='0.1.1',
    packages=['sql_filestream'],
    include_package_data=True,
    description='Provides Django model fields to use the SQL Server Filestream feature.',
    long_description=README,
    author='Renaud Parent',
    author_email='renaud.parent@gmail.com',
    url='https://github.com/rparent/django-mssql-filestream',
    license='MIT',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'Topic :: Software Development :: Libraries :: Application Frameworks',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python :: 2',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3.4',
      'Framework :: Django',
      'Framework :: Django :: 1.7',
    ],
    keywords='django concurrent editing lock locking tokens'
)
