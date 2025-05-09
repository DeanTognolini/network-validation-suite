"""
BGP Peer Validator Test Script
==============================
This script validates BGP peers against expected values.
You can define expected peers per device and validate that they exist and are operational.
"""

import logging
from pyats import aetest
from genie.testbed import load

EXPECTED_BGP_PEERS = {
    # Format: 'device_name': [{'peer_id': 'id', 'expected_state': 'state'}]
    'router1': [
        {'peer_id': '10.0.0.1', 'expected_state': 'Established'},
        {'peer_id': '10.0.0.2', 'expected_state': 'Established'}
    ],
    'router2': [
        {'peer_id': '10.0.0.1', 'expected_state': 'Established'},
        {'peer_id': '10.0.0.2', 'expected_state': 'Established'}
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

class BGPPeerValidator(aetest.Testcase):
    """Test case to validate BGP peers"""
    
    @aetest.test
    def validate_bgp_peer_existence(self, steps, testbed):
        """Validate that expected BGP peers exist"""
        for device_name, device in testbed.devices.items():
            with steps.start(f'Checking BGP peers on {device_name}'):
                # Skip devices with no expected BGP config
                if device_name not in EXPECTED_BGP_PEERS:
                    logger.info(f"No BGP expectations defined for {device_name}, skipping")
                    continue
                
                # Parse device output
                # For IOS/IOS-XE
                if device.os == 'iosxe':
                    try:
                        bgp = device.parse('show bgp all neighbors')
                    except Exception as e:
                        self.failed(f"Failed to parse OSPF neighbors for {device_name}: {e}")
                        continue
                # For IOS-XR
                elif device.os == 'iosxr':
                    try:
                        bgp = device.parse('show bgp instance all sessions')
                    except Exception as e:
                        self.failed(f"Failed to parse OSPF neighbors for {device_name}: {e}")
                        continue
                    
                else:
                    self.failed(f"Device OS not found in testbed.yaml")
                    
                # Check each expected peer
                expected_peers = EXPECTED_BGP_PEERS.get(device_name, [])
                # Extract peer id and expected state for each expected peer
                for peer_data in expected_peers:
                    peer_id = peer_data.get('peer_id')
                    expected_state = peer_data.get('expected_state', {}).lower()
                    
                    peer_found = False
                    actual_state = 'unknown'
                    
                    # For IOS/IOS-XE
                    if device.os == 'iosxe':
                        for vrf_name, vrf_data in bgp.get('vrf', {}).items():
                            for nei_id, nei_data in vrf_data.get('neighbor', {}).items():
                                if nei_id == peer_id:
                                    peer_found = True
                                    """
                                    Get state & normalise - some variations in output format between OS
                                    """
                                    state = nei_data.get('session_state', '').lower()
                                    if state:
                                        actual_state = state
                                    else:
                                        break
                                if peer_found:
                                    break

                    elif device.os == 'iosxr':
                        for ins_name, ins_data in bgp.get('instance', {}).items():
                            for vrf_name, vrf_data in ins_data.get('vrf', {}).items():
                                for nei_id, nei_data in vrf_data.get('neighbors', {}).items():
                                    if nei_id == peer_id:
                                        peer_found = True
                                        """
                                        Get state & normalise - some variations in output format between OS
                                        """
                                        state = nei_data.get('nbr_state', '').lower()
                                        if state:
                                            actual_state = state
                                        else:
                                            break
                                if peer_found:
                                    break

                    # Validate the results
                    if not peer_found:
                        self.failed(f"{device_name}: Expected BGP peer {peer_id} not found")
                    elif actual_state != expected_state:
                        self.failed(f"{device_name}: BGP peer {peer_id} in state {actual_state}, expected {expected_state}")
                    else:
                        logger.info(f"{device_name}: BGP peer {peer_id} found in expected state: {actual_state}")

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