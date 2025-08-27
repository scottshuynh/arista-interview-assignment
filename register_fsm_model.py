import cocotb
from cocotb.types import LogicArray, Range
from typing import List, Set, Tuple
from enum import Enum
import math
import random

from memory_model import MemoryModel


class CommandBytes(Enum):
    """Enum for command bytes as described in the Arista Interview Assignment."""

    NULL = 0
    READ = 19
    WRITE = 35
    READ_DATA = 3
    BREAK = 85
    ESCAPE = 231


class RegisterFsmModel:
    """Models the behaviour of the register FSM described in the Arista Interview Assignment.
    Also used to generate command bytestreams."""

    def __init__(self, num_cmds: int, data_w: int, addr_w: int):
        assert num_cmds > 0, (
            f"Number of commands must be greater than 0. Got {num_cmds}."
        )
        self.data_w = data_w
        self.addr_w = addr_w
        self.byte_w = 8
        self.mem_model = MemoryModel(self.data_w, self.addr_w)
        command_bytes = [
            CommandBytes.READ,
            CommandBytes.WRITE,
            CommandBytes.BREAK,
            CommandBytes.ESCAPE,
        ]
        self._command_values = [command.value for command in command_bytes]

        self.command_bytestreams: List[List[int]] = []
        self.read_bytestreams: List[List[int]] = []
        self.update_bytestreams(num_cmds)

    def __generate_random_address_bytes(self) -> Tuple[List[int], bool]:
        """For a write/read commands, generate random address bytes.

        The generation of address bytes is constrained. Address MSB
        is either a 0 or an ESCAPE byte. Zeros for MSB can be padded
        for any number of bytes.

        Address LSB is randomed from:
        * list of valid RAM addresses
        * an invalid address of 42
        * invalid addresses corresponding to WRITE, READ, BREAK bytes

        If the address MSB or LSB is an ESCAPE byte, the generation of the address
        LSB must be either a READ, WRITE, BREAK, ESCAPE byte.
        """
        num_bytes = math.ceil(self.addr_w / self.byte_w)
        addr_bytes: List[int] = [0, 0]
        is_escaped = False
        interrupt_cmd = False
        byte_idx = 0
        while byte_idx < num_bytes:
            if byte_idx == 0:
                if not is_escaped:
                    choice_addrs_msb = [0, CommandBytes.ESCAPE.value]
                    addr_byte = random.choice(choice_addrs_msb)
                    addr_bytes.append(addr_byte)
                    if addr_byte == CommandBytes.ESCAPE.value:
                        is_escaped = True
                    else:
                        byte_idx += 1
                if is_escaped:
                    addr_byte = random.choice(self._command_values)
                    is_escaped = False
                    addr_bytes.append(addr_byte)
                    byte_idx += 1
                    if addr_byte != CommandBytes.ESCAPE.value:
                        addr_bytes.extend(self.__generate_command_bytes(addr_byte))
                        byte_idx = num_bytes
                        interrupt_cmd = True
            else:
                if not is_escaped:
                    choice_addrs_lsb: List[int] = list(self.mem_model.valid_addrs)
                    choice_addrs_lsb.append(42)
                    choice_addrs_lsb.extend(self._command_values)
                    addr_byte = random.choice(choice_addrs_lsb)
                    addr_bytes.append(addr_byte)
                    if addr_byte == CommandBytes.ESCAPE.value:
                        is_escaped = True
                    else:
                        byte_idx += 1
                elif is_escaped:
                    addr_byte = random.choice(self._command_values)
                    is_escaped = False
                    addr_bytes.append(addr_byte)
                    byte_idx += 1
                    if addr_byte != CommandBytes.ESCAPE.value:
                        addr_bytes.extend(self.__generate_command_bytes(addr_byte))
                        byte_idx = num_bytes
                        interrupt_cmd = True

        return tuple([addr_bytes, interrupt_cmd])

    def __generate_random_data_bytes(self) -> List[int]:
        """For a write command, generate random data bytes.

        Data bytes can be any number from 0 to 2**BYTE_WIDTH-1.
        If a data byte generated is an ESCAPE byte, the subsequent byte must
        be either a READ, WRITE, BREAK, ESCAPE byte.
        """
        num_bytes = math.ceil(self.data_w / self.byte_w)
        data_bytes: List[int] = []
        is_escaped = False
        byte_idx = 0
        while byte_idx < num_bytes:
            if byte_idx == 0:
                if not is_escaped:
                    data_byte = random.randint(0, 2**self.byte_w - 1)
                    data_bytes.append(data_byte)
                    if data_byte == CommandBytes.ESCAPE.value:
                        is_escaped = True
                    else:
                        byte_idx += 1
                elif is_escaped:
                    data_byte = random.choice(self._command_values)
                    is_escaped = False
                    data_bytes.append(data_byte)
                    if data_byte == CommandBytes.ESCAPE.value:
                        byte_idx += 1
                    else:
                        data_bytes.extend(self.__generate_command_bytes(data_byte))
                        byte_idx = num_bytes
            else:
                if not is_escaped:
                    data_byte = random.randint(0, 2**self.byte_w - 1)
                    data_bytes.append(data_byte)
                    if data_byte == CommandBytes.ESCAPE.value:
                        is_escaped = True
                    else:
                        byte_idx += 1
                elif is_escaped:
                    data_byte = random.choice(self._command_values)
                    is_escaped = False
                    data_bytes.append(data_byte)
                    if data_byte == CommandBytes.ESCAPE.value:
                        byte_idx += 1
                    else:
                        data_bytes.extend(self.__generate_command_bytes(data_byte))
                        byte_idx = num_bytes

        return data_bytes

    def __generate_command_bytes(self, command_value: int) -> List[int]:
        """Generate command bytes for the corresponding command value.
        Requirements for how the bytes should be generated can be found in
        the Arista Interview Assignment document.

        Args:
            command_value (int): Command byte value.

        Returns:
            List[int]: List of generated bytes.
        """
        command_bytes: List[int] = []
        if command_value == CommandBytes.READ.value:
            command_byte, _ = self.__generate_random_address_bytes()
            command_bytes.extend(command_byte)
        elif command_value == CommandBytes.WRITE.value:
            command_byte, interrupt_cmd = self.__generate_random_address_bytes()
            command_bytes.extend(command_byte)
            if not interrupt_cmd:
                command_bytes.extend(self.__generate_random_data_bytes())
        elif command_value == CommandBytes.BREAK.value:
            return []
        elif command_value == CommandBytes.ESCAPE.value:
            return []
        return command_bytes

    def __update_command_bytestreams(self, num_cmds: int) -> None:
        """Update the command bytestreams by generating new commands.

        Args:
            num_cmds (int): Number of command bytestreams to generate.
        """
        command_bytestreams: List[List[int]] = []
        for idx in range(num_cmds):
            command_bytestreams.append([CommandBytes.ESCAPE.value])
            choices = list(self._command_values)
            choices.append(0)
            bytestream_complete = False
            while not bytestream_complete:
                command_type = random.choice(choices)
                if command_type == 0:
                    command_bytestreams[idx].append(command_type)
                else:
                    command_bytestreams[idx].append(command_type)
                    command_bytestreams[idx].extend(
                        self.__generate_command_bytes(command_type)
                    )
                    bytestream_complete = True

        self.command_bytestreams = command_bytestreams

    def __parse_write_bytestream(self, wr_bytestream: List[int]) -> List[int]:
        """Parse a write command bytestream to write to Memory Model (RAM). RAM
        data changes on a successful write.

        Args:
            wr_bytestream (List[int]): List of write command bytes,

        Returns:
            List[int]: Read response bytestream, if the write command was interrupted.
        """
        addr_bytes = []
        data_bytes = []
        num_addr_bytes = 4
        num_data_bytes = math.ceil(self.data_w / self.byte_w)
        is_escaped = False
        for idx, byte in enumerate(wr_bytestream):
            if len(addr_bytes) < num_addr_bytes:
                if len(addr_bytes) == 0:
                    if not is_escaped:
                        if byte == CommandBytes.ESCAPE.value:
                            is_escaped = True
                        else:
                            addr_bytes.append(byte)
                    elif is_escaped:
                        if byte == CommandBytes.BREAK.value:
                            return None
                        elif byte == CommandBytes.WRITE.value:
                            return self.__parse_write_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.READ.value:
                            return self.__parse_read_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.ESCAPE.value:
                            addr_bytes.append(byte)
                            is_escaped = False
                else:
                    if not is_escaped:
                        if byte == CommandBytes.ESCAPE.value:
                            is_escaped = True
                        else:
                            addr_bytes.append(byte)
                    elif is_escaped:
                        if byte == CommandBytes.BREAK.value:
                            return None
                        elif byte == CommandBytes.WRITE.value:
                            return self.__parse_write_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.READ.value:
                            return self.__parse_read_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.ESCAPE.value:
                            addr_bytes.append(byte)
                            is_escaped = False

            elif len(data_bytes) < num_data_bytes:
                if len(data_bytes) == 0:
                    if not is_escaped:
                        if byte == CommandBytes.ESCAPE.value:
                            is_escaped = True
                        else:
                            data_bytes.append(byte)
                    elif is_escaped:
                        if byte == CommandBytes.BREAK.value:
                            return None
                        elif byte == CommandBytes.WRITE.value:
                            return self.__parse_write_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.READ.value:
                            return self.__parse_read_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.ESCAPE.value:
                            data_bytes.append(byte)
                            is_escaped = False
                else:
                    if not is_escaped:
                        if byte == CommandBytes.ESCAPE.value:
                            is_escaped = True
                        else:
                            data_bytes.append(byte)
                    elif is_escaped:
                        if byte == CommandBytes.BREAK.value:
                            return None
                        elif byte == CommandBytes.WRITE.value:
                            return self.__parse_write_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.READ.value:
                            return self.__parse_read_bytestream(
                                wr_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.ESCAPE.value:
                            data_bytes.append(byte)
                            is_escaped = False

        # Convert into an unsigned integer address and data then write to RAM
        addr_bits = "".join(f"{byte:08b}" for byte in bytearray(addr_bytes))
        data_bits = "".join(f"{byte:08b}" for byte in bytearray(data_bytes))
        addr = LogicArray(addr_bits)[self.addr_w - 1 : 0].integer
        data = LogicArray(data_bits).integer
        self.mem_model.write(addr, data)
        return None

    def __parse_read_bytestream(self, rd_bytestream: List[int]) -> List[int]:
        """Parse a read command bytestream to read from RAM. Returns the read
        response bytestream if a successful read is completed.

        Args:
            rd_bytestream (List[int]): List of read command bytes.

        Returns:
            List[int]: Read response bytestream.
        """
        addr_bytes = []
        num_addr_bytes = 4
        num_data_bytes = math.ceil(self.data_w / self.byte_w)
        is_escaped = False
        for idx, byte in enumerate(rd_bytestream):
            if len(addr_bytes) < num_addr_bytes:
                if len(addr_bytes) == 0:
                    if not is_escaped:
                        if byte == CommandBytes.ESCAPE.value:
                            is_escaped = True
                        else:
                            addr_bytes.append(byte)
                    elif is_escaped:
                        if byte == CommandBytes.BREAK.value:
                            return None
                        elif byte == CommandBytes.WRITE.value:
                            return self.__parse_write_bytestream(
                                rd_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.READ.value:
                            return self.__parse_read_bytestream(
                                rd_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.ESCAPE.value:
                            addr_bytes.append(byte)
                            is_escaped = False
                else:
                    if not is_escaped:
                        if byte == CommandBytes.ESCAPE.value:
                            is_escaped = True
                        else:
                            addr_bytes.append(byte)
                    elif is_escaped:
                        if byte == CommandBytes.BREAK.value:
                            return None
                        elif byte == CommandBytes.WRITE.value:
                            return self.__parse_write_bytestream(
                                rd_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.READ.value:
                            return self.__parse_read_bytestream(
                                rd_bytestream[idx + 1 :]
                            )
                        elif byte == CommandBytes.ESCAPE.value:
                            addr_bytes.append(byte)
                            is_escaped = False

        # Convert into an unsigned integer address and data then read from RAM
        addr_bits = "".join(f"{byte:08b}" for byte in bytearray(addr_bytes))
        addr = LogicArray(addr_bits)[self.addr_w - 1 : 0].integer
        read_logicarray = self.mem_model.read(addr)
        read_bytes = []
        if read_logicarray:
            for idx in range(num_data_bytes):
                read_bytes.append(
                    read_logicarray[
                        (idx + 1) * self.byte_w - 1 : idx * self.byte_w
                    ].integer
                )
            read_bytes.reverse()
        else:
            read_bytes.append(CommandBytes.BREAK.value)
        return read_bytes

    def __parse_bytestream(self, bytestream: List[int]) -> List[int]:
        """Parse the bytestream for WRITE or READ commands.

        Args:
            bytestream (List[int]): List of bytes.

        Returns:
            List[int]: Read response bytestream.
        """
        for idx, byte in enumerate(bytestream):
            if idx == 0:
                assert byte == CommandBytes.ESCAPE.value
            else:
                if byte == CommandBytes.WRITE.value:
                    write_cmd = True
                    return self.__parse_write_bytestream(bytestream[idx + 1 :])
                elif byte == CommandBytes.READ.value:
                    return self.__parse_read_bytestream(bytestream[idx + 1 :])

        return None

    def __update_read_bytestreams(self) -> None:
        """Iterates over all command bytestreams and generates the corresponding
        read bytestream response."""
        read_bytestreams: List[List[int]] = []
        for command_bytestream in self.command_bytestreams:
            response = self.__parse_bytestream(command_bytestream)
            if response:
                read_bytestreams.append([CommandBytes.ESCAPE.value])
                if len(response) > 1:
                    read_bytestreams[-1].append(CommandBytes.READ_DATA.value)
                    for byte in response:
                        read_bytestreams[-1].append(byte)
                        if byte == CommandBytes.ESCAPE.value:
                            read_bytestreams[-1].append(byte)
                else:
                    read_bytestreams[-1].append(response[0])

        self.read_bytestreams = read_bytestreams

    def update_bytestreams(self, num_cmds: int) -> None:
        """Updates the command bytestream and the read bytestream.

        Command bytestream is used to drive the HDL DUT.

        Read bytestream is used in a scoreboard test to verify DUT behaviour.

        Args:
            num_cmds (int): Number of command bytestreams to generate.
        """
        self.__update_command_bytestreams(num_cmds)
        self.__update_read_bytestreams()
