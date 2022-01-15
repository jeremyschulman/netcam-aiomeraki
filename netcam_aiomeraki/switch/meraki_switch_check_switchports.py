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

# example = {'portId': '10',
#            'name': None,
#            'tags': [],
#            'enabled': True,
#            'poeEnabled': False,
#            'type': 'trunk',
#            'vlan': 5,
#            'voiceVlan': None,
#            'allowedVlans': 'all',
#            'isolationEnabled': False,
#            'rstpEnabled': True,
#            'stpGuard': 'loop guard',
#            'linkNegotiation': '1 Gigabit full duplex (forced)',
#            'portScheduleId': None,
#            'udld': 'Alert only',
#            'accessPolicyType': 'Open'}

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

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
    from .meraki_switch_dut import MerakiSwitchDeviceUnderTest

from netcad.helpers import range_string

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_switch_check_switchports"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_switch_check_switchports(
    self, check_collection: SwitchportCheckCollection
) -> tr.CheckResultsCollection:
    """
    Validate the device switchport configuration against the design
    expectations.
    """
    dut: MerakiSwitchDeviceUnderTest = self
    device = dut.device
    ports_config = await dut.get_port_config()
    map_ports_config = {rec["portId"]: rec for rec in ports_config}

    results = list()

    for check in check_collection.checks:
        expd_status = check.expected_results

        if_name = check.check_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next test-case.

        if not (msrd_port := map_ports_config.get(if_name)):
            results.append(tr.CheckFailNoExists(device=device, check=check))
            continue

        # check the switchport mode value.  If they do not match, then we report
        # the error and continue to the next test-case.

        expd_mode = expd_status.switchport_mode
        msrd_mode = msrd_port["type"]

        if expd_mode != msrd_mode:
            results.append(
                tr.CheckFailFieldMismatch(
                    device=device,
                    check=check,
                    field="switchport_mode",
                    measurement=msrd_mode,
                )
            )
            continue

        mode_handler = {
            "access": _check_access_switchport,
            "trunk": _check_trunk_switchport,
        }.get(expd_mode)

        results.extend(mode_handler(dut, check, expd_status, msrd_port))

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
    dut, check, expd_status: SwitchportTrunkExpectation, msrd_status: dict
) -> tr.CheckResultsCollection:
    """
    Check one interface that is a TRUNK port.
    """
    device = dut.device
    results = list()

    # if there is a native vlan expected, then validate the match.

    n_vl_id = expd_status.native_vlan.vlan_id if expd_status.native_vlan else None
    if n_vl_id and (msrd_vl_id := msrd_status["vlan"]) != n_vl_id:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="native_vlan",
                expected=n_vl_id,
                measurement=msrd_vl_id,
            )
        )

    # the trunk is either "all" or a CSV of vlans

    msrd_allowd_vlans = msrd_status["allowedVlans"]

    # if all, then done checking; really should not be using "all", so log an info.

    if msrd_allowd_vlans == "all":
        if not results:
            results.append(
                tr.CheckPassResult(device=device, check=check, measurement=msrd_status)
            )

        results.append(
            tr.CheckInfoLog(
                device=device,
                check=check,
                measurement="trunk port allows 'all' vlans",
            )
        )
        return results

    e_tr_allowed_vids = sorted(
        [vlan.vlan_id for vlan in expd_status.trunk_allowed_vlans]
    )

    # conver the list of vlan-ids to a range string for string comparison
    # purposes.

    e_tr_alwd_vstr = range_string(e_tr_allowed_vids)
    if e_tr_alwd_vstr != msrd_allowd_vlans:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="trunk_allowed_vlans",
                expected=e_tr_alwd_vstr,
                measurement=msrd_allowd_vlans,
            )
        )

    if not results:
        results = [
            tr.CheckPassResult(device=device, check=check, measurement=msrd_status)
        ]

    return results
