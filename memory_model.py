from cocotb.types import LogicArray, Range
from typing import List, Set


class MemoryModel:
    def __init__(self, data_w: int, addr_w: int):
        assert data_w > 0, f"Data width must be greater than 0. Got: {data_w}"
        assert addr_w > 0, f"Address width must be greater than 0. Got: {addr_w}"
        self.data_w: int = data_w
        self.addr_w: int = addr_w
        self.ram: List[LogicArray] = self.__generate_initial_ram(data_w)
        self.valid_addrs: Set[int] = {0, 1, 2, 3, 231}

    def write(self, addr: int, wr_data: int) -> None:
        assert addr >= 0 and addr < len(self.ram), f"Address out of range (0 to {len(self.ram)}). Got: {addr}"
        assert wr_data >= -(2 ** (self.data_w - 1)) and wr_data < 2 ** (
            self.data_w - 1
        ), f"Write data out of range ({-2**(self.data_w-1)} to {2**(self.data_w-1)-1}). Got: {wr_data}"
        if addr in self.valid_addrs:
            self.ram[addr] = LogicArray(wr_data, Range(self.data_w - 1, "downto", 0))

    def read(self, addr: int) -> int:
        assert addr >= 0 and addr < len(self.ram), f"Address out of range (0 to {len(self.ram)}). Got: {addr}"
        if addr in self.valid_addrs:
            return self.ram[addr]
        else:
            return None

    def __generate_initial_ram(self) -> List[LogicArray]:
        init_ram: List[int] = []
        for idx in range(2**self.addr_w):
            if idx == 0:
                init_ram.append(LogicArray(int("0x01234567", 16), Range(self.data_w - 1, "downto", 0)))
            elif idx == 1:
                init_ram.append(LogicArray(int("0x89abcde7", 16), Range(self.data_w - 1, "downto", 0)))
            elif idx == 2:
                init_ram.append(LogicArray(int("0x0a0b0c0d", 16), Range(self.data_w - 1, "downto", 0)))
            elif idx == 3:
                init_ram.append(LogicArray(int("0x10203040", 16), Range(self.data_w - 1, "downto", 0)))
            elif idx == 231:
                init_ram.append(LogicArray(int("0xdeadbeef", 16), Range(self.data_w - 1, "downto", 0)))
            else:
                init_ram.append(0)

        return init_ram
