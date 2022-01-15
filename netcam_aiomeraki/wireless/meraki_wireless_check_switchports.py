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

import asyncio
from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam import any_failures
from netcad.checks import check_result_types as tr

from netcad.vlans.checks.check_switchports import (
    SwitchportCheckCollection,
    SwitchportAccessExpectation,
    SwitchportTrunkExpectation,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_wireless_dut import MerakiWirelessDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_wireless_check_switchports"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_wireless_check_switchports(
    self, check_collection: SwitchportCheckCollection
) -> tr.CheckResultsCollection:
    """
    The Meraki APs are not technically "switches", but the construct of switchports and
    VLANs can be made by examining the SSID configurations for vlans in use.

    Notes
    -----
    Presently this code only supports Network wide SSID assignments and not
    per-AP SSID/VLAN assignments

    Returns
    -------
    List of test case results
    """

    dut: MerakiWirelessDeviceUnderTest = self
    device = dut.device

    # The VLANs used on the AP device include those configured on the SSIDs as
    # we as one used for the managmeent interface of the AP itself.

    api_ssid_data, api_mgmt_data = await asyncio.gather(
        dut.get_ssids(), dut.get_mgmt_iface()
    )

    msrd_vlan_ids = {
        ssid_rec["defaultVlanId"]
        for ssid_rec in api_ssid_data
        if ssid_rec.get("useVlanTagging", False) is True
    }

    if vlan_mgmt := api_mgmt_data["wan1"].get("vlan"):
        msrd_vlan_ids.add(vlan_mgmt)

    # for now, the only "status" is the set of VLANs used by the SSIDs

    map_msrd_status = dict(wired0=msrd_vlan_ids)

    # technical speaking, at this time, there is only one interface test case
    # for "wired0".  We will leave the looping construct here for now in case
    # something new comes out in the product line; or we find new information
    # about the behavior of the AP.

    results = list()
    for check in check_collection.checks:
        expd_status = check.expected_results

        if_name = check.check_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next test-case.

        if not (msrd_port := map_msrd_status.get(if_name)):
            results.append(tr.CheckFailNoExists(device=device, check=check))
            continue

        # check the switchport mode value.  If they do not match, then we report
        # the error and continue to the next test-case.

        # TODO: find where in the AP API there is the configuraiton for trunk
        #       vs. access mode (if there is one).  For now we will skip the
        #       switchport.mode check.

        mode_results = _check_trunk_switchport(dut, check, expd_status, msrd_port)
        results.extend(mode_results)

        if not any_failures(mode_results):
            results.append(
                tr.CheckPassResult(device=device, check=check, measurement=msrd_port)
            )

    return results


def _check_access_switchport(
    dut, check, expd_status: SwitchportAccessExpectation, msrd_status: dict
) -> tr.CheckResultsCollection:
    """
    Only one check for now, that is to validate that the configured VLAN on the
    access port matches the test case.
    """
    device = dut.device
    vl_id = expd_status.vlan.vlan_id
    results = list()

    if vl_id and (msrd_vl_id := msrd_status["vlan"]) != vl_id:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="vlan",
                expected=vl_id,
                measurement=msrd_vl_id,
            )
        )

    return results


def _check_trunk_switchport(
    dut, check, expd_status: SwitchportTrunkExpectation, msrd_status: set
) -> tr.CheckResultsCollection:
    """
    Validate the wireless device is configured as defined relative to the
    VLANs used and the configuraiton of the wired0 port.
    """

    device = dut.device
    results = list()

    # if there is a native vlan expected, then validate the match.

    # TODO: need to determine if/how to validate the native-vlan setting.  Need
    #       to find this in the API.

    expd_set = {vlan.vlan_id for vlan in expd_status.trunk_allowed_vlans}

    msrd_set = msrd_status

    if expd_set != msrd_set:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="trunk_allowed_vlans",
                expected=sorted(expd_set),
                measurement=sorted(msrd_set),
            )
        )

    return results
