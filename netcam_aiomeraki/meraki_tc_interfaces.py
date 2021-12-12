# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Generator, AsyncGenerator, Dict
from itertools import chain

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from netcad.device import Device
from netcad.netcam import tc_result_types as tr
from netcad.phy_port import PhyPortSpeeds

from netcad.topology.tc_interfaces import (
    InterfaceTestCases,
    InterfaceTestCase,
)


# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .meraki_dut import MerakiDeviceUnderTest

from .tc_helpers import pass_fail_field


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["meraki_tc_interfaces"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def meraki_tc_interfaces(self, testcases: InterfaceTestCases) -> AsyncGenerator:
    dut: MerakiDeviceUnderTest = self
    device = dut.device

    map_port_status = await get_ports_status(dut)

    tcr_generators = list()

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()

        if dut.meraki_device["model"].startswith("MX"):
            yield tr.InfoTestCase(
                device=device,
                test_case=test_case,
                measurement="MX interface status not supported",
            )
            continue

        if not (msrd_status := map_port_status.get(if_name)):
            # TODO: Management is in the design file, but the device
            #       does not have it. This means we need to update the
            #       device-type spec in Netbox and re-sync.
            continue

        tcr_generators.append(
            meraki_check_one_interface(
                device=device, test_case=test_case, measurement=msrd_status
            )
        )

    # execute each of the coroutines yielding generated test case results.

    for result in chain.from_iterable(tcr_generators):
        yield result


# -----------------------------------------------------------------------------
#
#                             PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def meraki_to_speed(speed_str: str) -> int:
    if not speed_str:
        return 0

    if speed_str == "1 Gbps":
        return PhyPortSpeeds.speed_1G

    raise RuntimeError(f"Unknown Meraki speed converstion for: {speed_str}")


class SwitchInterfaceMeasurement(BaseModel):
    used: bool
    oper_up: bool
    speed: int

    @classmethod
    def from_api(cls, api_payload: dict):
        return cls(
            used=api_payload["enabled"] is True,
            oper_up=api_payload["status"] == "Connected",
            speed=meraki_to_speed(api_payload["speed"]),
        )


async def get_ports_status(dut: "MerakiDeviceUnderTest") -> Dict:
    model = dut.meraki_device["model"]

    if model.startswith("MS"):
        async with dut.meraki_api() as api:
            status_list = await api.switch.getDeviceSwitchPortsStatuses(
                serial=dut.meraki_device_sn
            )

        return {
            port_st["portId"]: SwitchInterfaceMeasurement.from_api(port_st)
            for port_st in status_list
        }

    elif model.startswith("MX"):
        net_id = dut.meraki_device["networkId"]

        async with dut.meraki_api() as api:
            status_list = await api.appliance.getNetworkAppliancePorts(
                networkId=net_id,
            )


def meraki_check_one_interface(
    device: Device,
    test_case: InterfaceTestCase,
    measurement: SwitchInterfaceMeasurement,
) -> Generator:

    if_flags = test_case.test_params.interface_flags or {}
    is_reserved = if_flags.get("is_reserved", False)
    should_oper_status = test_case.expected_results

    # -------------------------------------------------------------------------
    # If the interface is marked as reserved, then report the current state in
    # an INFO report and done with this test-case.
    # -------------------------------------------------------------------------

    if is_reserved:
        yield tr.InfoTestCase(
            device=device,
            test_case=test_case,
            field="is_reserved",
            measurement=measurement.dict(),
        )
        return

    # -------------------------------------------------------------------------
    # Check the 'used' status.  Then if the interface is not being used, then no
    # more checks are required.
    # -------------------------------------------------------------------------

    results = list()

    if should_oper_status.used != measurement.used:
        res = tr.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="used",
            measurement=measurement.used,
        )
        results.append(res)
        yield res

    if not should_oper_status.used:
        return

    res = pass_fail_field(
        device,
        test_case=test_case,
        field="oper_up",
        expd_value=should_oper_status.oper_up,
        msrd_value=measurement.oper_up,
    )

    yield res
    results.append(res)

    res = pass_fail_field(
        device,
        test_case=test_case,
        field="speed",
        expd_value=should_oper_status.oper_up,
        msrd_value=measurement.oper_up,
    )

    yield res
    results.append(res)

    if all(isinstance(res, tr.PassTestCase) for res in results):
        yield tr.PassTestCase(
            device=device, test_case=test_case, measurement=measurement.dict()
        )
