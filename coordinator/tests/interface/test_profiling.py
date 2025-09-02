# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
from interface_tester import InterfaceTester


def test_profiling_v0_interface(profiling_tester: InterfaceTester):
    profiling_tester.configure(
        interface_name="profiling",
        endpoint="profiling",
        interface_version=0,
    )
    profiling_tester.run()
