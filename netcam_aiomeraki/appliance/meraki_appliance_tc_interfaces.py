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
from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam import tc_result_types as tr

from netcad.topology.tc_interfaces import (
    InterfaceTestCases,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_appliance_dut import MerakiApplianceDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_appliance_tc_interfaces"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_appliance_tc_interfaces(
    dut, testcases: InterfaceTestCases
) -> Optional[tr.CollectionTestResults]:

    dut: MerakiApplianceDeviceUnderTest
    device = dut.device

    api_data = await dut.get_switchports()
    map_port_status = {str(port_st["number"]): port_st for port_st in api_data}

    results = list()

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()

        # TODO: for now, only going to check the ports 3+, and not the wan
        #       (ports 1,2).  The SVI is checked via the ipaddrs test cases.

        if not (msrd_status := map_port_status.get(if_name)):
            continue

        msrd_used = msrd_status["enabled"] is True
        if msrd_used != test_case.expected_results.used:
            results.append(
                tr.FailFieldMismatchResult(
                    device=device,
                    test_case=test_case,
                    field="used",
                    measurement=msrd_used,
                )
            )
            continue

        results.append(
            tr.PassTestCase(device=device, test_case=test_case, measurement=msrd_status)
        )

    # return all testing results
    return results
