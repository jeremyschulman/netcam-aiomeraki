# -----------------------------------------------------------------------------
# System Impors
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.topology.tc_device_info import DeviceInformationTestCases

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


async def meraki_tc_device_info(self, testcases: DeviceInformationTestCases):
    dut: MerakiDeviceUnderTest = self

    testcase = testcases.tests[0]
    exp_values = testcase.expected_results

    expd_product_model = exp_values.product_model
    msrd_product_model = dut.meraki_device["model"]

    yield pass_fail_field(
        dut.device,
        testcase,
        field="model",
        expd_value=expd_product_model,
        msrd_value=msrd_product_model,
    )
