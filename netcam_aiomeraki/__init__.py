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
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional
import importlib.metadata as importlib_metadata

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.netcam.dut import AsyncDeviceUnderTest

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from .meraki_dut import MerakiDeviceUnderTest
from .appliance import MerakiApplianceDeviceUnderTest
from .switch import MerakiSwitchDeviceUnderTest
from .wireless import MerakiWirelessDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["plugin_init", "plugin_version", "plugin_get_dut", "plugin_description"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

plugin_version = importlib_metadata.version(__name__)
plugin_description = "NetCadCam plugin for Meraki Dashboard API (asyncio)"


dut_by_product = {
    "MX": MerakiApplianceDeviceUnderTest,
    "MS": MerakiSwitchDeviceUnderTest,
    "MR": MerakiWirelessDeviceUnderTest,
}


def plugin_get_dut(device: Device) -> Optional[AsyncDeviceUnderTest]:
    """
    This is the netcam plugin required "hook" function.  This function is
    required to examine the device instance and return back a Device Under Test
    (DUT) instance; or None if the device is not supported by this plugin.

    Parameters
    ----------
    device:
        The device instance for which a DUT is required.

    Returns
    -------
    None when the device product_model is not supported by this plugin
    DUT instance otherwise.
    """
    if device.os_name != "meraki":
        raise RuntimeError(
            f"Missing required DUT class for device {device.name}, os_name: {device.os_name}"
        )

    if not (dut_cls := dut_by_product.get(device.product_model[0:2])):
        return None

    return dut_cls(device=device)


def plugin_init(config: dict):
    """Required netcadcam plugin init hook function"""
    pass
