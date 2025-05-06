"""
Network Topology Validator Test Script
======================================
This script validates network topology by checking CDP neighbors.
It compares discovered CDP neighbors against expected topology defined in the testbed.
"""

import logging
import yaml
from pyats import aetest
from genie.testbed import load

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all devices in the testbed"""
        testbed.connect(log_stdout=False)
    
    @aetest.subsection
    def prepare_testbed(self, testbed):
        """Prepare testbed for topology validation"""
        # Load expected topology from the testbed file
        for device_name, device in testbed.devices.items():
            if not device.connected:
                self.failed(f"Failed to connect to {device_name}")
            logger.info(f"Successfully connected to {device_name}")
            
            # Store the devices in the testcase
            self.parent.parameters.update(testbed=testbed)

class TopologyValidator(aetest.Testcase):
    """Test case to validate network topology using CDP"""
    
    @aetest.setup
    def setup(self, testbed):
        """Setup for topology validation"""
        # Create a map of expected CDP neighbors from testbed links
        self.expected_neighbors = {}
        
        # Build expected topology from testbed links
        for link_name, link in testbed.links.items():
            for device1_name, intf1 in link.interfaces.items():
                device1 = testbed.devices[device1_name]
                
                # Initialize neighbor list for device if not already there
                if device1_name not in self.expected_neighbors:
                    self.expected_neighbors[device1_name] = {}
                
                # For each device, add all other devices on this link as expected neighbors
                for device2_name, intf2 in link.interfaces.items():
                    if device1_name != device2_name:
                        device2 = testbed.devices[device2_name]
                        
                        # Add this device as expected neighbor with interface
                        self.expected_neighbors[device1_name][device2_name] = {
                            'local_interface': intf1.name,
                            'remote_interface': intf2.name
                        }
        
        # Log the expected topology
        logger.info(f"Expected topology: {yaml.dump(self.expected_neighbors)}")
    
    @aetest.test
    def validate_cdp_neighbors(self, testbed):
        """Validate CDP neighbor relationships"""
        for device_name, device in testbed.devices.items():
            logger.info(f"Validating CDP neighbors for {device_name}")
            
            # Skip validation if device not in expected neighbors
            if device_name not in self.expected_neighbors:
                logger.info(f"No expected neighbors defined for {device_name}, skipping")
                continue
            
            # Get actual CDP neighbors
            try:
                cdp_neighbors = device.parse('show cdp neighbors detail')
            except Exception as e:
                self.failed(f"Failed to parse CDP neighbors for {device_name}: {e}")
                continue
            
            if not cdp_neighbors or 'index' not in cdp_neighbors:
                self.failed(f"No CDP neighbors found for {device_name}")
                continue
            
            # Check each expected neighbor
            for expected_neighbor_name, expected_data in self.expected_neighbors[device_name].items():
                expected_local_intf = expected_data['local_interface']
                expected_remote_intf = expected_data['remote_interface']
                
                # Convert expected neighbor name to hostname format that might appear in CDP
                expected_hostname = expected_neighbor_name
                
                # Look for the expected neighbor in CDP output
                neighbor_found = False
                for idx, neighbor_data in cdp_neighbors['index'].items():
                    # Check if this neighbor matches our expected one
                    # We check both the device hostname and domain name if available
                    if (neighbor_data.get('device_id', '').lower() == expected_hostname.lower() or
                        expected_hostname.lower() in neighbor_data.get('device_id', '').lower()):
                        
                        local_intf = neighbor_data.get('local_interface', '')
                        remote_intf = neighbor_data.get('port_id', '')
                        
                        # Normalize interface names for comparison
                        local_intf_norm = self._normalize_interface_name(local_intf)
                        remote_intf_norm = self._normalize_interface_name(remote_intf)
                        expected_local_intf_norm = self._normalize_interface_name(expected_local_intf)
                        expected_remote_intf_norm = self._normalize_interface_name(expected_remote_intf)
                        
                        if (local_intf_norm == expected_local_intf_norm and 
                            remote_intf_norm == expected_remote_intf_norm):
                            neighbor_found = True
                            logger.info(f"Found expected neighbor {expected_neighbor_name} on "
                                       f"{device_name} interface {local_intf} connecting to {remote_intf}")
                            break
                
                if not neighbor_found:
                    self.failed(f"{device_name}: Expected neighbor {expected_neighbor_name} on "
                                f"interface {expected_local_intf} connecting to {expected_remote_intf} NOT found")
    
    @aetest.test
    def validate_unexpected_neighbors(self, testbed):
        """Check for unexpected CDP neighbors not defined in testbed"""
        for device_name, device in testbed.devices.items():
            logger.info(f"Checking for unexpected neighbors on {device_name}")
            
            # Skip validation if device not in expected neighbors
            if device_name not in self.expected_neighbors:
                logger.info(f"No expected neighbors defined for {device_name}, skipping")
                continue
                
            # Get actual CDP neighbors
            try:
                cdp_neighbors = device.parse('show cdp neighbors detail')
            except Exception as e:
                logger.error(f"Failed to parse CDP neighbors for {device_name}: {e}")
                continue
                
            if not cdp_neighbors or 'index' not in cdp_neighbors:
                logger.info(f"No CDP neighbors found for {device_name}")
                continue
                
            # Create list of expected neighbor hostnames for this device
            expected_hostnames = [name.lower() for name in self.expected_neighbors[device_name].keys()]
            
            # Check each actual neighbor
            for idx, neighbor_data in cdp_neighbors['index'].items():
                neighbor_hostname = neighbor_data.get('device_id', '').split('.')[0].lower()
                
                # Check if this neighbor is unexpected
                unexpected = True
                for expected in expected_hostnames:
                    if expected in neighbor_hostname or neighbor_hostname in expected:
                        unexpected = False
                        break
                
                if unexpected:
                    local_intf = neighbor_data.get('local_interface', '')
                    remote_intf = neighbor_data.get('port_id', '')
                    self.failed(f"{device_name}: Unexpected neighbor {neighbor_hostname} found on "
                               f"interface {local_intf} connecting to {remote_intf}")
    
    def _normalize_interface_name(self, interface_name):
        """Normalize interface name for comparison by removing spaces and converting to lowercase"""
        if not interface_name:
            return ""
        
        # Remove spaces and convert to lowercase
        normalized = interface_name.replace(" ", "").lower()
        
        # Map short interface names to standard ones
        interface_map = {
            'gi': 'gigabitethernet',
            'ge': 'gigabitethernet',
            'fa': 'fastethernet',
            'fe': 'fastethernet',
            'te': 'tengigabitethernet',
            'eth': 'ethernet',
            'po': 'port-channel',
            'portch': 'port-channel',
            'lo': 'loopback'
        }
        
        # Try to match and replace short interface names
        for short, long in interface_map.items():
            if normalized.startswith(short):
                remaining = normalized[len(short):]
                if remaining and (remaining[0].isdigit() or remaining[0] == '/'):
                    normalized = long + remaining
                    break
        
        return normalized

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
