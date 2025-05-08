"""
LDP Peer Validator Test Script
==============================
This script validates LDP peers against expected values.
You can define expected peers per device and validate that they exist and are operational.
"""

import logging
from pyats import aetest
from genie.testbed import load

EXPECTED_LDP_PEERS = {
    # Format: 'device_name': [{'peer_id': 'id', 'expected_state': 'state'}]
    'router1': [
        {'peer_id': '10.0.0.1', 'expected_state': 'oper'},
        {'peer_id': '10.0.0.2', 'expected_state': 'oper'}
    ],
    'router2': [
        {'peer_id': '10.0.0.2', 'expected_state': 'oper'},
        {'peer_id': '10.0.0.3', 'expected_state': 'oper'},
    ]
}

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class CommonSetup(aetest.CommonSetup):

    @aetest.subsection
    def check_topology(self, testbed, device_list=None):
        # if nobody passedin the list, default to all devices in the testbed
        if device_list is None:
            device_list = list(testbed.devices.keys())

        devices = []
        for name in device_list:
            if name not in testbed.devices:
                self.failed(f"Device {name} not found in testbed")
            else:
                devices.append(testbed.devices[name])

        # make the list of device-objects available to every testcase
        self.parent.parameters.update(devices=devices)

    @aetest.subsection
    def establish_connections(self, steps, devices):
        # Connect to each device before running tests
        for dev in devices:
            with steps.start(f"Connecting to {dev.name}"):
                dev.connect(log_stdout = False)

class LDPPeerValidator(aetest.Testcase):
    """Test case to validate LDP peers"""
    
    @aetest.test
    def validate_ldp_peer_existence(self, steps, testbed):
        """Validate that expected LDP peers exist"""
        for device_name, device in testbed.devices.items():
            with steps.start(f'Checking LDP peers on {device_name}'):
                # Skip devices with no expected LDP config
                if device_name not in EXPECTED_LDP_PEERS:
                    logger.info(f"No LDP expectations defined for {device_name}, skipping")
                    continue
                
                # Get LDP neighbors
                try:
                    ldp_neighbors = device.parse('show mpls ldp neighbor')
                except Exception as e:
                    self.failed(f"Failed to parse LDP neighbors for {device_name}: {e}")
                    continue
                    
                # Check if any LDP data was returned
                if not ldp_neighbors:
                    self.failed(f"No LDP neighbors found for {device_name}")
                    continue
                    
                # Check each expected peer
                expected_peers = EXPECTED_LDP_PEERS.get(device_name, [])
                
                for peer_data in expected_peers:
                    peer_id = peer_data.get('peer_id')
                    expected_state = peer_data.get('expected_state', 'oper').lower()
                    
                    # Search for the peer in the LDP neighbors output
                    peer_found = False
                    actual_state = 'unknown'
                    
                    # Navigate through the LDP structure - this may vary by device OS
                    # For IOS/IOS-XE
                    for vrf_name, vrf_data in ldp_neighbors.get('vrf', {}).items():
                        for peer_ip, peer_data in vrf_data.get('peers', {}).items():
                            for ls_id, ls_data in peer_data.get('label_space_id', {}).items():
                                if peer_ip == peer_id or peer_data.get('ldp_id', '') == peer_id:
                                    peer_found = True
                                    # Get state - some variations in output format
                                    state = ls_data.get('state', '').lower()
                                    if state:
                                        actual_state = state
                                    else:
                                        break
                        if peer_found:
                            break
                    
                    # If not found above, try alternative structure (some IOS-XR versions)
                    if not peer_found:
                        for interfaces in ldp_neighbors.get('interfaces', []):
                            for peer in interfaces.get('peers', []):
                                if peer.get('peer_ldp_id', '') == peer_id:
                                    peer_found = True
                                    state = peer.get('state', '').lower()
                                    if state:
                                        actual_state = state
                                    break
                            if peer_found:
                                break
                    
                    # Validate the results
                    if not peer_found:
                        self.failed(f"{device_name}: Expected LDP peer {peer_id} not found")
                    elif actual_state != expected_state:
                        self.failed(f"{device_name}: LDP peer {peer_id} in state {actual_state}, expected {expected_state}")
                    else:
                        logger.info(f"{device_name}: LDP peer {peer_id} found in expected state: {actual_state}")

class CommonCleanup(aetest.CommonCleanup):
    """Common cleanup tasks"""
    
    @aetest.subsection
    def disconnect_from_devices(self, steps, testbed):
        """Disconnect from all devices"""
        for device_name, device in testbed.devices.items():
            if device.connected:
                device.disconnect()
                logger.info(f"Disconnected from {device_name}")

if __name__ == '__main__':
    # Import the testbed
    testbed = load('testbed.yaml')
    
    # Run the tests
    aetest.main()