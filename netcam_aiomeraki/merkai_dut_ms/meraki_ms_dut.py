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


class MerakiMSDeviceUnderTest(MerakiDeviceUnderTest):
    async def get_port_status(self):
        return await self.api_cache_get(
            key="port_status",
            call="switch.getDeviceSwitchPortsStatuses",
            serial=self.serial,
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
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .meraki_ms_tc_interfaces import meraki_switch_tc_interfaces

    execute_testcases.register(meraki_switch_tc_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from .meraki_ms_tc_switchports import meraki_ms_tc_switchports

    execute_testcases.register(meraki_ms_tc_switchports)
