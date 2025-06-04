"""
OSPF Peer Validator Test Script
==============================
This script validates OSPF peers against expected values.
You can define expected peers per device and validate that they exist and are operational.
"""

import logging
from pyats import aetest
from genie.testbed import load
from genie.libs.abstraction import Lookup

EXPECTED_OSPF_PEERS = {
    # Format: 'device_name': [{'peer_id': 'id', 'expected_state': 'state'}]
    'router1': [
        {'peer_id': '10.0.0.1', 'expected_state': 'full'},
        {'peer_id': '10.0.0.2', 'expected_state': 'full/dr'}
    ],
    'router2': [
        {'peer_id': '10.0.0.2', 'expected_state': 'full/bdr'},
        {'peer_id': '10.0.0.3', 'expected_state': 'full/bdr'},
    ]
}

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def normalize_ospf_state(state: str) -> str:
    """Return a normalised OSPF neighbor state string."""
    if not state:
        return ""
    state = state.lower().strip()
    if '/' in state:
        left, right = state.split('/', 1)
        left = left.strip()
        right = right.strip()
        if right in {"", "-"}:
            return left
        return f"{left}/{right.strip('/')}"
    return state

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

class OSPFPeerValidator(aetest.Testcase):
    """Test case to validate OSPF peers"""
    @aetest.test
    def validate_OSPF_peer_existence(self, steps, testbed):
        """Validate that expected OSPF peers exist"""
        for device_name, device in testbed.devices.items():
            with steps.start(f'Checking OSPF peers on {device_name}'):
                # Skip devices with no expected OSPF config
                if device_name not in EXPECTED_OSPF_PEERS:
                    logger.info(f"No OSPF expectations defined for {device_name}, skipping")
                    continue
                
                # Get OSPF neighbors using Genie abstraction
                try:
                    lookup = Lookup.from_device(device)
                    ospf_neighbors = lookup.parser.show_ospf_neighbor(device=device)
                except Exception as e:
                    self.failed(
                        f"Failed to parse OSPF neighbors for {device_name}: {e}"
                    )
                    continue

                # Check each expected peer
                expected_peers = EXPECTED_OSPF_PEERS.get(device_name, [])
                
                for peer_data in expected_peers:
                    peer_id = peer_data.get('peer_id')
                    expected_state = peer_data.get('expected_state', 'full').lower()
                    
                    # Search for the peer in the OSPF neighbors output
                    peer_found = False
                    actual_state = 'unknown'
                    
                    # Navigate through the OSPF structure - this may vary by device OS
                    # For IOS/IOS-XE
                    if device.os == 'iosxe':
                        for int_name, int_data in ospf_neighbors.get('interfaces', {}).items():
                            for nei_id, nei_data in int_data.get('neighbors', {}).items():
                                if nei_id == peer_id:
                                    peer_found = True
                                    state = normalize_ospf_state(nei_data.get('state', ''))
                                    if state:
                                        actual_state = state
                                    else:
                                        break
                            if peer_found:
                                break

                    elif device.os == 'iosxr':
                        for vrf_name, vrf_data in ospf_neighbors.get('vrfs', {}).items():
                            for nei_id, nei_data in vrf_data.get('neighbors', {}).items():
                                if nei_id == peer_id:
                                    peer_found = True
                                    state = normalize_ospf_state(nei_data.get('state', ''))
                                    if state:
                                        actual_state = state
                                    else:
                                        break
                            if peer_found:
                                break
                    
                    # Validate the results
                    if not peer_found:
                        self.failed(f"{device_name}: Expected OSPF peer {peer_id} not found")
                    elif actual_state != expected_state:
                        self.failed(f"{device_name}: OSPF peer {peer_id} in state {actual_state}, expected {expected_state}")
                    else:
                        logger.info(f"{device_name}: OSPF peer {peer_id} found in expected state: {actual_state}")

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