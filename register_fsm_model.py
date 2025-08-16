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
    def __init__(self, num_cmds: int, data_w: int, addr_w: int):
        assert num_cmds > 0, f"Number of commands must be greater than 0. Got {num_cmds}."
        self.data_w = data_w
        self.addr_w = addr_w
        self.byte_w = 8
        self.mem_model = MemoryModel(self.data_w, self.addr_w)
        commands = [CommandBytes.READ, CommandBytes.WRITE, CommandBytes.BREAK, CommandBytes.ESCAPE]
        self._command_values = [command.value for command in commands]
        self.generate_commands(num_cmds)
        self.generate_expected_read_datas()

    def __generate_random_address_bytes(self) -> Tuple[List[int], bool]:
        num_bytes = math.ceil(self.addr_w / self.byte_w)
        addr_bytes: List[int] = []
        is_escaped = False
        interrupt_cmd = False
        byte_idx = 0
        while byte_idx < num_bytes:
            if byte_idx == 0:
                choice_addrs_msb = [0, CommandBytes.ESCAPE.value]
                addr_byte = random.choice(choice_addrs_msb)
                addr_bytes.append(addr_byte)
                byte_idx += 1
                if addr_byte == CommandBytes.ESCAPE.value:
                    is_escaped = True
            else:
                if not is_escaped:
                    choice_addrs_lsb: List[int] = list(self.mem_model.valid_addrs).append(42)
                    choice_addrs_lsb.extend(self._command_values)
                    addr_byte = random.choice(choice_addrs_lsb)
                    addr_bytes.append(addr_byte)
                    if addr_byte == CommandBytes.ESCAPE.value:
                        is_escaped = True
                    elif addr_byte > 0:
                        byte_idx += 1
                elif is_escaped:
                    addr_byte = random.choice(self._command_values)
                    is_escaped = False
                    addr_bytes.append(addr_byte)
                    if addr_byte == CommandBytes.ESCAPE.value:
                        byte_idx += 1
                    else:
                        addr_bytes.extend(self.__generate_command_bytes(addr_byte))
                        byte_idx = num_bytes
                        interrupt_cmd = True

        return tuple([addr_bytes, interrupt_cmd])

    def __generate_random_data_bytes(self) -> List[int]:
        num_bytes = math.ceil(self.data_w / self.byte_w)
        data_bytes: List[int] = []
        is_escaped = False
        byte_idx = 0
        while byte_idx < num_bytes:
            if not is_escaped:
                data_byte = random.randint(-(2 ** (self.byte_w - 1)), 2 ** (self.byte_w - 1) - 1)
                data_bytes.append(data_byte)
                if data_byte == CommandBytes.ESCAPE.value:
                    is_escaped = True
                elif data_byte != CommandBytes.NULL.value:
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
