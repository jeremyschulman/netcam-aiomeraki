# -*- coding: utf-8 -*-

#  Copyright 2021 Jeremy Schulman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

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
