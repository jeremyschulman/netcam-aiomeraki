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

from macaddr import MacAddress

from netcad.topology.tc_cabling_nei import (
    InterfaceCablingTestCases,
    InterfaceCablingTestCase,
)
from netcad.topology.utils_cabling_nei import (
    nei_interface_match,
    nei_hostname_match,
)

from netcad.netcam import any_failures, tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_ms_dut import MerakiMSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_ms_tc_cabling"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_ms_tc_cabling(
    self, testcases: InterfaceCablingTestCases
) -> trt.CollectionTestResults:

    dut: MerakiMSDeviceUnderTest = self
    device = dut.device

    api_data = await dut.get_port_status()

    map_msrd_ports_status = {port["portId"]: port for port in api_data}

    results = list()

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()

        if not (msrd_nei_status := map_msrd_ports_status.get(if_name)):
            results.append(trt.FailNoExistsResult(device=device, test_case=test_case))
            continue

        if msrd_lldp_nei := msrd_nei_status.get("lldp"):
            results.extend(
                _test_one_lldp_interface(
                    device=device, test_case=test_case, msrd_lldp_nei=msrd_lldp_nei
                )
            )
        elif msrd_cdp_nei := msrd_nei_status.get("cdp"):
            nei_res = await _test_one_cdp_interface(
                dut=dut, test_case=test_case, msrd_cdp_nei=msrd_cdp_nei
            )
            results.extend(nei_res)
        else:
            results.append(
                trt.FailNoExistsResult(
                    device=device,
                    test_case=test_case,
                    error=dict(
                        message="Unexpcted API payload missing cdp|lldp",
                        expected=test_case.expected_results.dict(),
                    ),
                )
            )

    return results


# -----------------------------------------------------------------------------
#
#                             PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


async def _test_one_cdp_interface(
    dut: "MerakiMSDeviceUnderTest",
    test_case: InterfaceCablingTestCase,
    msrd_cdp_nei: dict,
) -> trt.CollectionTestResults:

    # results = list()
    device = dut.device

    # For now we are going to expect the deviceId is a MAC address, and that MAC
    # is associated with another Meraki device.  If this is not the case, then
    # this CDP check is not supported, and will result in a failure measurement.

    if "Meraki" not in (msrd_platform := (msrd_cdp_nei.get("platform", ""))):
        return [
            trt.FailNoExistsResult(
                device=device,
                test_case=test_case,
                error=dict(
                    message=f'CDP platform is not Meraki as expected: "{msrd_platform}"',
                    expected=test_case.expected_results.dict(),
                ),
            )
        ]

    cdp_device_id = msrd_cdp_nei.get("deviceId", "")

    try:
        cdp_device_mac = MacAddress(cdp_device_id)  # noqa

    except ValueError:
        return [
            trt.FailNoExistsResult(
                device=device,
                test_case=test_case,
                error=dict(
                    message=f'CDP device ID not MAC as expected: "{cdp_device_id}"',
                    expected=test_case.expected_results.dict(),
                ),
            )
        ]

    # Now that we have a known Meraki MAC address, we need to locate the device
    # in the Meraki inventory.

    # cdp_dev_obj = await dut.get_inventory_device(mac=str(cdp_device_mac))  # noqa

    # TODO: need to finish this coding, but not needed right now
    # TODO: unfinished business ....

    raise NotImplementedError("Meraki Switch CDP cabling check")


def meraki_hostname_match(expected, measured: str):
    if not measured.startswith("Meraki"):
        return False

    return expected == measured.split()[-1]


def _test_one_lldp_interface(
    device, test_case: InterfaceCablingTestCase, msrd_lldp_nei: dict
) -> trt.CollectionTestResults:
    results = list()

    expd_nei = test_case.expected_results

    msrd_name = msrd_lldp_nei["systemName"]
    msrd_port_id = msrd_lldp_nei["portId"]

    # ensure the expected hostname matches

    if not nei_hostname_match(expd_nei.device, msrd_name) and not meraki_hostname_match(
        expd_nei.device, msrd_name
    ):
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="device",
                measurement=msrd_name,
            )
        )

    # ensure the expected pot-id matches

    if not nei_interface_match(expd_nei.port_id, msrd_port_id):
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="port_id",
                measurement=msrd_port_id,
            )
        )

    # if there are no failures then report the test case passes

    if not any_failures(results):
        results.append(
            trt.PassTestCase(
                device=device, test_case=test_case, measurement=msrd_lldp_nei
            )
        )

    return results
