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
from typing import Optional, Dict, List, Union, TypeVar
from os import environ
from functools import partial, cached_property, singledispatchmethod, reduce
from http import HTTPStatus

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.logger import get_logger
from netcad.netcam.dut import AsyncDeviceUnderTest
from netcad.netcam import CheckResultsCollection
from netcad.checks import CheckCollection

from meraki.aio import AsyncDashboardAPI, AsyncAPIError

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    RetryCallState,
    RetryError,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from .plugin_init import g_meraki

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["MerakiDeviceUnderTest", "CheckCollection", "CheckResultsCollection"]

AsyncAPIErrorLike = TypeVar("AsyncAPIErrorLike", AsyncAPIError, BaseException)

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class MerakiDeviceUnderTest(AsyncDeviceUnderTest):
    """
    Base-class for all specific Meraki DUT subclasses.  This base-class provides a
    nuber of commonly used features and API related access methods.

    Notes
    -----
    The User is currently required to export the enviornment variable(s):

        * MERAKI_ORGID:
            The Meraki Dashboard API orgId value for which this device should be
            located.

    Attributes
    ----------
    model: str
        The device model, as reported from the Merkai API

    serial: str
        The device serial-number, as reported from the Meraki API

    network_id: str
        The Meraki API networkId value for which this device is associated, as
        obtained via the Meraki API.

    meraki_orgid: str
        The Meraki API orgId for which this device is located, as assigned
        via the User environment.

    meraki_device: dict
        The device Meraki API payload about the device, as retrieved during
        the testing setup process.

    meraki_device_reachable: bool
        During the setup process the DUT validates device reachabilty as
        determined by using a "ping-check" API.  This value is set to True when
        the device responds that it is reachable, False otherwse.
    """

    def __init__(self, **kwargs):
        """
        Creates a new Meraki DUT instanced.  kwargs are not used and passed to
        super-class asis.
        """
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

        self.meraki_orgid: Optional[str] = environ.get("MERAKI_ORGID")

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
        """The device model as discovered during setup"""
        return self.meraki_device["model"]

    @cached_property
    def serial(self):
        """The device serial-number as discovered during setup"""
        return self.meraki_device["serial"]

    @cached_property
    def network_id(self):
        """The device Meraki API networkId as discovered during setup"""
        return self.meraki_device["networkId"]

    # -------------------------------------------------------------------------
    #
    #                         Meraki Dashboard Methods
    #
    # -------------------------------------------------------------------------

    @staticmethod
    def meraki_hostname_match(expected, measured: str) -> bool:
        """
        This function is a "helper" used duirng the cabling tests.  The Meraki
        products report their LLDP system name as  "Meraki ... - <hostname>".
        This function extracts the <hostname> portion for LLDP system-name
        comparison purposes.

        Returns
        -------
        True when the LLDP system-name matches, False otherwise.
        """
        if not measured.startswith("Meraki"):
            return False

        return expected == measured.split()[-1]

    async def api_cache_get(self, key: str, call: str, **kwargs):
        """
        This function is used to cache responses from the Meraki API so that
        when various testing executors that need the same data do not make
        duplicate calls to the API.  This method is meant to be used by
        high-abstraction methods that represent the data being obtained.  See
        the "get_lldp" method, for exmaple.

        Parameters
        ----------
        key: str
            The unique cache-key, as used the by calling function.

        call: str
            The Meraki API call in dotted-notation that follows from the Merak
            API instance.  For example, to call the get-lldp-cdp API, the call
            value would be "devices.getDeviceLldpCdp"

        Other Parameters
        ----------------
        kwargs: dict
            API specific call parameters.  For example, the get-lldp-cdp API
            requires the parameter "serial".  So the calling function would
            provide that key-value in kwargs.

        Returns
        -------
        The API payload as retrieved or previously cached.
        """

        # obtan the cache-lock to deal with mutual-exclusion in asyncio
        # processing.

        async with self._api_cache_lock:

            # if the value is not in the cache, then invoke the specific API
            # method to perform the command.  Once retrieved store the value
            # into the cache for subsequent use.

            if not (has_data := self._api_cache.get(key)):
                async with self.meraki_api() as api:
                    meth = reduce(getattr, call.split("."), api)
                    has_data = await meth(**kwargs)
                    self._api_cache[key] = has_data

            # return the API call results
            return has_data

    # -------------------------------------------------------------------------
    # Common Meraki Device API calls
    # -------------------------------------------------------------------------

    async def get_org_id(self):
        """
        This function is used to obtain the Meraki Organizational ID value.

        Returns
        -------
        str
            The org-Id value.
        """

        if g_meraki.org_id:
            self.meraki_orgid = g_meraki.org_id
            return

        if not g_meraki.org_name:
            raise RuntimeError("Meraki plugin mssing 'org_name' in configuration")

        orgs = await self.api_cache_get(
            key="orgs",
            call="organizations.getOrganizations",
        )

        if not (
            found_org := next(
                iter(org for org in orgs if org["name"] == g_meraki.org_name), None
            )
        ):
            raise RuntimeError(
                f"Meraki Dashboard does not provide organization: {g_meraki.org_name}"
            )

        self.meraki_orgid = found_org["id"]

    async def get_lldp_status(self) -> dict:
        """
        Execute the Meraki API to fetch the device LLDP/CDP information.  This
        content is cached once retrieved.

        Returns
        -------
        dict:
            The Meraki API specific payload for the get-device-lldp-cdp API.

        References
        ----------
        https://developer.cisco.com/meraki/api-v1/#!get-device-lldp-cdp
        """
        return await self.api_cache_get(
            key="lldp_status",
            call="devices.getDeviceLldpCdp",
            serial=self.serial,
        )

    async def get_mgmt_iface(self):
        """
        Execute the Merak API to fetch the device managment information.  This
        content is cached once retrieved.

        Returns
        -------
        dict:
            The Meraki API specific payload for the
            get-device-management-interface API.

        References
        ----------
        https://developer.cisco.com/meraki/api-v1/#!get-device-management-interface
        """
        return await self.api_cache_get(
            key="config_mgmt_iface",
            call="devices.getDeviceManagementInterface",
            serial=self.serial,
        )

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

    async def ping_check(self, timeout=5) -> dict:
        """
        This function executes the Meraki Dashboard "check device connectivity"
        test and returns the resulting API payload.  When the check passes then
        the DUT attribute `meraki_device_reachable` is set to True, otherwise it
        is set to False.

        Parameters
        ----------
        timeout:
            The number of secions to await the ping-check response before
            returning a failure result.

        Returns
        -------
        dict
            The API payload of the ping check response, or a "sential" dict
            value indicating a timeout.

        Notes
        -----
        2021-dec-15/JLS: From asyncio concurrent testing, it appears that the
        Meraki Dashboard can only support a maximum of 5 concurrent ping-check
        tasks.  Ffffff. So now we need to add a backoff/retry mechanism to
        handle this acase.
        """

        # initialize to timeout to handle case where the timeout condition
        # occurs and we want to indicate that to the Caller.

        ping_check = {"status": "timeout"}
        log = get_logger()

        def retry_on_429(retry_state: RetryCallState):
            """tenacity handler for checking the return status of 429"""

            oc = retry_state.outcome
            if not oc.failed:
                return False

            # if the exception is a 429, then we are going to backoff
            # and try again.

            rt_exc: AsyncAPIErrorLike = retry_state.outcome.exception()
            if not hasattr(rt_exc, "status"):
                return False

            if rt_exc.status == HTTPStatus.TOO_MANY_REQUESTS:
                log.info(
                    f"{self.device.name}: Still working on Meraki ping request ..."
                )
                return True

            # otherwise, we've tried hard enough and we should stop trying.
            # this will result in a RetryError in the calling context.
            return False

        @retry(
            retry=retry_on_429,
            wait=wait_exponential(multiplier=1, min=4, max=10),
            stop=stop_after_attempt(5),
        )
        async def _create_ping(_api):
            """Create a ping-check job"""
            return await api.devices.createDeviceLiveToolsPingDevice(serial=self.serial)

        @retry(
            retry=retry_on_429,
            wait=wait_exponential(multiplier=1, min=4, max=10),
            stop=stop_after_attempt(5),
        )
        async def _check_ping(_api, _job):
            """Check the status of a ping-check job"""
            return await api.devices.getDeviceLiveToolsPingDevice(
                serial=self.serial, id=_job["pingId"]
            )

        async with self.meraki_api() as api:
            try:
                ping_job = await _create_ping(api)

            except (AsyncAPIError, RetryError):
                log.error(
                    f"{self.device.name}: Timeout starting Meraki ping check ... proceeding regardless"
                )
                self.meraki_device_reachable = True
                return ping_check

            while timeout:
                await asyncio.sleep(1)

                try:
                    ping_check = await _check_ping(api, ping_job)
                except (AsyncAPIError, RetryError):
                    log.error(
                        f"{self.device.name}: Timeout checking Meraki ping ... proceeding regardless"
                    )
                    self.meraki_device_reachable = True
                    return ping_check

                if ping_check["status"] == "complete":
                    break

                timeout -= 1

        # set the DUT attribute to indicate if the device is reachable.

        self.meraki_device_reachable = (p_st := ping_check["status"]) in (
            "complete",
            "ready",
        )
        if not self.meraki_device_reachable:
            log.error(f"{self.device.name}: Ping check failed, status: {p_st}")

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

        await self.get_org_id()

        if not (dev := await self.get_inventory_device(name=self.device.name)):
            raise RuntimeError(
                f"{self.device.name}: not found in Meraki Dashboard, check name in system"
            )

        self.meraki_device = dev

        log.info(f"{self.device.name}: Running Meraki connectivity ping check ...")

        await self.ping_check()
        if not self.meraki_device_reachable:
            raise RuntimeError("Device fails reachability ping-check")

    @singledispatchmethod
    async def execute_checks(
        self, testcases: CheckCollection
    ) -> Optional["CheckResultsCollection"]:
        """
        This method is only called when the sub-classing DUT does not implement
        a specific set of testcases; for example a DUT does not implement the
        "transceivers" testcases because the Meraki API does not support it.

        This function always returns None to indicates to the netcam infrasture
        that the DUT does not support these testcases.  The netcam testing
        infrastructure will process the None as a SKIP.

        Parameters
        ----------
        testcases:
            The specific testcases for DUT execution.

        Returns
        -------
        None, always.
        """
        return None

    # -------------------------------------------------------------------------
    # Support the 'device' testcases
    # -------------------------------------------------------------------------

    from .meraki_check_device import meraki_check_device_info

    execute_checks.register(meraki_check_device_info)
