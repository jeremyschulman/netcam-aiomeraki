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

        results.extend(
            _test_one_interface(
                device=device, test_case=test_case, measurement=msrd_nei_status
            )
        )

    return results


# -----------------------------------------------------------------------------
#
#                             PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def meraki_hostname_match(expected, measured: str):
    if not measured.startswith("Meraki"):
        return False

    return expected == measured.split()[-1]


def _test_one_interface(
    device, test_case: InterfaceCablingTestCase, measurement: dict
) -> trt.CollectionTestResults:
    results = list()

    expd_nei = test_case.expected_results

    # for now only checking the LLDP status; not checking CDP.
    # TODO: possibly support CDP if/when necessary

    if not (msrd_nei := measurement.get("lldp")):
        results.append(
            trt.FailNoExistsResult(
                device=device, test_case=test_case, measurement=measurement
            )
        )
        return results

    msrd_name = msrd_nei["systemName"]
    msrd_port_id = msrd_nei["portId"]

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

    if not nei_interface_match(expd_nei.port_id, msrd_port_id):
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="port_id",
                measurement=msrd_port_id,
            )
        )

    if not any_failures(results):
        results.append(
            trt.PassTestCase(
                device=device, test_case=test_case, measurement=measurement
            )
        )

    return results
