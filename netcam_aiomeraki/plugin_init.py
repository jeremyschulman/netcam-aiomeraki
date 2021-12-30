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

from typing import Optional, Dict, List


class MerakiPluginGlobals:
    def __init__(self):
        self.config: Optional[Dict] = None
        self.orgs: Optional[List[Dict]] = None

    @property
    def org_name(self):
        return self.config.get("org_name")

    @property
    def org_id(self):
        return self.config.get("org_id")


g_meraki = MerakiPluginGlobals()


def plugin_init(config: dict):
    """Required netcadcam plugin init hook function"""
    g_meraki.config = config
