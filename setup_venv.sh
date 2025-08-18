#!/usr/bin/env bash
if [ ! -f venv/bin/activate ]; then
    echo "No venv found. Making one now..."
    python -m venv venv
    source venv/bin/activate
    pip install git+https://github.com/pevhall/hdldepends.git@5b44ba5
    pip install git+https://github.com/scottshuynh/hdlworkflow.git
    pip install cocotb
else
    echo "venv found. Aborting..."
fi
