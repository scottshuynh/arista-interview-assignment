import cocotb
from cocotb.clock import Clock
from cocotb.types import LogicArray, Range
from cocotb.triggers import RisingEdge, FallingEdge
import random
from typing import List


async def reset_dut(dut, num_clock_cycles: int):
    dut.reset.value = 1
    dut.data_in.value = 0
    dut.data_in_vld.value = 0

    for _ in range(num_clock_cycles):
        await RisingEdge(dut.clk)

    dut.reset.value = 0


async def drive_cmds(dut, cmds: List[List[int]]):
    for cmd in cmds:
        for byte in cmd:
            dut.data_in.value = byte
            dut.data_in_vld.value = 1
            await RisingEdge(dut.clk)

    dut.data_in_vld.value = 0


async def verify_sequences(dut, sequences: List[List[int]]):
    timeout = 0
    for seq_idx, sequence in enumerate(sequences):
        byte_count = 0
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

    cmds = [
        [
            int("0xe7", 16),
            int("0x13", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x03", 16),
        ],
        [
            int("0xe7", 16),
            int("0x13", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0xe7", 16),
            int("0xe7", 16),
        ],
        [
            int("0xe7", 16),
            int("0x23", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x02", 16),
            int("0xaa", 16),
            int("0xe7", 16),
            int("0xe7", 16),
            int("0x55", 16),
            int("0xaa", 16),
            int("0xe7", 16),
            int("0x13", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x02", 16),
        ],
        [
            int("0xe7", 16),
            int("0x23", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x01", 16),
            int("0xaa", 16),
            int("0xe7", 16),
            int("0x55", 16),
            int("0xe7", 16),
            int("0x13", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x00", 16),
            int("0x01", 16),
        ],
    ]

    sequences = [
        [
            int("0xe7", 16),
            int("0x03", 16),
            int("0x10", 16),
            int("0x20", 16),
            int("0x30", 16),
            int("0x40", 16),
        ],
        [
            int("0xe7", 16),
            int("0x03", 16),
            int("0xde", 16),
            int("0xad", 16),
            int("0xbe", 16),
            int("0xef", 16),
        ],
        [
            int("0xe7", 16),
            int("0x03", 16),
            int("0xaa", 16),
            int("0xe7", 16),
            int("0xe7", 16),
            int("0x55", 16),
            int("0xaa", 16),
        ],
        [
            int("0xe7", 16),
            int("0x03", 16),
            int("0x89", 16),
            int("0xab", 16),
            int("0xcd", 16),
            int("0xe7", 16),
            int("0xe7", 16),
        ],
    ]

    drive_task = cocotb.start_soon(drive_cmds(dut, cmds))
    verify_task = cocotb.start_soon(verify_sequences(dut, sequences))

    while not verify_task.done():
        await RisingEdge(dut.clk)
