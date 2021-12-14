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
from typing import Sequence, List

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.tc_ipaddrs import (
    IPInterfacesTestCases,
    IPInterfaceTestCase,
    IPInterfaceExclusiveListTestCase,
)

from netcad.device import Device
from netcad.netcam import any_failures, tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_appliance_dut import MerakiMXDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_mx_tc_ipaddrs"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_mx_tc_ipaddrs(
    self, testcases: IPInterfacesTestCases
) -> trt.CollectionTestResults:

    dut: MerakiMXDeviceUnderTest = self
    device = dut.device

    # The IP addresses to check come from the VLAN/Address configuration

    api_data = await dut.get_vlans()

    # Form the interface name using the nomencature "Vlan<N>" where <N> is the
    # VlanId.  Note that this convention requires the Designer to create device
    # interfaces with the same naming convention.
    # TODO: Note this in the documentation.

    map_msrd_svi_config = {f"Vlan{rec['id']}": rec for rec in api_data}

    results = list()
    if_names = list()

    for test_case in testcases.tests:

        if_name = test_case.test_case_id()
        if_names.append(if_name)

        if not (if_ip_data := map_msrd_svi_config.get(if_name)):
            results.append(
                trt.FailNoExistsResult(
                    device=device, test_case=test_case, field="if_ipaddr"
                )
            )
            continue

        one_results = await _test_one_interface(
            device=device, test_case=test_case, msrd_data=if_ip_data
        )

        results.extend(one_results)

    # Validate the exclusive list of IP addresses expected

    results.extend(
        _test_exclusive_list(
            device=device,
            expd_if_names=if_names,
            msrd_if_names=list(map_msrd_svi_config),
        )
    )

    return results


# -----------------------------------------------------------------------------


async def _test_one_interface(
    device: Device,
    test_case: IPInterfaceTestCase,
    msrd_data: dict,
) -> trt.CollectionTestResults:

    results = list()

    msrd_if_addr = msrd_data["applianceIp"]
    msrd_if_pflen = msrd_data["subnet"].split("/")[-1]
    msrd_if_ipaddr = f"{msrd_if_addr}/{msrd_if_pflen}"

    # -------------------------------------------------------------------------
    # Ensure the IP interface value matches.
    # -------------------------------------------------------------------------

    expd_if_ipaddr = test_case.expected_results.if_ipaddr

    if msrd_if_ipaddr != expd_if_ipaddr:
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="if_ipaddr",
                measurement=msrd_if_ipaddr,
            )
        )

    if not any_failures(results):
        results.append(
            trt.PassTestCase(device=device, test_case=test_case, measurement=msrd_data)
        )

    return results


def _test_exclusive_list(
    device: Device, expd_if_names: Sequence[str], msrd_if_names: List[str]
) -> trt.CollectionTestResults:

    # the previous per-interface checks for any missing; therefore we only need
    # to check for any extra interfaces found on the device.

    tc = IPInterfaceExclusiveListTestCase()

    if extras := set(msrd_if_names) - set(expd_if_names):
        result = trt.FailExtraMembersResult(
            device=device,
            test_case=tc,
            field="exclusive_list",
            expected=sorted(expd_if_names),
            extras=sorted(extras),
        )
    else:
        result = trt.PassTestCase(
            device=device, test_case=tc, measurement=msrd_if_names
        )

    return [result]
