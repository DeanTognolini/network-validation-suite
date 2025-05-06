"""
LDP Peer Validator Test Script
==============================
This script validates LDP peers against expected values.
You can define expected peers per device and validate that they exist and are operational.

Example of expected_ldp_peers.yaml file:
---------------------------------------
router1:
  - peer_id: '2.2.2.2'
    expected_state: 'operational'
  - peer_id: '3.3.3.3'
    expected_state: 'operational'
router2:
  - peer_id: '1.1.1.1'
    expected_state: 'operational'
  - peer_id: '3.3.3.3'
    expected_state: 'operational'
"""

import logging
import yaml
from pyats import aetest
from genie.testbed import load

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define expected LDP peer relationships
# This can be loaded from a separate YAML file for flexibility
EXPECTED_LDP_PEERS = {
    # Format: 'device_name': [{'peer_id': 'id', 'expected_state': 'state'}]
    'router1': [
        {'peer_id': '2.2.2.2', 'expected_state': 'operational'},
        {'peer_id': '3.3.3.3', 'expected_state': 'operational'}
    ],
    'router2': [
        {'peer_id': '1.1.1.1', 'expected_state': 'operational'},
        {'peer_id': '3.3.3.3', 'expected_state': 'operational'}
    ]
}

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all devices in the testbed"""
        testbed.connect(log_stdout=False)
    
    @aetest.subsection
    def prepare_testbed(self, testbed):
        """Prepare testbed and load configurations"""
        # Load expected LDP peers from file if available
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'expected_bgp_peers.yaml')
            with open(config_path, 'r') as f:
                expected_ldp = yaml.safe_load(f)
                if expected_ldp:
                    global EXPECTED_LDP_PEERS
                    EXPECTED_LDP_PEERS = expected_ldp
                    logger.info("Loaded expected LDP peer configuration from file")
        except FileNotFoundError:
            logger.info("No custom LDP peer file found, using default expectations")
        except Exception as e:
            logger.error(f"Error loading LDP peer file: {e}")
        
        # Log the expected LDP configuration
        logger.info(f"Expected LDP peers: {yaml.dump(EXPECTED_LDP_PEERS)}")
        
        # Check device connectivity
        for device_name, device in testbed.devices.items():
            if not device.connected:
                self.failed(f"Failed to connect to {device_name}")
            logger.info(f"Successfully connected to {device_name}")

class LDPPeerValidator(aetest.Testcase):
    """Test case to validate LDP peers"""
    
    @aetest.test
    def validate_ldp_peer_existence(self, testbed):
        """Validate that expected LDP peers exist"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected LDP config
            if device_name not in EXPECTED_LDP_PEERS:
                logger.info(f"No LDP expectations defined for {device_name}, skipping")
                continue
                
            logger.info(f"Validating LDP peers for {device_name}")
            
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
                expected_state = peer_data.get('expected_state', 'operational').lower()
                
                # Search for the peer in the LDP neighbors output
                peer_found = False
                actual_state = 'unknown'
                
                # Navigate through the LDP structure - this may vary by device OS
                # For IOS/IOS-XE
                for vrf_name, vrf_data in ldp_neighbors.get('vrf', {}).items():
                    for peer, peer_info in vrf_data.get('peers', {}).items():
                        # Peer can be an IP or ID depending on show command output
                        if peer == peer_id or peer_info.get('ldp_id', '') == peer_id:
                            peer_found = True
                            # Get state - some variations in output format
                            state = peer_info.get('state', '').lower()
                            if state:
                                actual_state = state
                            else:
                                # If state not directly found, check session state
                                session = peer_info.get('session', {})
                                if session.get('state', '').lower() == 'operational':
                                    actual_state = 'operational'
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
    
    @aetest.test
    def validate_ldp_bindings(self, testbed):
        """Validate that LDP is advertising/receiving bindings"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected LDP config
            if device_name not in EXPECTED_LDP_PEERS:
                continue
                
            logger.info(f"Validating LDP bindings for {device_name}")
            
            # Get LDP bindings
            try:
                ldp_bindings = device.parse('show mpls ldp bindings')
            except Exception as e:
                logger.warning(f"Could not parse LDP bindings for {device_name}: {e}")
                continue
                
            # Check if any bindings exist
            binding_count = 0
            
            # Navigate through the bindings output structure
            for vrf_name, vrf_data in ldp_bindings.get('vrf', {}).items():
                for prefix, prefix_data in vrf_data.get('lib', {}).items():
                    binding_count += len(prefix_data.get('bindings', {}))
            
            if binding_count == 0:
                self.failed(f"{device_name}: No LDP bindings found, device might not be exchanging labels")
            else:
                logger.info(f"{device_name}: Found {binding_count} LDP bindings - device is exchanging labels")
                
    @aetest.test
    def validate_ldp_interfaces(self, testbed):
        """Validate that LDP is enabled on expected interfaces"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected LDP config
            if device_name not in EXPECTED_LDP_PEERS:
                continue
                
            logger.info(f"Validating LDP interfaces for {device_name}")
            
            # Get LDP interfaces
            try:
                ldp_interfaces = device.parse('show mpls ldp interface')
            except Exception as e:
                logger.warning(f"Could not parse LDP interfaces for {device_name}: {e}")
                continue
                
            # Check if LDP is enabled on at least one interface
            interface_count = 0
            
            # Navigate through the interface output structure
            # Structure varies by OS version, try a few common ones
            
            # IOS/IOS-XE common structure
            for vrf_name, vrf_data in ldp_interfaces.get('vrf', {}).items():
                interface_count += len(vrf_data.get('interfaces', {}))
            
            # Alternative structure
            if interface_count == 0:
                interface_count = len(ldp_interfaces.get('interfaces', []))
            
            if interface_count == 0:
                self.failed(f"{device_name}: No LDP-enabled interfaces found")
            else:
                logger.info(f"{device_name}: Found {interface_count} LDP-enabled interfaces")

class CommonCleanup(aetest.CommonCleanup):
    """Common cleanup tasks"""
    
    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        """Disconnect from all devices"""
        for device_name, device in testbed.devices.items():
            if device.connected:
                device.disconnect()
                logger.info(f"Disconnected from {device_name}")

if __name__ == '__main__':
    # Import the testbed
    testbed = load('testbed.yaml')
    
    # Run the tests
    aetest.main(testbed=testbed)
