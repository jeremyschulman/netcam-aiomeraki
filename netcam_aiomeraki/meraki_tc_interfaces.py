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

from typing import TYPE_CHECKING, Dict, Optional

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from netcad.device import Device
from netcad.netcam import tc_result_types as tr
from netcad.phy_port import PhyPortSpeeds

from netcad.topology.tc_interfaces import (
    InterfaceTestCases,
    InterfaceTestCase,
)


# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_dut import MerakiDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_tc_interfaces"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_tc_interfaces(
    self, testcases: InterfaceTestCases
) -> Optional[tr.CollectionTestResults]:
    dut: MerakiDeviceUnderTest = self

    # The "MX" platform interface status checks are currently not supported.
    # TODO: investigating the Meraki Dashboard API for support.
    #       https://github.com/meraki/dashboard-api-python/issues

    if dut.model.startswith("MX"):
        return None

    # For now, supporting MS switch product
    results = await _meraki_switch_tc_interfaces(dut, testcases)
    return results


async def _meraki_switch_tc_interfaces(
    dut, testcases: InterfaceTestCases
) -> Optional[tr.CollectionTestResults]:

    device = dut.device
    map_port_status = await get_ports_status(dut)
    results = list()

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()

        if not (msrd_status := map_port_status.get(if_name)):
            # design is attempting to use an interface that does not exist on
            # the device.  Report this as an error, and continue to next
            # test-case.
            results.append(tr.FailNoExistsResult(device=device, test_case=test_case))
            continue

        results_iface = meraki_check_switch_one_interface(
            device=device, test_case=test_case, measurement=msrd_status
        )

        if not any(isinstance(res, tr.FailTestCase) for res in results_iface):
            results_iface.append(
                tr.PassTestCase(
                    device=device, test_case=test_case, measurement=msrd_status.dict()
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
    if not speed_str:
        return 0

    if speed_str == "1 Gbps":
        return PhyPortSpeeds.speed_1G

    raise RuntimeError(f"Unknown Meraki speed converstion for: {speed_str}")


class SwitchInterfaceMeasurement(BaseModel):
    used: bool
    oper_up: bool
    speed: int

    @classmethod
    def from_api(cls, api_payload: dict):
        return cls(
            used=api_payload["enabled"] is True,
            oper_up=api_payload["status"] == "Connected",
            speed=meraki_to_speed(api_payload["speed"]),
        )


async def get_ports_status(dut: "MerakiDeviceUnderTest") -> Dict:
    model = dut.meraki_device["model"]

    if model.startswith("MS"):
        async with dut.meraki_api() as api:
            status_list = await api.switch.getDeviceSwitchPortsStatuses(
                serial=dut.serial
            )

        return {
            port_st["portId"]: SwitchInterfaceMeasurement.from_api(port_st)
            for port_st in status_list
        }

    else:
        raise RuntimeError(
            f"{dut.device.name}: Unsupported: Meraki device port status for model: {model}"
        )

    # elif model.startswith("MX"):
    #     net_id = dut.meraki_device["networkId"]
    #
    #     async with dut.meraki_api() as api:
    #         status_list = await api.appliance.getNetworkAppliancePorts(
    #             networkId=net_id,
    #         )


def meraki_check_switch_one_interface(
    device: Device,
    test_case: InterfaceTestCase,
    measurement: SwitchInterfaceMeasurement,
) -> tr.CollectionTestResults:

    if_flags = test_case.test_params.interface_flags or {}
    is_reserved = if_flags.get("is_reserved", False)
    should_oper_status = test_case.expected_results

    # -------------------------------------------------------------------------
    # If the interface is marked as reserved, then report the current state in
    # an INFO report and done with this test-case.
    # -------------------------------------------------------------------------

    if is_reserved:
        return [
            tr.InfoTestCase(
                device=device,
                test_case=test_case,
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
            tr.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="used",
                measurement=measurement.used,
            )
        )

    if not should_oper_status.used:
        return results

    if should_oper_status.oper_up != measurement.oper_up:
        results.append(
            tr.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="oper_up",
                measurement=measurement.oper_up,
            )
        )

    if should_oper_status.speed != measurement.speed:
        results.append(
            tr.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="speed",
                measurement=measurement.speed,
            )
        )

    return results
