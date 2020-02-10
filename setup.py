"""Setup.

Allows installing of the package using setuptools

Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    February 05, 2020
"""
from setuptools import setup


setup(name='dgxtools',
      version='0.9',
      description='A set of tools to help with DGX server tasks',
      url='https://github.com/yvan674/dgx_tools',
      author='Yvan Satyawan',
      author_email='y_satyawan@hotmail.com',
      license='MIT',
      packages=['dgxtools'],
      scripts=['bin/sgpu',
               'bin/container-inspect',
               'bin/gpu-graph'],
      zip_safe=False)
