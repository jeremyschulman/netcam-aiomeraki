# -----------------------------------------------------------------------------
# Systme Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict
from os import environ
from functools import partial

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam.dut import AsyncDeviceUnderTest
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

        # create a functional partial that is used to create a new instnace of
        # the Meraki dashboard API.  This is necessary beacuse the use of the
        # meraki-dashboard asyncio requires the use of an async-context
        # management; not sure why but that is how it is implemented. So each
        # usage by the test-case executors will instantiate a new dashboard
        # instance in a context-manager

        self.meraki_api = partial(AsyncDashboardAPI, suppress_logging=True)

        # The Meraki organizational ID value is currently extracted from an
        # environment variable.  Perhaps rethink this approach; but for now ...

        self.meraki_orgid = environ["MERAKI_ORGID"]

        # property values assigned in the `setup` method, these are used
        # throughout the testcase executors when making calls to the Meraki
        # Dashboard API.

        # the device object
        self.meraki_device: Optional[Dict] = None

        # the network ID associated to the device
        self.meraki_netid: Optional[str] = None

        # The device serial-number
        self.meraki_device_sn: Optional[str] = None

    async def setup(self):
        """
        The setup process retrieves the Meraki dashboard device object and
        assignes DUT properties.
        """
        async with self.meraki_api() as api:
            call = api.organizations.getOrganizationDevices
            resp = await call(organizationId=self.meraki_orgid, name=self.device.name)
            self.meraki_device = resp[0]
            self.meraki_device_sn = self.meraki_device["serial"]
            self.meraki_netid = self.meraki_device["networkId"]

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

    AsyncDeviceUnderTest.execute_testcases.register(meraki_tc_device_info)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .meraki_tc_interfaces import meraki_tc_interfaces

    AsyncDeviceUnderTest.execute_testcases.register(meraki_tc_interfaces)
