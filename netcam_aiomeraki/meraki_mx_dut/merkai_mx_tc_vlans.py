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
from collections import defaultdict

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.netcam import any_failures, tc_result_types as trt
from netcad.vlan.tc_vlans import VlanTestCases, VlanTestCase, VlanTestCaseExclusiveList
from netcad.helpers import parse_istrange

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_mx_dut import MerakiMXDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_mx_tc_vlans"]


async def meraki_mx_tc_vlans(
    self, testcases: VlanTestCases
) -> trt.CollectionTestResults:
    dut: MerakiMXDeviceUnderTest = self
    device = dut.device
    results = list()

    # the VLANs are obtained from the device ports config

    msrd_ports_config = await dut.get_switchports()

    # get the list of VLAN id values expected on this switch, for only those
    # VLANs that have interfaces assigned.  There are some cases where the VLAN
    # is defined, but no interfaces; for example the native VLAN on trunk ports.

    expd_vlan_ids = [
        tc.expected_results.vlan.vlan_id
        for tc in testcases.tests
        if tc.expected_results.interfaces
    ]

    map_vl2ifs = _correlate_vlans_to_ports(msrd_ports_config, expd_vlan_ids)

    results.extend(
        _test_exclusive_list(device=device, expected=expd_vlan_ids, measured=map_vl2ifs)
    )

    for test_case in testcases.tests:
        results.extend(_test_one_vlan(device, test_case, map_vl2ifs))

    return results


def _correlate_vlans_to_ports(port_configs: List, expd_vlan_ids: List) -> Dict:

    map_vlans_to_interfaces = defaultdict(set)

    def is_unused_port(_data):
        return (
            _data["enabled"] is False
            and _data["type"] == "trunk"
            and _data["dropUntaggedTraffic"] is True
        )

    for if_data in port_configs:

        if is_unused_port(if_data):
            continue

        if_name = str(if_data["number"])

        # if the port is access, then we only have one vlan to contend with.

        if vlan_id := if_data.get("vlan"):
            map_vlans_to_interfaces[vlan_id].add(if_name)

        if if_data["type"] == "access":
            continue

        # if the trunk is set to allow 'all', then add the interface to all of
        # the expected vlans on the switch.  Otherwise we parse the vlan-string
        # value and add those vlans.

        if (msrd_allowd := if_data["allowedVlans"]) == "all" and (
            if_data["enabled"] is True
        ):
            add_vlan_ids = expd_vlan_ids
        else:
            add_vlan_ids = parse_istrange(msrd_allowd)

        for vlan_id in add_vlan_ids:
            map_vlans_to_interfaces[vlan_id].add(if_name)

    # check for the existance of VLAN 1, the default VLAN.  If it does exit and
    # all interfaces associated with VLAN 1 are disabled, then remove VLAN 1
    # from the list of "used" VLANs, since it is really not.

    if vlan_1_ifaces := map_vlans_to_interfaces.get(1):
        disabled = [
            port
            for port in port_configs
            if (str(port["number"]) in vlan_1_ifaces) and (port["enabled"] is False)
        ]
        if len(disabled) == len(vlan_1_ifaces):
            del map_vlans_to_interfaces[1]

    return map_vlans_to_interfaces


def _test_exclusive_list(device, expected, measured) -> trt.CollectionTestResults:

    results = list()

    s_expd = set(expected)
    s_msrd = set(measured)

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
            trt.PassTestCase(device=device, test_case=tc, measurement=sorted(s_msrd))
        )

    return results


def _test_one_vlan(
    device: Device, test_case: VlanTestCase, vlans_to_intfs: dict
) -> trt.CollectionTestResults:

    results = list()

    # The test case ID is the VLAN ID in string form, we will want it as
    # an int since that is how it is stored in the Meraki API.

    vlan_id = int(test_case.test_case_id())

    # The expect list of interface names (ports), exclude the "Vlan" SVI
    # interfaces, as those are checked by the "ipaddrs" test-case processing.

    expd_if_set = {
        if_name
        for if_name in test_case.expected_results.interfaces
        if not if_name.startswith("Vlan")
    }

    msrd_if_set = vlans_to_intfs[vlan_id]

    if msrd_if_set == expd_if_set:
        return [
            trt.PassTestCase(
                device=device, test_case=test_case, measurement=sorted(msrd_if_set)
            )
        ]

    results.append(
        trt.FailFieldMismatchResult(
            device,
            test_case,
            "interfaces",
            measurement=sorted(msrd_if_set, key=int),
            expected=sorted(expd_if_set, key=int),
        )
    )

    return results
