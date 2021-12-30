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

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from netcad.device import Device
from netcad.checks import check_result_types as tr
from netcad.phy_port import PhyPortSpeeds

from netcad.topology.check_interfaces import (
    InterfaceCheckCollection,
    InterfaceCheck,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_switch_check_interfaces"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_switch_check_interfaces(
    dut, check_collection: InterfaceCheckCollection
) -> Optional[tr.CheckResultsCollection]:
    """
    Validate the device interface configuration and status against the design
    expectations.
    """
    device = dut.device

    status_list = await dut.get_port_status()
    map_port_status = {
        port_st["portId"]: SwitchInterfaceMeasurement.from_api(port_st)
        for port_st in status_list
    }

    results = list()

    for check in check_collection.checks:
        if_name = check.check_id()

        if not (msrd_status := map_port_status.get(if_name)):
            # design is attempting to use an interface that does not exist on
            # the device.  Report this as an error, and continue to next
            # test-case.
            results.append(tr.CheckFailNoExists(device=device, check=check))
            continue

        results_iface = meraki_check_switch_one_interface(
            device=device, check=check, measurement=msrd_status
        )

        if not any(isinstance(res, tr.CheckFailResult) for res in results_iface):
            results_iface.append(
                tr.CheckPassResult(
                    device=device, check=check, measurement=msrd_status.dict()
                )
            )

        results.extend(results_iface)

    # return the collection of the test case results.
    return results


# -----------------------------------------------------------------------------
#
#                             PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def meraki_to_speed(speed_str: str) -> int:
    """
    Convert the API returned speed value, represented as a string, into an int
    value in the form used by the design.
    """

    if not speed_str:
        return 0

    if speed_str == "1 Gbps":
        return PhyPortSpeeds.speed_1G

    elif speed_str == "100 Mbps":
        return PhyPortSpeeds.speed_100M

    raise RuntimeError(f"Unknown Meraki speed converstion for: '{speed_str}'")


class SwitchInterfaceMeasurement(BaseModel):
    """
    This class is used to normalize the Meraki API data into a form that makes
    it esaier to compare against the design expectations.
    """

    used: bool
    oper_up: bool
    speed: int

    @classmethod
    def from_api(cls, api_payload: dict):
        """convert Meraki API paayload into object"""
        return cls(
            used=api_payload["enabled"] is True,
            oper_up=api_payload["status"] == "Connected",
            speed=meraki_to_speed(api_payload["speed"]),
        )


def meraki_check_switch_one_interface(
    device: Device,
    check: InterfaceCheck,
    measurement: SwitchInterfaceMeasurement,
) -> tr.CheckResultsCollection:
    """
    Validate the state of one interface agains the design expectations.
    """

    if_flags = check.check_params.interface_flags or {}
    is_reserved = if_flags.get("is_reserved", False)
    should_oper_status = check.expected_results

    # -------------------------------------------------------------------------
    # If the interface is marked as reserved, then report the current state in
    # an INFO report and done with this test-case.
    # -------------------------------------------------------------------------

    if is_reserved:
        return [
            tr.CheckInfoLog(
                device=device,
                check=check,
                field="is_reserved",
                measurement=measurement.dict(),
            )
        ]

    # -------------------------------------------------------------------------
    # Check the 'used' status.  Then if the interface is not being used, then no
    # more checks are required.
    # -------------------------------------------------------------------------

    results = list()

    if should_oper_status.used != measurement.used:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="used",
                measurement=measurement.used,
            )
        )

    if not should_oper_status.used:
        return results

    if should_oper_status.oper_up != measurement.oper_up:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="oper_up",
                measurement=measurement.oper_up,
            )
        )

    if should_oper_status.speed != measurement.speed:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="speed",
                measurement=measurement.speed,
            )
        )

    return results
