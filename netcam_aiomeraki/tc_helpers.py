# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.testing_services import TestCase
from netcad.netcam import PassTestCase, FailFieldMismatchResult


def pass_fail_field(device: Device, test_case: TestCase, expd_value, msrd_value, field):
    if expd_value == msrd_value:
        return PassTestCase(
            device=device, test_case=test_case, field=field, measurement=msrd_value
        )

    return FailFieldMismatchResult(
        device=device, test_case=test_case, field=field, measurement=msrd_value
    )
