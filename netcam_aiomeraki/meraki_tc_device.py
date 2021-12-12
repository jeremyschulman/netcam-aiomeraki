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

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.topology.tc_device_info import DeviceInformationTestCases
from netcad.netcam import tc_result_types as trt, any_failures

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_dut import MerakiDeviceUnderTest

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
) -> trt.CollectionTestResults:

    dut: MerakiDeviceUnderTest = self
    device = dut.device

    results = list()
    testcase = testcases.tests[0]
    exp_values = testcase.expected_results

    # check for matching product model.

    expd_product_model = exp_values.product_model
    msrd_product_model = dut.meraki_device["model"]

    if msrd_product_model != expd_product_model:
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=testcase,
                field="product_model",
                measurement=msrd_product_model,
            )
        )

    if not any_failures(results):
        results.append(
            trt.PassTestCase(
                device=device, test_case=testcase, measurement=exp_values.dict()
            )
        )

    return results
