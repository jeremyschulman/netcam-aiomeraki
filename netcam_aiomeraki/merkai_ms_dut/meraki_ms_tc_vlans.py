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

from typing import TYPE_CHECKING, List, Dict

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.netcam import any_failures, tc_result_types as trt
from netcad.vlan.tc_vlans import VlanTestCases, VlanTestCase, VlanTestCaseExclusiveList

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_ms_dut import MerakiMSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_ms_tc_vlans"]


async def meraki_ms_tc_vlans(
    self, testcases: VlanTestCases
) -> trt.CollectionTestResults:
    dut: MerakiMSDeviceUnderTest = self
    device = dut.device
    results = list()

    # the VLANs are obtained from the device ports config

    msrd_ports_config = await dut.get_port_config()

    results.extend(
        _test_exclusive_list(
            device=device, testcases=testcases, msrd_ports_config=msrd_ports_config
        )
    )

    for test_case in testcases.tests:
        results.extend(_test_one_vlan(device, test_case, msrd_ports_config))

    return results


def _test_exclusive_list(
    device, testcases: VlanTestCases, msrd_ports_config: List[Dict]
) -> trt.CollectionTestResults:

    results = list()

    expd_vlan_ids = [tc.expected_results.vlan.vlan_id for tc in testcases.tests]

    # collect the "access"/"native" vlan IDs
    msrd_vlan_ids = [port["vlan"] for port in msrd_ports_config]

    # TODO: collect the "allowed vlans".  For now, all use-cases are using the
    #       value of 'all'.  So need to find some lab/test infrastructure to
    #       dev-test this use case.

    s_expd = set(expd_vlan_ids)
    s_msrd = set(msrd_vlan_ids)

    tc = VlanTestCaseExclusiveList()

    if missing_vlans := s_expd - s_msrd:
        results.append(
            trt.FailMissingMembersResult(
                device=device,
                test_case=tc,
                field=tc.test_case,
                expected=sorted(s_expd),
                missing=sorted(missing_vlans),
            )
        )

    if extra_vlans := s_msrd - s_expd:
        results.append(
            trt.FailExtraMembersResult(
                device=device,
                test_case=tc,
                field=tc.test_case,
                expected=sorted(s_expd),
                extras=sorted(extra_vlans),
            )
        )

    if not any_failures(results):
        results.append(
            trt.PassTestCase(device=device, test_case=tc, measurement=msrd_vlan_ids)
        )

    return results


def _test_one_vlan(
    device: Device, test_case: VlanTestCase, map_port_configs: List
) -> trt.CollectionTestResults:

    results = list()

    # The test case ID is the VLAN ID in string form, we will want it as
    # an int since that is how it is stored in the Meraki API.

    vlan_id = int(test_case.test_case_id())

    # The expect list of interface names (ports)
    expd_if_list = test_case.expected_results.interfaces

    # find all interfaces where this vlan ID is located.  We check both the
    # 'vlan' field for now

    msrd_if_list = set()

    for if_data in map_port_configs:

        if_name = if_data["portId"]
        if if_data["vlan"] == vlan_id:
            msrd_if_list.add(if_name)

        if if_data["type"] == "trunk" and if_data["allowedVlans"] == "all":
            msrd_if_list.add(if_name)

    if msrd_if_list != set(expd_if_list):
        results.append(
            trt.FailFieldMismatchResult(
                device,
                test_case,
                "interfaces",
                measurement=sorted(msrd_if_list, key=int),
                expected=sorted(expd_if_list, key=int),
            )
        )

    return results
