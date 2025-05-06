"""
BGP Peer Validator Test Script
==============================
This script validates BGP peers against expected values.
You can define expected peers per device and validate that they exist and are established.

Example of expected_bgp_peers.yaml file:
---------------------------------------
router1:
  10.1.1.2:
    peer_as: '65002'
    expected_state: 'established'
  10.1.1.3:
    peer_as: '65003'
    expected_state: 'established'
router2:
  10.1.1.1:
    peer_as: '65001'
    expected_state: 'established'
  10.2.2.3:
    peer_as: '65003'
    expected_state: 'established'
"""

import logging
import yaml
from pyats import aetest
from genie.testbed import load

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define expected BGP peer relationships
# This can be loaded from a separate YAML file for flexibility
EXPECTED_BGP_PEERS = {
    # Format: 'device_name': {'peer_ip': {'peer_as': 'expected_state'}}
    'router1': {
        '10.1.1.2': {'peer_as': '65002', 'expected_state': 'established'},
        '10.1.1.3': {'peer_as': '65003', 'expected_state': 'established'}
    },
    'router2': {
        '10.1.1.1': {'peer_as': '65001', 'expected_state': 'established'},
        '10.2.2.3': {'peer_as': '65003', 'expected_state': 'established'}
    }
}

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all devices in the testbed"""
        testbed.connect(log_stdout=False)
    
    @aetest.subsection
    def prepare_testbed(self, testbed):
        """Prepare testbed and load configurations"""
        # Load expected BGP peers from file if available
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'expected_bgp_peers.yaml')
            with open(config_path, 'r') as f:
                expected_bgp = yaml.safe_load(f)
                if expected_bgp:
                    global EXPECTED_BGP_PEERS
                    EXPECTED_BGP_PEERS = expected_bgp
                    logger.info("Loaded expected BGP peer configuration from file")
        except FileNotFoundError:
            logger.info("No custom BGP peer file found, using default expectations")
        except Exception as e:
            logger.error(f"Error loading BGP peer file: {e}")
        
        # Log the expected BGP configuration
        logger.info(f"Expected BGP peers: {yaml.dump(EXPECTED_BGP_PEERS)}")
        
        # Check device connectivity
        for device_name, device in testbed.devices.items():
            if not device.connected:
                self.failed(f"Failed to connect to {device_name}")
            logger.info(f"Successfully connected to {device_name}")
            
class BGPPeerValidator(aetest.Testcase):
    """Test case to validate BGP peers"""
    
    @aetest.test
    def validate_bgp_peer_existence(self, testbed):
        """Validate that expected BGP peers exist"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected BGP config
            if device_name not in EXPECTED_BGP_PEERS:
                logger.info(f"No BGP expectations defined for {device_name}, skipping")
                continue
                
            logger.info(f"Validating BGP peers for {device_name}")
            
            # Get BGP neighbors
            try:
                bgp_neighbors = device.parse('show ip bgp neighbors')
            except Exception as e:
                self.failed(f"Failed to parse BGP neighbors for {device_name}: {e}")
                continue
                
            # Check if any BGP data was returned
            if not bgp_neighbors:
                self.failed(f"No BGP neighbors found for {device_name}")
                continue
                
            # Check each expected peer
            expected_peers = EXPECTED_BGP_PEERS.get(device_name, {})
            
            for peer_ip, peer_data in expected_peers.items():
                expected_as = peer_data.get('peer_as')
                
                # Check if peer exists
                if peer_ip not in bgp_neighbors:
                    self.failed(f"{device_name}: Expected BGP peer {peer_ip} (AS {expected_as}) not found")
                    continue
                    
                # Verify AS number if provided
                if expected_as:
                    actual_as = str(bgp_neighbors[peer_ip].get('remote_as', ''))
                    if actual_as != expected_as:
                        self.failed(f"{device_name}: BGP peer {peer_ip} has wrong AS number: {actual_as} "
                                   f"(expected {expected_as})")
                
                logger.info(f"{device_name}: Found expected BGP peer {peer_ip}")
    
    @aetest.test
    def validate_bgp_peer_states(self, testbed):
        """Validate that BGP peers are in expected states"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected BGP config
            if device_name not in EXPECTED_BGP_PEERS:
                continue
                
            logger.info(f"Validating BGP peer states for {device_name}")
            
            # Get BGP summary to check states
            try:
                bgp_summary = device.parse('show ip bgp summary')
            except Exception as e:
                self.failed(f"Failed to parse BGP summary for {device_name}: {e}")
                continue
                
            # Get BGP neighbors for detailed info
            try:
                bgp_neighbors = device.parse('show ip bgp neighbors')
            except Exception as e:
                logger.warning(f"Could not parse detailed BGP neighbors for {device_name}: {e}")
                bgp_neighbors = {}
                
            # Check each expected peer
            expected_peers = EXPECTED_BGP_PEERS.get(device_name, {})
            
            for peer_ip, peer_data in expected_peers.items():
                expected_state = peer_data.get('expected_state', 'established').lower()
                
                # Navigate through the summary structure to find neighbor state
                # Structure can vary depending on IOS version and BGP configuration
                peer_found = False
                actual_state = "unknown"
                
                # First check in summary - typical IOS structure
                for vrf_name, vrf_data in bgp_summary.get('vrf', {}).items():
                    for as_num, as_data in vrf_data.get('neighbor', {}).items():
                        if as_num == peer_ip:
                            peer_found = True
                            # Check if the neighbor is established (will show a number for prefixes if so)
                            state_pfxrcd = as_data.get('state_pfxrcd', '')
                            
                            # In 'show ip bgp summary', established sessions show a number of prefixes received
                            # while non-established sessions show the state as a string
                            if state_pfxrcd.isdigit() or state_pfxrcd == '':
                                actual_state = 'established'
                            else:
                                actual_state = state_pfxrcd.lower()
                            break
                    if peer_found:
                        break
                
                # If not found in summary, check detailed output
                if not peer_found and peer_ip in bgp_neighbors:
                    peer_found = True
                    session_state = bgp_neighbors[peer_ip].get('session_state', '').lower()
                    if 'established' in session_state:
                        actual_state = 'established'
                    else:
                        actual_state = session_state
                
                # Validate the state
                if not peer_found:
                    self.failed(f"{device_name}: Could not determine state for BGP peer {peer_ip}")
                elif actual_state != expected_state:
                    self.failed(f"{device_name}: BGP peer {peer_ip} in state {actual_state}, expected {expected_state}")
                else:
                    logger.info(f"{device_name}: BGP peer {peer_ip} in expected state: {actual_state}")
    
    @aetest.test
    def validate_bgp_routes(self, testbed):
        """Validate that BGP is advertising/receiving routes"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected BGP config
            if device_name not in EXPECTED_BGP_PEERS:
                continue
                
            logger.info(f"Validating BGP routes for {device_name}")
            
            # Get BGP routes
            try:
                bgp_routes = device.parse('show ip bgp')
            except Exception as e:
                logger.warning(f"Could not parse BGP routes for {device_name}: {e}")
                continue
                
            # Check if any BGP routes exist
            total_routes = 0
            
            # Navigate through the BGP routes structure
            for vrf_name, vrf_data in bgp_routes.get('vrf', {}).items():
                for address_family, af_data in vrf_data.get('address_family', {}).items():
                    if address_family.startswith('ipv4'):
                        # Count routes in main table
                        total_routes += len(af_data.get('routes', {}))
            
            if total_routes == 0:
                self.failed(f"{device_name}: No BGP routes found, device might not be exchanging routes")
            else:
                logger.info(f"{device_name}: Found {total_routes} BGP routes - device is exchanging routes")
