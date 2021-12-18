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

from typing import TYPE_CHECKING, List, Dict, Set, Tuple
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
    from .meraki_ms_dut import MerakiSwitchDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_ms_tc_vlans"]


async def meraki_ms_tc_vlans(
    self, testcases: VlanTestCases
) -> trt.CollectionTestResults:
    dut: MerakiSwitchDeviceUnderTest = self
    device = dut.device
    results = list()

    # the VLANs are obtained from the device ports config

    msrd_ports_config = await dut.get_port_config()

    # get the list of VLAN id values expected on this switch.

    expd_vlan_ids = [tc.expected_results.vlan.vlan_id for tc in testcases.tests]

    all_dev_vlans, map_vl2ifs = _correlate_vlans_to_ports(
        msrd_ports_config, expd_vlan_ids
    )

    results.extend(
        _test_exclusive_list(
            device=device, expected=expd_vlan_ids, measured=all_dev_vlans
        )
    )

    for test_case in testcases.tests:
        results.extend(_test_one_vlan(device, test_case, map_vl2ifs))

    return results


def _correlate_vlans_to_ports(
    port_configs: List, expd_vlan_ids: List
) -> Tuple[Set, Dict]:

    map_vlans_to_interfaces = defaultdict(set)
    all_device_vlans = set()

    def is_unused(_data) -> bool:
        """
        Make a function that mimicks the "unused" setting for a port.  The MS
        devices do not have such a configuration setting (yet).  So we will use
        the following algorithm to declare a port is not used: If the port is
        Access/VLAN-1 and disabled, then usued.

        Parameters
        ----------
        _data: dict
            The port data object from the API

        Returns
        -------
        bool - True if the port is "unused", False otherwise
        """
        return bool(_data["vlan"] == 1 and _data["enabled"] is False)

    for if_data in port_configs:
        if_name = if_data["portId"]

        # if the port is access, then we only have one vlan to contend with.

        if if_data["type"] == "access":
            if is_unused(if_data):
                continue

            # This access port is in use, so account for the VLAN usage, and the
            # continue to the next interface

            vlan_id = if_data["vlan"]
            all_device_vlans.add(vlan_id)
            map_vlans_to_interfaces[vlan_id].add(if_name)

            continue

        # ---------------------------------------------------------------------
        # if here, then port is TRUNK ...
        # ---------------------------------------------------------------------

        # need to account for the 'vlan' (native-vlan) being used by the device.

        all_device_vlans.add(if_data["vlan"])

        # if the trunk is set to allow 'all', then add the interface to all of
        # the expected vlans on the switch.  Otherwise we parse the vlan-string
        # value and add those vlans.

        if (msrd_allowd := if_data["allowedVlans"]) == "all":
            all_intf_vlans = expd_vlan_ids
        else:
            all_intf_vlans = parse_istrange(msrd_allowd)

        all_device_vlans.update(all_intf_vlans)

        for vlan_id in all_intf_vlans:
            map_vlans_to_interfaces[vlan_id].add(if_name)

    # check for the existance of VLAN 1, the default VLAN.  If it does exit and
    # all interfaces associated with VLAN 1 are disabled, then remove VLAN 1
    # from the list of "used" VLANs, since it is really not.

    if vlan_1_ifaces := map_vlans_to_interfaces.get(1):
        disabled = [
            port
            for port in port_configs
            if (port["portId"] in vlan_1_ifaces) and (port["enabled"] is False)
        ]
        if len(disabled) == len(vlan_1_ifaces):
            del map_vlans_to_interfaces[1]

    return all_device_vlans, map_vlans_to_interfaces


def _test_exclusive_list(
    device, expected: List, measured: Set
) -> trt.CollectionTestResults:
    """
    This function checks to see if the measure list of device vlans matches the
    expected list; and generates any failure reports if needed.

    Parameters
    ----------
    device
        The device instance

    expected: list
        The list of all vlan_ids expected to be used on the device

    measured: set
        The set of all vlan_ids that are used on the device

    Returns
    -------
    List of test case measurement results.
    """

    results = list()

    s_expd = set(expected)

    tc = VlanTestCaseExclusiveList()

    if missing_vlans := s_expd - measured:
        results.append(
            trt.FailMissingMembersResult(
                device=device,
                test_case=tc,
                field=tc.test_case,
                expected=sorted(s_expd),
                missing=sorted(missing_vlans),
            )
        )

    if extra_vlans := measured - s_expd:
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
            trt.PassTestCase(device=device, test_case=tc, measurement=sorted(measured))
        )

    return results


def _test_one_vlan(
    device: Device, test_case: VlanTestCase, vlans_to_intfs: dict
) -> trt.CollectionTestResults:

    results = list()

    # The test case ID is the VLAN ID in string form, we will want it as
    # an int since that is how it is stored in the Meraki API.

    vlan_id = int(test_case.test_case_id())

    # The expect list of interface names (ports)
    expd_if_list = test_case.expected_results.interfaces

    msrd_if_set = vlans_to_intfs[vlan_id]

    if msrd_if_set == set(expd_if_list):
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
            expected=sorted(expd_if_list, key=int),
        )
    )

    return results
