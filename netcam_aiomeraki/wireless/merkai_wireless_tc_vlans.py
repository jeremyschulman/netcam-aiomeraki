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
import asyncio

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt
from netcad.vlan.check_vlans import VlanCheckCollection, VlanCheckExclusiveList

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_wireless_dut import MerakiWirelessDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_wireless_tc_vlans"]


async def meraki_wireless_tc_vlans(
    self, testcases: VlanCheckCollection
) -> trt.CheckResultsCollection:
    """
    This code is basically the same from the "switchports" test executor; so we'll lift
    that code here.
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

    expd_vlan_ids = {
        tc.expected_results.vlan.vlan_id
        for tc in testcases.checks
        if tc.expected_results.interfaces
    }

    # for the wireless APs, since they are not a switch and all VLANs are
    # carried on the same wired0 (for now), we will only check the exclusive
    # list of expected vlan IDs

    return _test_exclusive_list(device, expected=expd_vlan_ids, measured=msrd_vlan_ids)


def _test_exclusive_list(device, expected, measured) -> trt.CheckResultsCollection:
    """
    Validate the wireless device is configured with the exclusive list of VLANs
    as defined in the design.
    """
    results = list()

    tc = VlanCheckExclusiveList()

    if missing_vlans := expected - measured:
        results.append(
            trt.CheckFailMissingMembers(
                device=device,
                check=tc,
                field=tc.check_type,
                expected=sorted(expected),
                missing=sorted(missing_vlans),
            )
        )

    if extra_vlans := measured - expected:
        results.append(
            trt.CheckFailExtraMembers(
                device=device,
                check=tc,
                field=tc.check_type,
                expected=sorted(expected),
                extras=sorted(extra_vlans),
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(device=device, check=tc, measurement=sorted(measured))
        )

    return results
