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

from typing import TYPE_CHECKING, List, Dict, Set
from collections import defaultdict

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt
from netcad.vlan import VlanProfile
from netcad.vlan.check_vlans import (
    VlanCheckCollection,
    VlanCheck,
    VlanCheckExclusiveList,
)
from netcad.helpers import parse_istrange

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_appliance_dut import MerakiApplianceDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_appliance_check_vlans"]


async def meraki_appliance_check_vlans(
    self, check_collection: VlanCheckCollection
) -> trt.CheckResultsCollection:
    """
    Validate the device use of VLANs against the design expectations.
    """
    dut: MerakiApplianceDeviceUnderTest = self
    device = dut.device
    results = list()

    # the VLANs are obtained from the device ports config

    msrd_ports_config = await dut.get_switchports()

    # get the list of VLAN id values expected on this switch, for only those
    # VLANs that have interfaces assigned.  There are some cases where the VLAN
    # is defined, but no interfaces; for example the native VLAN on trunk ports.

    expd_vlans = [
        check.expected_results.vlan
        for check in check_collection.checks
        if check.expected_results.interfaces
    ]

    map_vl2ifs = _correlate_vlans_to_ports(msrd_ports_config, expd_vlans)

    results.extend(
        _check_exclusive_list(
            device=device,
            check=check_collection.exclusive,
            expd_vlan_ids={vlan.vlan_id for vlan in expd_vlans},
            msrd_vlan_ids=set(map_vl2ifs),
        )
    )

    for check in check_collection.checks:
        results.extend(_check_one_vlan(device, check, map_vl2ifs))

    return results


def _correlate_vlans_to_ports(
    port_configs: List, expd_vlans: List[VlanProfile]
) -> Dict:
    """
    The API does not provide a means to correlate the interfaces to VLANs as one
    would find in other swtich products.  This function computes that mapping
    based on the port configuration.
    """

    map_vlans_to_interfaces = defaultdict(set)
    expd_vlan_ids = [vlan.vlan_id for vlan in expd_vlans]

    def is_unused_port(_data):
        """
        Represent whether or not a port is "used" by the device by examing the
        state of the port.  If the port is disabled and in trunk mode and
        dropped traffic set to True, then we declare that port "unused".
        """
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


def _check_exclusive_list(
    device,
    check: VlanCheckExclusiveList,
    expd_vlan_ids: Set[int],
    msrd_vlan_ids: Set[int],
) -> trt.CheckResultsCollection:
    """
    Validate the exclusive list of VLANs used by the device against the design
    expectation.
    """
    results = list()

    if missing_vlans := expd_vlan_ids - msrd_vlan_ids:
        results.append(
            trt.CheckFailMissingMembers(
                device=device,
                check=check,
                field=check.check_type,
                expected=sorted(expd_vlan_ids),
                missing=sorted(missing_vlans),
            )
        )

    if extra_vlans := msrd_vlan_ids - expd_vlan_ids:
        results.append(
            trt.CheckFailExtraMembers(
                device=device,
                check=check,
                field=check.check_type,
                expected=sorted(expd_vlan_ids),
                extras=sorted(extra_vlans),
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(
                device=device, check=check, measurement=sorted(msrd_vlan_ids)
            )
        )

    return results


def _check_one_vlan(
    device: Device, check: VlanCheck, vlans_to_intfs: dict
) -> trt.CheckResultsCollection:
    """
    Test one VLAN use of related interfaces against the design expectations.
    """

    results = list()

    # The test case ID is the VLAN ID in string form, we will want it as
    # an int since that is how it is stored in the Meraki API.

    vlan_id = int(check.check_id())

    # The expect list of interface names (ports), exclude the "Vlan" SVI
    # interfaces, as those are checked by the "ipaddrs" test-case processing.

    expd_if_set = {
        if_name
        for if_name in check.expected_results.interfaces
        if not if_name.startswith("Vlan")
    }

    msrd_if_set = vlans_to_intfs[vlan_id]

    if msrd_if_set == expd_if_set:
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
            expected=sorted(expd_if_set, key=int),
        )
    )

    return results
