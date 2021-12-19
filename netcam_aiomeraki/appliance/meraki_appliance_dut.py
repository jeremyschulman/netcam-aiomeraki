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

__all__ = ["MerakiApplianceDeviceUnderTest"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class MerakiApplianceDeviceUnderTest(MerakiDeviceUnderTest):
    """
    Meraki DUT sub-class for "appliance" devices such as the MX product line.
    """

    # -------------------------------------------------------------------------
    #
    #                           Meraki MX Methods
    #
    # -------------------------------------------------------------------------

    # async def get_lldp_stqqatus(self):
    #     return await self.api_cache_get(
    #         key="lldp_status",
    #         call="devices.getDeviceLldpCdp",
    #         serial=self.serial,
    #     )

    async def get_switchports(self):
        """Get the appliance switchport configuration"""
        return await self.api_cache_get(
            key="switchports",
            call="appliance.getNetworkAppliancePorts",
            networkId=self.network_id,
        )

    async def get_vlans(self):
        """Get the appliance vlan configuraiton"""
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
        """
        Dispatch hook for testcase executor registration in this sub-class. If
        this method is reached it means that this DUT does not implement the
        specific testcases and the super-class is tried.
        """
        return await super().execute_testcases(testcases)

    # -------------------------------------------------------------------------
    #
    #                           Testing Executors
    #
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Support the 'cabling' testcases
    # -------------------------------------------------------------------------

    from .meraki_appliance_tc_cabling import meraki_device_tc_cabling

    execute_testcases.register(meraki_device_tc_cabling)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .meraki_appliance_tc_interfaces import meraki_appliance_tc_interfaces

    execute_testcases.register(meraki_appliance_tc_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'ipaddrs' testcases
    # -------------------------------------------------------------------------

    from .meraki_appliance_tc_ipaddrs import meraki_mx_tc_ipaddrs

    execute_testcases.register(meraki_mx_tc_ipaddrs)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from .meraki_appliance_tc_switchports import meraki_appliance_tc_switchports

    execute_testcases.register(meraki_appliance_tc_switchports)

    # -------------------------------------------------------------------------
    # Support the 'vlans' testcases
    # -------------------------------------------------------------------------

    from .merkai_appliance_tc_vlans import meraki_mx_tc_vlans

    execute_testcases.register(meraki_mx_tc_vlans)
