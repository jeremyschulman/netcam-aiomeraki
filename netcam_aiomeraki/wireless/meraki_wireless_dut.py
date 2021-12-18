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

__all__ = ["MerakiWirelessDeviceUnderTest"]


class MerakiWirelessDeviceUnderTest(MerakiDeviceUnderTest):
    async def get_ssids(self):
        """
        The SSIDs configuration contains the specific vlans that are in use.
        """
        return await self.api_cache_get(
            key="config_ssids",
            call="wireless.getNetworkWirelessSsids",
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
        If this DUT does not explicity implement a test-case, then try the
        superclass.
        """
        return await super().execute_testcases(testcases)

    # -------------------------------------------------------------------------
    # Support the 'cabling' testcases
    # -------------------------------------------------------------------------

    from .meraki_wireless_tc_cabling import meraki_device_tc_cabling

    execute_testcases.register(meraki_device_tc_cabling)

    # -------------------------------------------------------------------------
    # Support the 'ipaddrs' testcases
    # -------------------------------------------------------------------------

    from .meraki_wireless_tc_ipaddrs import meraki_wireless_tc_ipaddrs

    execute_testcases.register(meraki_wireless_tc_ipaddrs)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .meraki_wireless_tc_interfaces import meraki_wireless_tc_interfaces

    execute_testcases.register(meraki_wireless_tc_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from .meraki_wireless_tc_switchports import meraki_wireless_tc_switchports

    execute_testcases.register(meraki_wireless_tc_switchports)

    # -------------------------------------------------------------------------
    # Support the 'vlans' testcases
    # -------------------------------------------------------------------------

    from .merkai_wireless_tc_vlans import meraki_wireless_tc_vlans

    execute_testcases.register(meraki_wireless_tc_vlans)
