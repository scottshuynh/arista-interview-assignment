#!/usr/bin/env bash
if [ ! -f compile_order.txt ]; then
    hdldepends hdldepends_config.toml --top-entity tb_vhdl_assignment_simple --compile-order-vhdl-lib work:compile_order.txt
fi
hdlworkflow nvc top compile_order.txt --cocotb tb_vhdl_assignment --wave gtkwave