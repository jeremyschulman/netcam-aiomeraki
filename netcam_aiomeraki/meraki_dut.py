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

import asyncio
from typing import Optional, Dict, List, Union
from os import environ
from functools import partial, cached_property, singledispatchmethod, reduce

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.logger import get_logger
from netcad.netcam.dut import AsyncDeviceUnderTest
from netcad.netcam import CollectionTestResults
from netcad.testing_services import TestCases
from meraki.aio import AsyncDashboardAPI

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["MerakiDeviceUnderTest", "TestCases", "CollectionTestResults"]


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
        self.meraki_device_reachable = False

        # create a cache for API data, access and usage should only be done with
        # api_cache_get method.

        self._api_cache_lock = asyncio.Lock()
        self._api_cache = dict()

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
    #                         Meraki Dashboard Methods
    #
    # -------------------------------------------------------------------------

    async def api_cache_get(self, key: str, call: str, **kwargs):
        async with self._api_cache_lock:
            if not (has_data := self._api_cache.get(key)):
                async with self.meraki_api() as api:
                    meth = reduce(getattr, call.split("."), api)
                    has_data = await meth(**kwargs)
                    self._api_cache[key] = has_data

            return has_data

    async def get_inventory_device(
        self, single=True, **kwargs
    ) -> Optional[Union[List[Dict], Dict]]:
        """
        Obtain a device from the Meraki dashboard inventory.  The Caller can
        provide any supported query parameters as defined by the Meraki API,
        here:
        https://developer.cisco.com/meraki/api-v1/#!get-organization-devices

        Parameters
        ----------
        single: bool
            When True (default), expect and return only one device record. This
            is the common use-case to get one device.  That said, a Caller can
            set this single=False, and this function will return a list of
            dictionary objects that match the kwargs query params.

        Other Parameters
        ----------
        kwargs:
            As described.  For example "mac=<value>" would be used to located a
            device by mac-address.  "name=<value>" would be used to locate a
            device by hostname.

        Returns
        -------
        None:
            When the query returns no devices

        dict:
            When single=True, the device object payload from the API.

        list[dict]:
            When single=False, the list of device objects
        """
        async with self.meraki_api() as api:

            api_data = await api.organizations.getOrganizationDevices(
                organizationId=self.meraki_orgid, **kwargs
            )

            if not single:
                return api_data

            if not len(api_data):
                return None

            return api_data[0]

    async def ping_check(self, timeout=5):
        ping_check = {"status": "none"}

        async with self.meraki_api() as api:
            ping_device = await api.devices.createDeviceLiveToolsPingDevice(
                serial=self.serial
            )

            while timeout:
                await asyncio.sleep(1)

                ping_check = await api.devices.getDeviceLiveToolsPingDevice(
                    serial=self.serial, id=ping_device["pingId"]
                )

                if ping_check["status"] == "complete":
                    break

                timeout -= 1

        # set the DUT attribute to indicate if the device is reachable.
        self.meraki_device_reachable = ping_check["status"] == "complete"
        return ping_check

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
        log = get_logger()

        if not (dev := await self.get_inventory_device(name=self.device.name)):
            raise RuntimeError(
                f"DUT: {self.device.name}: not found in Meraki Dashboard, check name in system"
            )

        self.meraki_device = dev

        log.info(f"DUT: {self.device.name}: Running connectivity ping check ...")

        await self.ping_check()
        if not self.meraki_device_reachable:
            raise RuntimeError("Device fails reachability ping-check")

    @singledispatchmethod
    async def execute_testcases(
        self, testcases: TestCases
    ) -> Optional["CollectionTestResults"]:
        return None

    # -------------------------------------------------------------------------
    # Support the 'device' testcases
    # -------------------------------------------------------------------------

    from .meraki_tc_device import meraki_tc_device_info

    execute_testcases.register(meraki_tc_device_info)
