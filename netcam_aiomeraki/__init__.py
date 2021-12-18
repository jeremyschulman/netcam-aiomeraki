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

import importlib.metadata as importlib_metadata
from pathlib import Path

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from .appliance import MerakiApplianceDeviceUnderTest
from .switch import MerakiSwitchDeviceUnderTest
from .wireless import MerakiWirelessDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["__version__", "get_dut"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

__version__ = importlib_metadata.version(__name__)

dut_by_product = {
    "MX": MerakiApplianceDeviceUnderTest,
    "MS": MerakiSwitchDeviceUnderTest,
    "MR": MerakiWirelessDeviceUnderTest,
}


def get_dut(device: Device, testcases_dir: Path):

    if device.os_name != "meraki":
        raise RuntimeError(
            f"Missing required DUT class for device {device.name}, os_name: {device.os_name}"
        )

    if not (dut_cls := dut_by_product.get(device.product_model[0:2])):
        return None

    return dut_cls(device=device, testcases_dir=testcases_dir)
