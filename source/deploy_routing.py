#! /usr/lib/python2.7
import argparse
from lxml import etree as et
from ncclient import manager

DEFAULT_AREA = '0.0.0.0'
DEFAULT_PROTOCOL = 'OSPF'
DEFAULT_RBRIDGE_ID = 1


def create_ospf_element(interface_num, ospf_area, rbridge_id):
    """

    :param interface_num: interface to enable OSPF on in the format <rb-id>/<slot-id>/<port-id>, e.g 1/0/1
    :param ospf_area:Id of the area in dotted decimal format,e.g: '0.0.0.0' for area 0
    :param rbridge_id: Rbridge ID of the switch on which routing protocol will be enabled
    :return: lxml.etree._Element
    """
    set_interface_area = et.Element('config')
    interface = et.SubElement(set_interface_area, 'interface', xmlns="urn:brocade.com:mgmt:brocade-interface")
    tengigabit = et.SubElement(interface, 'tengigabitethernet')
    name = et.SubElement(tengigabit, 'name')
    name.text = interface_num
    ip = et.SubElement(tengigabit, 'ip')
    interface_te = et.SubElement(ip, 'interface-te-ospf-conf', xmlns="urn:brocade.com:mgmt:brocade-ospf")
    interface_config = et.SubElement(interface_te, 'ospf-interface-config')
    area = et.SubElement(interface_config, 'area')
    area.text = ospf_area

    set_router_ospf = et.Element('config')
    rbridge_id_ele = et.SubElement(set_router_ospf, 'rbridge-id', xmlns="urn:brocade.com:mgmt:brocade-rbridge")
    rbridge_id_subele = et.SubElement(rbridge_id_ele, 'rbridge-id')
    rbridge_id_subele.text = str(rbridge_id)
    router_subele = et.SubElement(rbridge_id_ele, 'router')
    ospf = et.SubElement(router_subele, 'ospf', xmlns="urn:brocade.com:mgmt:brocade-ospf")
    vrf = et.SubElement(ospf, 'vrf')
    vrf.text = 'default-vrf'
    area1 = et.SubElement(ospf, 'area')
    area_id = et.SubElement(area1, 'area-id')
    area_id.text = ospf_area

    return set_interface_area, set_router_ospf


class NetconfDevice(object):
    def __init__(self, **kwargs):
        """
        Args:

        ip_addr(string): IP address of the switch/router to connect over ssh
        username(string): username to connect to switch
        password(string): password for above username
        port(int): TCP port number at which switch/router is listening for Netconf connections, default: 830
        hostkey(bool): True to verify hostkey, False to bypass
        allow_agent(bool): enables querying SSH agent (if found) for keys
        keys(bool): enables looking under locations for ssh keys (e.g. ~/.ssh/id_*)

        """

        if not kwargs.get('ip_addr'):
            raise Exception("Please enter IP address to connect to remote device")
        else:
            self._ip_addr = kwargs.get('ip_addr', None)
        self._username = kwargs.get('username', 'admin')
        self._password = kwargs.get('password', 'password')
        self._port = kwargs.get('port', 830)
        self._hostkey = kwargs.get('hostkey_verify', False)
        self._allow_agent = kwargs.get('allow_agent', False)
        self._keys = kwargs.get('look_for_keys', False)
        self._router = self.__connect_to_router

    @property
    def __connect_to_router(self):
        """
        Connects to router using netconf. Method takes in an IP address, username,password and other optional parameters
        to connect. If successful returns an object of class ncclient.manager

        """

        try:
            router_connect = manager.connect(host=self._ip_addr, username=self._username, password=self._password,
                                             port=self._port, hostkey_verify=self._hostkey,
                                             allow_agent=self._allow_agent,
                                             look_for_keys=self._keys)
            return router_connect
        except Exception as e:
            print "unable to establish Netconf session with {}, Exception: {} --> {}".format(self._ip_addr, type(e), e)

    def configure_router(self, interface, ospf_area=DEFAULT_AREA,
                         rbridge_id=DEFAULT_RBRIDGE_ID):
        area_element, router_ospf_element = create_ospf_element(interface, ospf_area, rbridge_id)
        try:
            configure_router_ospf = self._router.edit_config(target='running', config=router_ospf_element)
            print "OSPF configured Successfully on router {}".format(self._ip_addr)

            configure_ospf_area = self._router.edit_config(target='running', config=area_element)
            print "Interface {} is configured successfully with area {}".format(interface, ospf_area)

            return [configure_router_ospf, configure_ospf_area]
        except Exception as e:
            print("Netconf Edit Operation caused error"), type(e), e

    def close(self):
        try:
            self._router.close_session()
            print "The session with router {} closed successfully".format(self._ip_addr)
            return
        except Exception as e:
            print "close on object of class {} failed,Error: {} --> {}".format(NetconfDevice.__name__, type(e), e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("ip_addr", help="IP address to connect to switch")
    parser.add_argument("interface", help="interface to enable OSPF on")
    parser.add_argument("-username", help="Username to log into switch", default='admin')
    parser.add_argument("-password", help="User login Password", default='password')
    parser.add_argument("-area", help="Id of the area in dotted decimal format,e.g: '0.0.0.0' for area 0",
                        default=DEFAULT_AREA)
    parser.add_argument("-rbridge_id", help="Rbridge ID of the switch on which routing protocol will be enabled",
                        default=DEFAULT_RBRIDGE_ID)
    args = parser.parse_args()

    router = NetconfDevice(ip_addr=args.ip_addr, username=args.username, password=args.password)
    result = router.configure_router(args.interface, ospf_area=args.area, rbridge_id=args.rbridge_id)
    router.close()
