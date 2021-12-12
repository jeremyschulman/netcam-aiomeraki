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
# Systme Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict
from os import environ
from functools import partial, cached_property

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

        # the device object assigned in the `setup` method
        self.meraki_device: Optional[Dict] = None

    # -------------------------------------------------------------------------
    #
    #                            PROPERTIES
    #
    # -------------------------------------------------------------------------

    @cached_property
    def model(self):
        return self.meraki_device["model"]

    @cached_property
    def serial(self):
        return self.meraki_device["serial"]

    @cached_property
    def network_id(self):
        return self.meraki_device["networkId"]

    # -------------------------------------------------------------------------
    #
    #                              DUT METHODS
    #
    # -------------------------------------------------------------------------

    async def setup(self):
        """
        The setup process retrieves the Meraki dashboard device object and
        assignes DUT properties.
        """
        async with self.meraki_api() as api:
            call = api.organizations.getOrganizationDevices
            resp = await call(organizationId=self.meraki_orgid, name=self.device.name)
            self.meraki_device = resp[0]

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
