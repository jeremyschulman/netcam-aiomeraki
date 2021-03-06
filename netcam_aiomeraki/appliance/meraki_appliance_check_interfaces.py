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

from netcad.checks import check_result_types as tr

from netcad.topology.checks.check_interfaces import (
    InterfaceCheckCollection,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_appliance_dut import MerakiApplianceDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_appliance_check_interfaces"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_appliance_check_interfaces(
    dut, check_collection: InterfaceCheckCollection
) -> Optional[tr.CheckResultsCollection]:
    """
    Validate the device interface config and status against the design
    expectations.
    """
    dut: MerakiApplianceDeviceUnderTest
    device = dut.device

    api_data = await dut.get_switchports()
    map_port_status = {str(port_st["number"]): port_st for port_st in api_data}

    results = list()

    for check in check_collection.checks:
        if_name = check.check_id()

        # TODO: for now, only going to check the ports 3+, and not the wan
        #       (ports 1,2).  The SVI is checked via the ipaddrs test cases.

        if not (msrd_status := map_port_status.get(if_name)):
            continue

        msrd_used = msrd_status["enabled"] is True
        if msrd_used != check.expected_results.used:
            results.append(
                tr.CheckFailFieldMismatch(
                    device=device,
                    check=check,
                    field="used",
                    measurement=msrd_used,
                )
            )
            continue

        results.append(
            tr.CheckPassResult(device=device, check=check, measurement=msrd_status)
        )

    # return all testing results
    return results
