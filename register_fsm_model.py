import cocotb
from cocotb.types import LogicArray, Range
from typing import List, Set, Tuple
from enum import Enum
import math
import random

from .memory_model import MemoryModel


class CommandBytes(Enum):
    NULL = 0
    READ = 19
    WRITE = 35
    READ_DATA = 3
    BREAK = 85
    ESCAPE = 231


class RegisterFsmModel:
    def __init__(self, num_cmds: int):
        self.set_num_commands(num_cmds)
        self.generate_commands()
        self.generate_expected_read_datas()
        self.data_w = 32
        self.addr_w = 16
        self.byte_w = 8
        self.mem_model = MemoryModel(self.data_w, self.addr_w)
        commands = [CommandBytes.READ, CommandBytes.WRITE, CommandBytes.BREAK, CommandBytes.ESCAPE]
        self._command_values = [command.value for command in commands]

    def set_num_commands(self, num_cmds: int):
        assert num_cmds > 0, f"Number of commands must be greater than 0. Got {num_cmds}."
        self._num_cmds = num_cmds

    def __gemerate_random_address_lsbs(self) -> Tuple[List[int], bool]:
        choice_addrs_lsb: List[int] = list(self.mem_model.valid_addrs).append(42)
        choice_addrs_lsb.extend(self._command_values)
        addr_lsbs: List[int] = []
        addr_complete = False
        interrupt_cmd = False
        while not addr_complete:
            addr_lsb = random.choice(choice_addrs_lsb)
            if addr_lsb == 0:
                addr_lsbs.append(addr_lsb)
            elif addr_lsb in self.mem_model.valid_addrs or addr_lsb == 42:
                addr_lsbs.append(addr_lsb)
                addr_complete = True
            else:
                addr_lsbs.extend(self.__generate_command_bytes(addr_lsb))
                addr_complete = True
                interrupt_cmd = True

        return tuple([addr_lsbs, interrupt_cmd])

    def __generate_random_address_bytes(self) -> Tuple[List[int], bool]:
        choice_addrs_msb = [0, CommandBytes.ESCAPE.value]
        addr_msbs = [random.choice(choice_addrs_msb)]
        addr_lsbs: List[int] = []
        interrupt_cmd = False
        if addr_msbs[0] == 0:
            addr_lsbs, interrupt_cmd = self.__gemerate_random_address_lsbs()
        elif addr_msbs[0] == CommandBytes.ESCAPE.value:
            addr_msb = random.choice(self._command_values)
            addr_msbs.extend(self.__generate_command_bytes(addr_msb))
            interrupt_cmd = False
        return tuple([addr_msbs + addr_lsbs, interrupt_cmd])

    def __generate_random_data_bytes(self) -> List[int]:
        pass

    def __generate_command_bytes(self, command_value: int):
        command_bytes: List[int] = []
        if command_value == CommandBytes.READ.value:
            command_byte, _ = self.__generate_random_address_bytes()
            command_bytes.extend(command_byte)
        elif command_value == CommandBytes.WRITE.value:
            command_byte, interrupt_cmd = self.__generate_random_address_bytes()
            command_bytes.extend(command_byte)
            if not interrupt_cmd:
                command_bytes.extend(self.__generate_random_data_bytes)
        elif command_value == CommandBytes.BREAK.value:
            command_bytes.append(command_value)
        elif command_value == CommandBytes.ESCAPE.value:
            command_bytes.append(command_value)
        return command_bytes

    def generate_commands(self, num_cmds: int) -> List[List[int]]:
        self._cmds: List[List[int]] = []
        for idx in range(num_cmds):
            self._cmds.append[[CommandBytes.ESCAPE.value]]
            command_type = random.choice(self._command_values)
            self._cmds[idx].extend(self.__generate_command_bytes(command_type))

    def generate_expected_read_datas(self):
        pass
