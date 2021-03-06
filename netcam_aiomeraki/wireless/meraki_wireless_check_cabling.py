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

from typing import TYPE_CHECKING, Optional

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.checks.check_cabling_nei import (
    InterfaceCablingCheckCollection,
    InterfaceCablingCheck,
)
from netcad.topology.checks.utils_cabling_nei import (
    nei_interface_match,
    nei_hostname_match,
)

from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_wireless_dut import MerakiWirelessDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_wireless_check_cabling"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_wireless_check_cabling(
    self, check_collection: InterfaceCablingCheckCollection
) -> Optional[trt.CheckResultsCollection]:
    """
    Validate the cabling neighborship data (LLDP/CDP) of the device against the
    design.
    """
    dut: MerakiWirelessDeviceUnderTest = self
    device = dut.device
    results = list()

    # if for some reason, the MX device is not reporting any cabling,
    # then return no results, and the User will see a "Skipped" indication.

    if not (api_data := await dut.get_lldp_status()):
        return None

    # create a mapping to the LLDP neighbor exclusive for the "port" interfaces.
    # there are other interfaces such as "wan" that are not of interest (yet).

    map_msrd_port_nei = {
        port_name: port_data for port_name, port_data in api_data["ports"].items()
    }

    for check in check_collection.checks:
        if_name = check.check_id()

        if not (msrd_ifnei := map_msrd_port_nei.get(if_name)):
            results.append(trt.CheckFailNoExists(device=device, check=check))
            continue

        results.extend(
            _check_one_interface(dut=dut, check=check, measurement=msrd_ifnei)
        )

    return results


def _check_one_interface(
    dut: "MerakiWirelessDeviceUnderTest",
    check: InterfaceCablingCheck,
    measurement: dict,
) -> trt.CheckResultsCollection:
    """
    Validate one of the interfaces on the wireless device for cabling.
    """
    results = list()
    device = dut.device
    expd_nei = check.expected_results

    # for now only checking the LLDP status; not checking CDP.
    # TODO: possibly support CDP if/when necessary

    if not (msrd_nei := measurement.get("lldp")):
        results.append(
            trt.CheckFailNoExists(device=device, check=check, measurement=measurement)
        )
        return results

    msrd_name = msrd_nei["systemName"]
    msrd_port_id = msrd_nei["portId"]

    if not nei_hostname_match(
        expd_nei.device, msrd_name
    ) and not dut.meraki_hostname_match(expd_nei.device, msrd_name):
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="device",
                measurement=msrd_name,
            )
        )

    if not nei_interface_match(expd_nei.port_id, msrd_port_id):
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="port_id",
                measurement=msrd_port_id,
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(device=device, check=check, measurement=measurement)
        )

    return results
