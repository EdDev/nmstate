#
# Copyright (c) 2019 Red Hat, Inc.
#
# This file is part of nmstate
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
from contextlib import contextmanager

import libnmstate
from libnmstate.schema import Interface
from libnmstate.schema import InterfaceIPv4
from libnmstate.schema import InterfaceIPv6
from libnmstate.schema import InterfaceState
from libnmstate.schema import InterfaceType
from libnmstate.schema import LinuxBridge

import yaml


BRIDGE_OPTIONS_YAML = """
options:
  group-forward-mask: 0
  mac-ageing-time: 300
  multicast-snooping: true
  stp:
    enabled: true
    forward-delay: 15
    hello-time: 2
    max-age: 20
    priority: 32768
"""

BRIDGE_PORT_YAML = """
stp-hairpin-mode: false
stp-path-cost: 100
stp-priority: 32
"""


@contextmanager
def linux_bridge(name, bridge_subtree_state, extra_iface_state=None):
    desired_state = {
        Interface.KEY: [
            {
                Interface.NAME: name,
                Interface.TYPE: InterfaceType.LINUX_BRIDGE,
                Interface.STATE: InterfaceState.UP,
                Interface.IPV4: {InterfaceIPv4.ENABLED: False},
                Interface.IPV6: {InterfaceIPv6.ENABLED: False},
                LinuxBridge.CONFIG_SUBTREE: bridge_subtree_state or {},
            }
        ]
    }
    if extra_iface_state:
        desired_state[Interface.KEY][0].update(extra_iface_state)

    libnmstate.apply(desired_state)

    try:
        yield desired_state
    finally:
        libnmstate.apply(
            {
                Interface.KEY: [
                    {
                        Interface.NAME: name,
                        Interface.TYPE: InterfaceType.LINUX_BRIDGE,
                        Interface.STATE: InterfaceState.ABSENT,
                    }
                ]
            },
            verify_change=False,
        )


def add_port_to_bridge(bridge_subtree_state, port_name, port_state=None):
    if LinuxBridge.PORT_SUBTREE not in bridge_subtree_state:
        bridge_subtree_state[LinuxBridge.PORT_SUBTREE] = []

    if port_state is None:
        port_state = {}

    port_state[LinuxBridge.PORT_NAME] = port_name
    bridge_subtree_state[LinuxBridge.PORT_SUBTREE].append(port_state)

    return bridge_subtree_state


def create_bridge_subtree_state(options_state=None):
    if options_state is None:
        options_state = {
            LinuxBridge.STP_SUBTREE: {LinuxBridge.STP_ENABLED: False}
        }
    return {LinuxBridge.OPTIONS_SUBTREE: options_state}


def create_bridge_subtree_config(port_names):
    bridge_state = yaml.load(BRIDGE_OPTIONS_YAML, Loader=yaml.SafeLoader)

    for port in port_names:
        port_state = yaml.load(BRIDGE_PORT_YAML, Loader=yaml.SafeLoader)
        add_port_to_bridge(bridge_state, port, port_state)

    return bridge_state
