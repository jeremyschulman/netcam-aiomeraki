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

from typing import Optional, List, Dict
from functools import singledispatchmethod

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aiomeraki.meraki_dut import (
    MerakiDeviceUnderTest,
    CheckCollection,
    CheckResultsCollection,
)


class MerakiSwitchDeviceUnderTest(MerakiDeviceUnderTest):
    """
    Support the Meraki switch devices, product models that being with "MS".
    """

    async def get_port_config(self) -> List[Dict]:
        """
        Obtain the switch port configuration.  The API content is cached.
        """
        return await self.api_cache_get(
            key="ports_config",
            call="switch.getDeviceSwitchPorts",
            serial=self.serial,
        )

    async def get_port_status(self) -> dict:
        """
        Obtain the switch port status information.  The API content is cached.
        """
        return await self.api_cache_get(
            key="ports_status",
            call="switch.getDeviceSwitchPortsStatuses",
            serial=self.serial,
        )

    # -------------------------------------------------------------------------
    #
    #                           DUT Methods
    #
    # -------------------------------------------------------------------------

    @singledispatchmethod
    async def execute_checks(
        self, testcases: CheckCollection
    ) -> Optional["CheckResultsCollection"]:
        """
        If this DUT does not explicity implement a test-case, then try the
        superclass.
        """
        return await super().execute_checks(testcases)

    # -------------------------------------------------------------------------
    # Support the 'cabling' testcases
    # -------------------------------------------------------------------------

    from .meraki_switch_check_cabling import meraki_switch_check_cabling

    execute_checks.register(meraki_switch_check_cabling)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .meraki_switch_check_interfaces import meraki_switch_check_interfaces

    execute_checks.register(meraki_switch_check_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from .meraki_switch_check_switchports import meraki_switch_check_switchports

    execute_checks.register(meraki_switch_check_switchports)

    # -------------------------------------------------------------------------
    # Support the 'vlans' testcases
    # -------------------------------------------------------------------------

    from .meraki_switch_tc_vlans import meraki_switch_check_vlans

    execute_checks.register(meraki_switch_check_vlans)
