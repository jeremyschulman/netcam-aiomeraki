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

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam import tc_result_types as tr, any_failures
from netcad.helpers import parse_istrange

from netcad.vlan.tc_switchports import (
    SwitchportTestCases,
    SwitchportAccessExpectation,
    SwitchportTrunkExpectation,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_mx_dut import MerakiMXDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_mx_tc_switchports"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_mx_tc_switchports(
    self, testcases: SwitchportTestCases
) -> tr.CollectionTestResults:

    dut: MerakiMXDeviceUnderTest = self
    device = dut.device

    # The MX port data stores the port number as an int; need to convert to str
    # to conform with test case id value.

    api_data = await dut.get_switchports()
    map_msrd_ports_lldpnei = {str(rec["number"]): rec for rec in api_data}

    results = list()

    for test_case in testcases.tests:
        expd_status = test_case.expected_results

        if_name = test_case.test_case_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next test-case.

        if not (msrd_port := map_msrd_ports_lldpnei.get(if_name)):
            results.append(tr.FailNoExistsResult(device=device, test_case=test_case))
            continue

        # check the switchport mode value.  If they do not match, then we report
        # the error and continue to the next test-case.

        expd_mode = expd_status.switchport_mode
        msrd_mode = msrd_port["type"]

        if expd_mode != msrd_mode:
            results.append(
                tr.FailFieldMismatchResult(
                    device=device,
                    test_case=test_case,
                    field="switchport_mode",
                    measurement=msrd_mode,
                )
            )
            continue

        mode_handler = {
            "access": _check_access_switchport,
            "trunk": _check_trunk_switchport,
        }.get(expd_mode)

        mode_results = mode_handler(dut, test_case, expd_status, msrd_port)
        results.extend(mode_results)

        if not any_failures(mode_results):
            results.append(
                tr.PassTestCase(
                    device=device, test_case=test_case, measurement=msrd_port
                )
            )

    return results


def _check_access_switchport(
    dut, test_case, expd_status: SwitchportAccessExpectation, msrd_status: dict
) -> tr.CollectionTestResults:
    """
    Only one check for now, that is to validate that the configured VLAN on the
    access port matches the test case.
    """
    device = dut.device
    vl_id = expd_status.vlan.vlan_id
    results = list()

    if vl_id and (msrd_vl_id := msrd_status["vlan"]) != vl_id:
        results.append(
            tr.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="vlan",
                expected=vl_id,
                measurement=msrd_vl_id,
            )
        )

    return results


def _check_trunk_switchport(
    dut, test_case, expd_status: SwitchportTrunkExpectation, msrd_status: dict
) -> tr.CollectionTestResults:

    device = dut.device
    results = list()

    # if there is a native vlan expected, then validate the match.

    if msrd_status.get("dropUntaggedTraffic", False) is True:
        # then not checking the native vlan.
        pass
    else:
        n_vl_id = expd_status.native_vlan.vlan_id if expd_status.native_vlan else None
        if n_vl_id and (msrd_vl_id := msrd_status["vlan"]) != n_vl_id:
            results.append(
                tr.FailFieldMismatchResult(
                    device=device,
                    test_case=test_case,
                    field="native_vlan",
                    expected=n_vl_id,
                    measurement=msrd_vl_id,
                )
            )

    msrd_allowd_vlans = msrd_status["allowedVlans"]
    if msrd_allowd_vlans == "all":
        return results

    # need to process the vlan list. Meraki provides this as a CSV we need to
    # create a CSV from the expected vlans. Then convert the list of vlan-ids to
    # a range string for string comparison purposes.

    expd_set = {vlan.vlan_id for vlan in expd_status.trunk_allowed_vlans}

    msrd_set = parse_istrange(msrd_allowd_vlans)

    if expd_set != msrd_set:
        results.append(
            tr.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="trunk_allowed_vlans",
                expected=sorted(expd_set),
                measurement=sorted(msrd_set),
            )
        )

    return results
