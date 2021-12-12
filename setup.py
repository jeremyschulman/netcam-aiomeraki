# -*- coding: utf-8 -*-
from setuptools import setup

packages = ["netcam_aiomeraki"]

package_data = {"": ["*"]}

install_requires = ["meraki>=1.15.0,<2.0.0"]

setup_kwargs = {
    "name": "netcam-aiomeraki",
    "version": "0.1.0",
    "description": "Meraki Dashboard integration for netcad-netcam",
    "long_description": '# netcam-test-aiomeraki\nMeraki Dashboard integration for netcad-netcam\n\nThis package provides the "netcam test ..." integrations\nfor Cisco Meraki device managed through the Merkai Dashboard portal.\n\n## References\n\n   * [Meraki Dashboard API](https://developer.cisco.com/meraki/api-v1/#!introduction)\n   * [Python Docs on DevNet](https://developer.cisco.com/meraki/api-v1/#python)\n   * [Python Client on Github](https://github.com/meraki/dashboard-api-python/)\n\n\n',
    "author": "Jeremy Schulman",
    "author_email": None,
    "maintainer": None,
    "maintainer_email": None,
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "python_requires": ">=3.8,<4.0",
}


setup(**setup_kwargs)
