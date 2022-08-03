import pytest
from euci import EUci, UciExceptionNotFound 
from nextsec import firewall
from unittest.mock import MagicMock, patch

# Setup fake ip command output
ip_json='[{"ifindex":9,"ifname":"vnet3","flags":["BROADCAST","MULTICAST","UP","LOWER_UP"],"mtu":1500,"qdisc":"noqueue","master":"virbr2","operstate":"UNKNOWN","group":"default","txqlen":1000,"link_type":"ether","address":"fe:62:31:19:0b:29","broadcast":"ff:ff:ff:ff:ff:ff","addr_info":[{"family":"inet6","local":"fe80::fc62:31ff:fe19:b29","prefixlen":64,"scope":"link","valid_life_time":4294967295,"preferred_life_time":4294967295}]}]'
mock_ip_stdout = MagicMock()
mock_ip_stdout.configure_mock(**{"stdout": ip_json})

firewall_db = """
config zone lan1
	option name 'lan'
	list network 'lan'
	option input 'ACCEPT'
	option output 'ACCEPT'
	option forward 'ACCEPT'
	list device 'eth0'

config zone wan1
	option name 'wan'
	list network 'wan'
	list network 'wan6'
	option input 'REJECT'
	option output 'ACCEPT'
	option forward 'REJECT'
	option masq '1'
	option mtu_fix '1'

config forwarding fw1
	option src 'lan'
	option dest 'wan'
"""

network_db = """
config interface lan
	option device 'vnet3'
"""

def _setup_firewall_db(tmp_path):
     # setup fake firewall db
    with tmp_path.joinpath('firewall').open('w') as fp:
        fp.write(firewall_db)
    return EUci(confdir=tmp_path.as_posix())

@patch("nextsec.firewall.subprocess.run")
def test_get_device_name_valid(mock_run):
    # setup mock
    mock_run.return_value = mock_ip_stdout

    assert firewall.get_device_name("fe:62:31:19:0b:29") == 'vnet3'

def test_get_device_name_not_valid():
    assert firewall.get_device_name("aa:bb:cc:dd:66:55") == None

@patch("nextsec.firewall.subprocess.run")
def test_get_interface_name(mock_run2, tmp_path):
    # setup mock
    mock_run2.return_value = mock_ip_stdout
    # setup fake network db
    with tmp_path.joinpath('network').open('w') as fp:
        fp.write(network_db)
    u = EUci(confdir=tmp_path.as_posix())

    assert firewall.get_interface_name(u, "fe:62:31:19:0b:29") == 'lan'
    assert firewall.get_interface_name(u, "aa:bb:cc:dd:66:55") == None

def test_add_to_zone(tmp_path):
    u = _setup_firewall_db(tmp_path)
    assert firewall.add_to_zone(u, "vnet1", "lan") == 'lan1'
    assert 'vnet1' in u.get_all('firewall', 'lan1', 'device')
    assert firewall.add_to_zone(u, "vnet1", "blue") == None

def test_add_to_lan(tmp_path):
    u = _setup_firewall_db(tmp_path)
    assert firewall.add_to_lan(u, "vnet1") == 'lan1'
    assert 'vnet1' in u.get_all('firewall', 'lan1', 'device')

def test_add_to_wan(tmp_path):
    u = _setup_firewall_db(tmp_path)
    assert firewall.add_to_wan(u, "vnet2") == 'wan1'
    assert 'vnet2' in u.get_all('firewall', 'wan1', 'device')

def test_add_service(tmp_path):
    u = _setup_firewall_db(tmp_path)
    assert firewall.add_service(u, "my-service", "1234", "tcp") == "ns_allow_my_service"
    assert u.get('firewall', 'ns_allow_my_service', 'dest_port') == '1234'
    assert u.get('firewall', 'ns_allow_my_service', 'proto') == 'tcp'
    assert u.get('firewall', 'ns_allow_my_service', 'src') == 'wan'
    assert u.get('firewall', 'ns_allow_my_service', 'name') == 'Allow-my-service'

def test_block_service(tmp_path):
    u = _setup_firewall_db(tmp_path)
    firewall.add_service(u, "my-service", "1234", "tcp")
    assert firewall.remove_service(u, "my-service") == "ns_allow_my_service"
    with pytest.raises(UciExceptionNotFound):
        u.get('firewall', 'ns_allow_my_service')

def test_disable_service(tmp_path):
    u = _setup_firewall_db(tmp_path)
    firewall.add_service(u, "my-service", "1234", "tcp")
    assert firewall.disable_service(u, "my-service") == "ns_allow_my_service"
    assert u.get("firewall", "ns_allow_my_service", "enabled") == "0"
    assert firewall.disable_service(u, "non-existing") == None

def test_enable_service(tmp_path):
    u = _setup_firewall_db(tmp_path)
    firewall.add_service(u, "my-service", "1234", "tcp")
    firewall.disable_service(u, "my-service")
    assert firewall.enable_service(u, "my-service") == "ns_allow_my_service"
    assert u.get("firewall", "ns_allow_my_service", "enabled")
    assert firewall.enable_service(u, "non-existing") == None

def test_apply():
    # Already tested in pyuci
    assert 1
