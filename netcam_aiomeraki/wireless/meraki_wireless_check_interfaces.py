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

from netcad.topology.check_interfaces import (
    InterfaceCheckCollection,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_wireless_dut import MerakiWirelessDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_wireless_check_interfaces"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_wireless_check_interfaces(
    dut, check_collection: InterfaceCheckCollection
) -> Optional[tr.CheckResultsCollection]:
    """
    Validate the wireless device interfaces against the design.
    """
    dut: MerakiWirelessDeviceUnderTest
    device = dut.device

    # the only way to measure the operational status of the ethernet ports is
    # to check the LLDP data. If the data is there, then the interface is up.

    api_data = await dut.get_lldp_status()
    if not api_data:
        message = "No LLDP/CDP data returned from API"
        return [tr.CheckSkipResult(device=device, message=message)]

    def nei_data_exists(_on_port) -> bool:
        """
        Returns True if the interface is reporting any neighbor device either
        via LLDP or CDP.
        """
        return bool(
            _on_port.get("lldp", {}).get("systemName")
            or _on_port.get("cdp", {}).get("deviceId")
        )

    map_port_status = {
        port_name: True
        for port_name, port_data in api_data["ports"].items()
        if nei_data_exists(port_data)
    }

    map_port_status["wan1"] = True
    results = list()

    for check in check_collection.checks:
        if_name = check.check_id()

        # if the expected interface does not exist then report the error
        if not (msrd_status := map_port_status.get(if_name)):
            results.append(tr.CheckFailNoExists(device=device, check=check))
            continue

        # not checking the status of wan1 since it is always there.  The IP
        # assignment would be checked by the 'ipaddrs' testcases.

        if if_name == "wan1":
            continue

        msrd_used = msrd_status is True
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
