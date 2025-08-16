import cocotb
from cocotb.clock import Clock
from cocotb.types import LogicArray, Range
from cocotb.triggers import RisingEdge, FallingEdge
import random
from typing import List, Sequence

from register_fsm_model import RegisterFsmModel


async def reset_dut(dut, num_clock_cycles: int):
    dut.reset.value = 1
    dut.data_in.value = 0
    dut.data_in_vld.value = 0

    for _ in range(num_clock_cycles):
        await RisingEdge(dut.clk)

    dut.reset.value = 0


async def drive_cmds(dut, cmds: List[Sequence[int]]):
    for cmd in cmds:
        for byte in cmd:
            dut.data_in.value = byte
            dut.data_in_vld.value = 1
            await RisingEdge(dut.clk)

        dut.data_in_vld.value = 0
        await FallingEdge(dut.clk)
        assert dut.u_fsm.reg_fsm.value == 0
        for _ in range(8):
            await RisingEdge(dut.clk)

    dut.data_in_vld.value = 0


async def drive_cmds_random_vlds(dut, cmds: List[Sequence[int]]):
    for cmd in cmds:
        byte_idx = 0
        while byte_idx < len(cmd):
            if random.randint(0, 1):
                dut.data_in.value = cmd[byte_idx]
                dut.data_in_vld.value = 1
                byte_idx += 1
            else:
                dut.data_in_vld.value = 0
            await RisingEdge(dut.clk)

    dut.data_in_vld.value = 0


async def verify_sequences(dut, sequences: List[Sequence[int]]):
    timeout = 0
    for seq_idx, sequence in enumerate(sequences):
        byte_count = 0
        # cocotb.log.info(f"Validating sequence#{seq_idx}: {sequence}")
        while byte_count < len(sequence):
            timeout += 1
            await FallingEdge(dut.clk)
            if dut.data_out_vld.value:
                assert (
                    sequence[byte_count] == dut.data_out.value.integer
                ), f"Expecting: {sequence[byte_count]}. Got: {dut.data_out.value.integer}"
                timeout = 0
                byte_count += 1

            assert timeout < 2048, f"Timeout while validating sequence #{seq_idx}."

    cocotb.log.info(f"Verified {len(sequences)} sequences.")


@cocotb.test()
async def test_simple_cases(dut):
    """Drives commands in and verifies against expected sequence."""
    cocotb.start_soon(Clock(dut.clk, 1, "ns").start())
    await reset_dut(dut, random.randint(1, 10))
    await RisingEdge(dut.clk)

    cmds: List[bytearray] = [
        bytearray([0xE7, 0x13, 0x00, 0x00, 0x00, 0x03]),
        bytearray([0xE7, 0x13, 0x00, 0x00, 0x00, 0xE7, 0xE7]),
        bytearray(
            [0xE7, 0x23, 0x00, 0x00, 0x00, 0x02, 0xAA, 0xE7, 0xE7, 0x55, 0xAA, 0xE7, 0x13, 0x00, 0x00, 0x00, 0x02]
        ),
        bytearray([0xE7, 0x23, 0x00, 0x00, 0x00, 0x01, 0xAA, 0xE7, 0x55, 0xE7, 0x13, 0x00, 0x00, 0x00, 0x01]),
    ]

    sequences: List[bytearray] = [
        bytearray([0xE7, 0x03, 0x10, 0x20, 0x30, 0x40]),
        bytearray([0xE7, 0x03, 0xDE, 0xAD, 0xBE, 0xEF]),
        bytearray([0xE7, 0x03, 0xAA, 0xE7, 0xE7, 0x55, 0xAA]),
        bytearray([0xE7, 0x03, 0x89, 0xAB, 0xCD, 0xE7, 0xE7]),
    ]

    drive_task = cocotb.start_soon(drive_cmds(dut, cmds))
    verify_task = cocotb.start_soon(verify_sequences(dut, sequences))

    while not verify_task.done():
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_simple_random_vlds(dut):
    """Drives commands in at random times and verifies against expected sequence."""
    cocotb.start_soon(Clock(dut.clk, 1, "ns").start())
    await reset_dut(dut, random.randint(1, 10))
    await RisingEdge(dut.clk)

    cmds: List[bytearray] = [
        bytearray([0xE7, 0x13, 0x00, 0x00, 0x00, 0x03]),
        bytearray([0xE7, 0x13, 0x00, 0x00, 0x00, 0xE7, 0xE7]),
        bytearray(
            [0xE7, 0x23, 0x00, 0x00, 0x00, 0x02, 0xAA, 0xE7, 0xE7, 0x55, 0xAA, 0xE7, 0x13, 0x00, 0x00, 0x00, 0x02]
        ),
        bytearray([0xE7, 0x23, 0x00, 0x00, 0x00, 0x01, 0xAA, 0xE7, 0x55, 0xE7, 0x13, 0x00, 0x00, 0x00, 0x01]),
    ]

    sequences: List[bytearray] = [
        bytearray([0xE7, 0x03, 0x10, 0x20, 0x30, 0x40]),
        bytearray([0xE7, 0x03, 0xDE, 0xAD, 0xBE, 0xEF]),
        bytearray([0xE7, 0x03, 0xAA, 0xE7, 0xE7, 0x55, 0xAA]),
        bytearray([0xE7, 0x03, 0x89, 0xAB, 0xCD, 0xE7, 0xE7]),
    ]

    drive_task = cocotb.start_soon(drive_cmds_random_vlds(dut, cmds))
    verify_task = cocotb.start_soon(verify_sequences(dut, sequences))

    while not verify_task.done():
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_scoreboard_vs_model(dut):
    cocotb.start_soon(Clock(dut.clk, 1, "ns").start())
    await reset_dut(dut, random.randint(1, 10))
    await RisingEdge(dut.clk)

    data_w = dut.u_fsm.DATA_W.value
    addr_w = dut.u_fsm.ADDR_W.value
    num_commands = 2 ** (addr_w + 1)

    cocotb.log.info("Initialising model...")
    model = RegisterFsmModel(num_commands, data_w, addr_w)

    drive_task = cocotb.start_soon(drive_cmds(dut, model.command_bytestreams))
    verify_task = cocotb.start_soon(verify_sequences(dut, model.read_bytestreams))

    cocotb.log.info("Start verification...")
    while not verify_task.done() or not drive_task.done():
        await RisingEdge(dut.clk)
