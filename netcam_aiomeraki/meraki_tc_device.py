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
# System Impors
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, List

# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.topology.tc_device_info import DeviceInformationTestCases
from netcad.netcam import ResultsTestCase

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_dut import MerakiDeviceUnderTest

from .tc_helpers import pass_fail_field

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_tc_device_info"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_tc_device_info(
    self, testcases: DeviceInformationTestCases
) -> List[ResultsTestCase]:
    dut: MerakiDeviceUnderTest = self

    testcase = testcases.tests[0]
    exp_values = testcase.expected_results

    expd_product_model = exp_values.product_model
    msrd_product_model = dut.meraki_device["model"]

    return [
        pass_fail_field(
            dut.device,
            testcase,
            field="model",
            expd_value=expd_product_model,
            msrd_value=msrd_product_model,
        )
    ]
