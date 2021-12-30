# -*- coding: utf-8 -*-
from setuptools import setup

packages = [
    "netcam_aiomeraki",
    "netcam_aiomeraki.appliance",
    "netcam_aiomeraki.switch",
    "netcam_aiomeraki.wireless",
]

package_data = {"": ["*"]}

install_requires = [
    "aiohttp<4.0",
    "macaddr>=2.1,<3.0",
    "meraki>=1.15.0,<2.0.0",
    "tenacity>=8.0.1,<9.0.0",
]

setup_kwargs = {
    "name": "netcam-aiomeraki",
    "version": "0.1.0",
    "description": "Meraki Dashboard integration for netcad-netcam",
    "long_description": "# netcam-aiomeraki\nNetCadCam plugin for Meraki Dashboard integration.\n\nThe following design services are supported:\n\n   * Topology\n   * VLANs\n\n---\n**NOTE**: This package is under active development and not distributed via pypi.  Code is not\nconsidered alpha at this point.  You are welcome to look around and try things out, but\nplease be aware the code is subject to change without notice.\n---\n\n## Topology Design Support\n\nThe following topology checks are supported:\n\n   * device\n   * interfaces\n   * cabling\n   * ipaddrs\n\n## VLANs Design Support\n\nThe following vlans checks are supported:\n   * vlans\n   * switchports\n\n\n## References\n\n   * [Meraki Dashboard API](https://developer.cisco.com/meraki/api-v1/#!introduction)\n   * [Python Docs on DevNet](https://developer.cisco.com/meraki/api-v1/#python)\n   * [Python Client on Github](https://github.com/meraki/dashboard-api-python/)\n\n### Python Client References:\n   * [Find a specific device by name](https://developer.cisco.com/meraki/api-v1/#!get-organization-devices)\n\n",
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
