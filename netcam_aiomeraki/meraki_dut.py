# -----------------------------------------------------------------------------
# Systme Imports
# -----------------------------------------------------------------------------

from typing import AsyncGenerator, Optional, Dict
from os import environ
from functools import singledispatchmethod, partial

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam.dut import AsyncDeviceUnderTest
from netcad.testing_services import TestCases
from netcad.netcam import SkipTestCases

from meraki.aio import AsyncDashboardAPI


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["MerakiDeviceUnderTest"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class MerakiDeviceUnderTest(AsyncDeviceUnderTest):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.meraki_api = partial(AsyncDashboardAPI, suppress_logging=True)
        self.meraki_orgid = environ["MERAKI_ORGID"]
        self.meraki_device: Optional[Dict] = None
        self.meraki_device_sn: Optional[str] = None

    async def setup(self):
        async with self.meraki_api() as api:
            call = api.organizations.getOrganizationDevices
            resp = await call(organizationId=self.meraki_orgid, name=self.device.name)
            self.meraki_device = resp[0]
            self.meraki_device_sn = self.meraki_device["serial"]

    @singledispatchmethod
    async def execute_testcases(self, testcases: TestCases) -> AsyncGenerator:
        """dispatch the testcases to the registered methods"""
        cls_name = testcases.__class__.__name__
        # breakpoint()
        # x='raise'
        # raise NotImplementedError(
        #     f'Missing: device {self.device.name} support for testcases of type "{cls_name}"'
        # )

        cls_name = testcases.__class__.__name__
        yield SkipTestCases(
            device=self.device,
            message=f'Missing: device {self.device.name} support for testcases of type "{cls_name}"',
        )

    async def teardown(self):
        # no teardown process as each call to the Meraki API must be done as
        # part of a context manager.  dunno why that is, but that is how the
        # docs say the client must be used.  Tried other method and it does not
        # work in non-context-manager form.  TODO: investigate further.
        pass

    # -------------------------------------------------------------------------
    # Support the 'device' testcases
    # -------------------------------------------------------------------------

    from .meraki_tc_device import meraki_tc_device_info

    execute_testcases.register(meraki_tc_device_info)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .meraki_tc_interfaces import meraki_tc_interfaces

    execute_testcases.register(meraki_tc_interfaces)
