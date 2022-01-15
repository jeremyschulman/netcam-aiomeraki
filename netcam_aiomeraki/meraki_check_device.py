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

from netcad.topology.checks.check_device_info import DeviceInformationCheckCollection
from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_dut import MerakiDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_check_device_info"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_check_device_info(
    self, testcases: DeviceInformationCheckCollection
) -> trt.CheckResultsCollection:
    """
    The testcase execute for the "device" testcase.  This function is used to
    validate the expected product model.

    Parameters
    ----------
    self: MerakiDeviceUnderTest
        The DUT instance

    testcases:
        The DeviceInformation set of testcases.

    Returns
    -------
    List of test-case results that are processed by the netcam infrastructure.
    """
    dut: MerakiDeviceUnderTest = self
    device = dut.device

    results = list()
    testcase = testcases.checks[0]
    exp_values = testcase.expected_results

    # check for matching product model.

    expd_product_model = exp_values.product_model
    msrd_product_model = dut.meraki_device["model"]

    if msrd_product_model != expd_product_model:
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=testcase,
                field="product_model",
                measurement=msrd_product_model,
            )
        )

    # add an information result to capture the state of the device data.

    results.append(
        trt.CheckInfoLog(
            device=device,
            check=testcase,
            field="device_info",
            measurement=self.meraki_device,
        )
    )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(
                device=device,
                check=testcase,
                field="product_model",
                measurement=msrd_product_model,
            )
        )

    return results
