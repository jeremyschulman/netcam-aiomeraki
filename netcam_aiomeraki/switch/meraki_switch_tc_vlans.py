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
from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt
from netcad.vlans.checks.check_vlans import (
    VlanCheckCollection,
    VlanCheck,
    VlanCheckExclusiveList,
)
from netcad.helpers import parse_istrange

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_switch_dut import MerakiSwitchDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_switch_check_vlans"]


async def meraki_switch_check_vlans(
    self, check_collection: VlanCheckCollection
) -> trt.CheckResultsCollection:
    """
    Validate the switch set of used VLANs against those defined in the design.
    """
    dut: MerakiSwitchDeviceUnderTest = self
    device = dut.device
    results = list()

    # the VLANs are obtained from the device ports config

    msrd_ports_config = await dut.get_port_config()

    # get the list of VLAN id values expected on this switch.

    expd_vlan_ids = [
        check.expected_results.vlan.vlan_id for check in check_collection.checks
    ]

    all_dev_vlans, map_vl2ifs = _correlate_vlans_to_ports(
        msrd_ports_config, expd_vlan_ids
    )

    results.extend(
        _check_exclusive_list(
            device=device, check=check_collection.exclusive, measured=all_dev_vlans
        )
    )

    for test_case in check_collection.checks:
        results.extend(_test_one_vlan(device, test_case, map_vl2ifs))

    return results


def _correlate_vlans_to_ports(
    port_configs: List, expd_vlan_ids: List
) -> Tuple[Set, Dict]:
    """
    The switch API does not have a route that gives the interface to VLAN mapping directly,
    so this function is used to build that correlation.

    Parameters
    ----------
    port_configs: list[dict]
        The list of port config objects as returned from the Merak API

    expd_vlan_ids:
        The List of VLANs as defined in the design.

    Returns
    -------
    Tuple:
        Set of all VLAN-IDs used by the device
        Dict: maaping of VLANs to interfaces using each Vlan.
            key=vlan-id,
            value=set of interfaec names usiing that vlan
    """
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


def _check_exclusive_list(
    device, check: VlanCheckExclusiveList, measured: Set
) -> trt.CheckResultsCollection:
    """
    This function checks to see if the measure list of device vlans matches the
    expected list; and generates any failure reports if needed.

    Parameters
    ----------
    device
        The device instance

    check: VlanCheckExclusiveList
        The check instance containing the expected exclusive list of VLANs.

    measured: set
        The set of all vlan_ids that are used on the device

    Returns
    -------
    List of test case measurement results.
    """

    results = list()

    s_expd = {vlan.vlan_id for vlan in check.expected_results.vlans}

    if missing_vlans := s_expd - measured:
        results.append(
            trt.CheckFailMissingMembers(
                device=device,
                check=check,
                field=check.check_type,
                expected=sorted(s_expd),
                missing=sorted(missing_vlans),
            )
        )

    if extra_vlans := measured - s_expd:
        results.append(
            trt.CheckFailExtraMembers(
                device=device,
                check=check,
                field=check.check_type,
                expected=sorted(s_expd),
                extras=sorted(extra_vlans),
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(
                device=device, check=check, measurement=sorted(measured)
            )
        )

    return results


def _test_one_vlan(
    device: Device, check: VlanCheck, vlans_to_intfs: dict
) -> trt.CheckResultsCollection:
    """
    Check the device configuration for a specific VLAN->interfaces usage against
    the expected interfaces in the design.
    """
    results = list()

    # The test case ID is the VLAN ID in string form, we will want it as
    # an int since that is how it is stored in the Meraki API.

    vlan_id = int(check.check_id())

    # The expect list of interface names (ports)
    expd_if_list = check.expected_results.interfaces

    msrd_if_set = vlans_to_intfs[vlan_id]

    if msrd_if_set == set(expd_if_list):
        return [
            trt.CheckPassResult(
                device=device, check=check, measurement=sorted(msrd_if_set)
            )
        ]

    results.append(
        trt.CheckFailFieldMismatch(
            device,
            check=check,
            field="interfaces",
            measurement=sorted(msrd_if_set, key=int),
            expected=sorted(expd_if_list, key=int),
        )
    )

    return results
