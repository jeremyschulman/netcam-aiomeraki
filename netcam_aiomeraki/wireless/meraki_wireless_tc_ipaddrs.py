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
from ipaddress import IPv4Interface

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
    from .meraki_wireless_dut import MerakiWirelessDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_wireless_tc_ipaddrs"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_wireless_tc_ipaddrs(
    self, testcases: IPInterfacesTestCases
) -> trt.CollectionTestResults:
    """
    Validate the wireless device configured IP addresses against those defined
    in the design.
    """
    dut: MerakiWirelessDeviceUnderTest = self
    device = dut.device

    # The only IP address to validate is the managment IP assigned on "wan1"
    # interface.

    api_data = await dut.get_mgmt_iface()

    # Form the interface name using the nomencature "Vlan<N>" where <N> is the
    # VlanId.  Note that this convention requires the Designer to create device
    # interfaces with the same naming convention.
    # TODO: Note this in the documentation.

    def _static_ip(_port_data: dict):
        """
        extract the static IP configuration from the API payload and return the
        IP interface as a string with prefixlen nation.
        """
        ifip_str = f"{_port_data['staticIp']}/{_port_data['staticSubnetMask']}"
        return str(IPv4Interface(ifip_str).with_prefixlen)

    map_msrd_ip_config = {
        port_name: _static_ip(port_data) for port_name, port_data in api_data.items()
    }

    results = list()
    if_names = list()

    for test_case in testcases.tests:

        if_name = test_case.test_case_id()
        if_names.append(if_name)

        if not (if_ip_data := map_msrd_ip_config.get(if_name)):
            results.append(
                trt.FailNoExistsResult(
                    device=device, test_case=test_case, field="if_ipaddr"
                )
            )
            continue

        one_results = await _test_one_interface(
            device=device, test_case=test_case, msrd_if_ipaddr=if_ip_data
        )

        results.extend(one_results)

    # Validate the exclusive list of IP addresses expected

    results.extend(
        _test_exclusive_list(
            device=device,
            expd_if_names=if_names,
            msrd_if_names=list(map_msrd_ip_config),
        )
    )

    return results


# -----------------------------------------------------------------------------


async def _test_one_interface(
    device: Device,
    test_case: IPInterfaceTestCase,
    msrd_if_ipaddr: str,
) -> trt.CollectionTestResults:
    """
    Validate one interface on the device against the test case defining the designed
    IP address.
    """

    results = list()

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
            trt.PassTestCase(
                device=device, test_case=test_case, measurement=msrd_if_ipaddr
            )
        )

    return results


def _test_exclusive_list(
    device: Device, expd_if_names: Sequence[str], msrd_if_names: List[str]
) -> trt.CollectionTestResults:
    """
    The previous per-interface checks for any missing; therefore we only need
    to check for any extra interfaces found on the device.
    """

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
