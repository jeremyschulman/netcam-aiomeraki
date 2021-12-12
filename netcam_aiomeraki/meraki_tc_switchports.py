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

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam import tc_result_types as tr
from netcad.vlan.tc_switchports import SwitchportTestCases

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_dut import MerakiDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_tc_switchports"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_tc_switchports(
    self, testcases: SwitchportTestCases
) -> tr.CollectionTestResults:
    dut: MerakiDeviceUnderTest = self

    product_handlers = {
        "MX": _meraki_mx_tc_switchports,
        "MS": _meraki_ms_tc_switchports,
    }

    if not (handler := product_handlers.get(dut.model[0:2])):
        return [
            tr.SkipTestCases(
                device=self.device,
                message=f"Missing: device {self.device.name} model: {dut.model} support for "
                f"testcases: {testcases.get_service_name()}",
            )
        ]

    return await handler(dut, testcases)


async def _meraki_mx_tc_switchports(
    dut: "MerakiDeviceUnderTest", testcases: SwitchportTestCases
) -> tr.CollectionTestResults:
    ...


async def _meraki_ms_tc_switchports(
    dut: "MerakiDeviceUnderTest", testcases: SwitchportTestCases
) -> tr.CollectionTestResults:

    ...
