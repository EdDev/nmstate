#
# Copyright 2018 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from libnmstate.ethtool import minimal_ethtool
from libnmstate.nm import nmclient
from libnmstate.schema import Interface


ZEROED_MAC = '00:00:00:00:00:00'


class WiredSetting(object):
    def __init__(self, state):
        self.mtu = state.get(Interface.MTU)
        self.mac = state.get(Interface.MAC)

        ethernet = state.get('ethernet', {})
        self.speed = ethernet.get('speed')
        self.duplex = ethernet.get('duplex')
        self.auto_negotiation = ethernet.get('auto-negotiation')

    def __hash__(self):
        hash(self.__key())

    def __eq__(self, other):
        return self is other and self.__key() == other.__key()

    def __bool__(self):
        return bool(
            self.mac or
            self.mtu or
            self.speed or
            self.duplex or
            (self.auto_negotiation is not None)
        )

    # TODO: drop when py2 is no longer needed
    __nonzero__ = __bool__

    def __key(self):
        return (
            self.mtu,
            self.mac,
            self.speed,
            self.duplex,
            self.auto_negotiation
        )


def create_setting(iface_state, base_con_profile):
    setting = WiredSetting(iface_state)

    nm_wired_setting = None
    if base_con_profile:
        nm_wired_setting = base_con_profile.get_setting_wired()
        if nm_wired_setting:
            nm_wired_setting = nm_wired_setting.duplicate()

    if not setting:
        return nm_wired_setting

    if not nm_wired_setting:
        nm_wired_setting = nmclient.NM.SettingWired.new()

    if setting.mac:
        nm_wired_setting.props.cloned_mac_address = setting.mac

    if setting.mtu:
        nm_wired_setting.props.mtu = setting.mtu

    if setting.auto_negotiation:
        nm_wired_setting.props.auto_negotiate = True
        if not setting.speed and not setting.duplex:
            nm_wired_setting.props.speed = 0
            nm_wired_setting.props.duplex = None

        elif not setting.speed:
            ethtool_results = minimal_ethtool(str(iface_state['name']))
            setting.speed = ethtool_results['speed']
        elif not setting.duplex:
            ethtool_results = minimal_ethtool(str(iface_state['name']))
            setting.duplex = ethtool_results['duplex']

    elif setting.auto_negotiation is False:
        nm_wired_setting.props.auto_negotiate = False
        ethtool_results = minimal_ethtool(str(iface_state['name']))
        if not setting.speed:
            setting.speed = ethtool_results['speed']
        if not setting.duplex:
            setting.duplex = ethtool_results['duplex']

    if setting.speed:
        nm_wired_setting.props.speed = setting.speed

    if setting.duplex in ['half', 'full']:
        nm_wired_setting.props.duplex = setting.duplex

    return nm_wired_setting


def get_info(device):
    """
    Provides the current active values for a device
    """
    info = {}

    iface = device.get_iface()
    try:
        info['mtu'] = int(device.get_mtu())
    except AttributeError:
        pass

    mac = device.get_hw_address()
    # A device may not have a MAC or it may not yet be "realized" (zeroed mac).
    if mac and mac != ZEROED_MAC:
        info[Interface.MAC] = mac

    if device.get_device_type() == nmclient.NM.DeviceType.ETHERNET:
        ethernet = _get_ethernet_info(device, iface)
        if ethernet:
            info['ethernet'] = ethernet

    return info


def _get_ethernet_info(device, iface):
    ethernet = {}
    try:
        speed = int(device.get_speed())
        if speed > 0:
            ethernet['speed'] = speed
        else:
            return None
    except AttributeError:
        return None

    ethtool_results = minimal_ethtool(iface)
    auto_setting = ethtool_results['auto-negotiation']
    if auto_setting is True:
        ethernet['auto-negotiation'] = True
    elif auto_setting is False:
        ethernet['auto-negotiation'] = False
    else:
        return None

    duplex_setting = ethtool_results['duplex']
    if duplex_setting in ['half', 'full']:
        ethernet['duplex'] = duplex_setting
    else:
        return None
    return ethernet
