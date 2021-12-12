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

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional
from functools import singledispatchmethod

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aiomeraki.meraki_dut import (
    MerakiDeviceUnderTest,
    TestCases,
    CollectionTestResults,
)

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["MerakiMXDeviceUnderTest"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class MerakiMXDeviceUnderTest(MerakiDeviceUnderTest):

    # -------------------------------------------------------------------------
    #
    #                           Meraki MX Methods
    #
    # -------------------------------------------------------------------------

    async def get_lldp_status(self):
        return await self.api_cache_get(
            key="lldp_status",
            call="devices.getDeviceLldpCdp",
            serial=self.serial,
        )

    async def get_switchports(self):
        return await self.api_cache_get(
            key="switchports",
            call="appliance.getNetworkAppliancePorts",
            networkId=self.network_id,
        )

    async def get_vlans(self):
        return await self.api_cache_get(
            key="vlans",
            call="appliance.getNetworkApplianceVlans",
            networkId=self.network_id,
        )

    # -------------------------------------------------------------------------
    #
    #                           DUT Methods
    #
    # -------------------------------------------------------------------------

    @singledispatchmethod
    async def execute_testcases(
        self, testcases: TestCases
    ) -> Optional["CollectionTestResults"]:
        return await super().execute_testcases(testcases)

    # -------------------------------------------------------------------------
    #
    #                           Testing Executors
    #
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Support the 'cabling' testcases
    # -------------------------------------------------------------------------

    from .meraki_mx_tc_cabling import meraki_mx_tc_cabling

    execute_testcases.register(meraki_mx_tc_cabling)

    # -------------------------------------------------------------------------
    # Support the 'ipaddrs' testcases
    # -------------------------------------------------------------------------

    from .meraki_mx_tc_ipaddrs import meraki_mx_tc_ipaddrs

    execute_testcases.register(meraki_mx_tc_ipaddrs)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from .meraki_mx_tc_switchports import meraki_mx_tc_switchports

    execute_testcases.register(meraki_mx_tc_switchports)
