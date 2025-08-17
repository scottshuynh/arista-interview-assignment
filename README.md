# Arista Interview Assignment Submission
Included in this repo are:
* Source files implementing `register_fsm` and `memory_model`
* Simple VHDL testbench provided by Arista to test the design
* Cocotb testbench, including:
    * Tests provided in the VHDL testbench ported to python
    * Random constrained test
        * Generating random constrained command bytestreams
        * Utilising a python model to emulate the DUT
        * Scoreboard test to verify both model and DUT behave the same

## Requirements
* Linux OS ([Ubuntu](https://ubuntu.com/desktop))
* [Python](https://www.python.org/) 3.11 or greater
* [nvc](https://github.com/nickg/nvc) 1.17

### Optional
If the user requires a waveform viewer, install:
* [gtkwave](https://github.com/gtkwave/gtkwave) 3.3.116

## Set up python environment
Once everything is installed, run:
```sh
git clone https://github.com/scottshuynh/arista_interview_assignment.git
cd arista_interview_assignment
./setup_venv.sh
```

It is a requirement to run these steps before running any testbenches. Testbench scripts are run in the same terminal that `setup_venv.sh` was run.

`setup_venv.sh` creates a python virtual environment (venv), installs the python packages required to seamlessly run the testbenches, and activates the venv. If a venv was already set up, `setup_venv.sh` will simply activate it.

### Installed python packages
* [hdldepends](https://github.com/pevhall/hdldepends) - HDL dependency finder
* [hdlworkflow](https://github.com/scottshuynh/hdlworkflow) - Streamlines and simplifies HDL workflows
* [cocotb](https://github.com/cocotb/cocotb) - Enables users to write HDL testbenches in python

## Running testbenches
Before running any testbenches, make sure to follow the steps in the section: [Set up python environment](#set-up-python-environment).

All testbench scripts must be run from the root directory of the repo.

### Simple VHDL testbench
To run the simple VHDL testbench provided by Arista using nvc as the simulator:
```sh
./tb_simple_nvc.sh
```

To run the same testbench but view waveforms:
```sh
./tb_simple_nvc_gtkwave.sh
```

### Cocotb testbench
To run the random constrained test as well as the simple test using nvc as the simulator:
```sh
./tb_random_constrained_nvc.sh
```

To run the same testbench but view waveforms:
```sh
./tb_random_constrained_nvc_gtkwave.sh
```