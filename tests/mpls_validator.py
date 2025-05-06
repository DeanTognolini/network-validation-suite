"""
MPLS Validator Test Script
==========================
This script validates MPLS configuration and operation on network devices.
It checks MPLS interfaces, forwarding, and LSP tunnels if applicable.

Example of expected_mpls_config.yaml file:
-----------------------------------------
router1:
  enabled_interfaces:
    - GigabitEthernet0/0
    - GigabitEthernet0/1
  tunnel_count: 2
  forwarding_entries_min: 10
router2:
  enabled_interfaces:
    - GigabitEthernet0/0
    - GigabitEthernet0/2
  tunnel_count: 2
  forwarding_entries_min: 10
"""

import os
import logging
import yaml
from pyats import aetest
from genie.testbed import load

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define expected MPLS configuration
# This can be loaded from a separate YAML file for flexibility
EXPECTED_MPLS_CONFIG = {
    # Format: 'device_name': {'enabled_interfaces': [], 'tunnel_count': int, 'forwarding_entries_min': int}
    'router1': {
        'enabled_interfaces': ['GigabitEthernet0/0', 'GigabitEthernet0/1'],
        'tunnel_count': 2,
        'forwarding_entries_min': 10
    },
    'router2': {
        'enabled_interfaces': ['GigabitEthernet0/0', 'GigabitEthernet0/2'],
        'tunnel_count': 2,
        'forwarding_entries_min': 10
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
        # Load expected MPLS config from file if available
        try:
            # Check for config in the config directory (structured project)
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
            if os.path.exists(os.path.join(config_dir, 'expected_mpls_config.yaml')):
                config_path = os.path.join(config_dir, 'expected_mpls_config.yaml')
            else:
                # Fall back to current directory
                config_path = 'expected_mpls_config.yaml'
                
            with open(config_path, 'r') as f:
                expected_mpls = yaml.safe_load(f)
                if expected_mpls:
                    global EXPECTED_MPLS_CONFIG
                    EXPECTED_MPLS_CONFIG = expected_mpls
                    logger.info(f"Loaded expected MPLS configuration from {config_path}")
        except FileNotFoundError:
            logger.info("No custom MPLS config file found, using default expectations")
        except Exception as e:
            logger.error(f"Error loading MPLS config file: {e}")
        
        # Log the expected MPLS configuration
        logger.info(f"Expected MPLS configuration: {yaml.dump(EXPECTED_MPLS_CONFIG)}")
        
        # Check device connectivity
        for device_name, device in testbed.devices.items():
            if not device.connected:
                self.failed(f"Failed to connect to {device_name}")
            logger.info(f"Successfully connected to {device_name}")

class MPLSValidator(aetest.Testcase):
    """Test case to validate MPLS configuration and operation"""
    
    @aetest.test
    def validate_mpls_interfaces(self, testbed):
        """Validate that MPLS is enabled on expected interfaces"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected MPLS config
            if device_name not in EXPECTED_MPLS_CONFIG:
                logger.info(f"No MPLS expectations defined for {device_name}, skipping")
                continue
                
            logger.info(f"Validating MPLS interfaces for {device_name}")
            
            # Get interfaces with MPLS enabled
            try:
                mpls_interfaces = device.parse('show mpls interfaces')
            except Exception as e:
                self.failed(f"Failed to parse MPLS interfaces for {device_name}: {e}")
                continue
                
            # Check if any MPLS-enabled interfaces were found
            enabled_interfaces = []
            
            # Navigate through the MPLS interface structure - varies by OS
            # IOS/IOS-XE structure
            for intf_name, intf_data in mpls_interfaces.get('interfaces', {}).items():
                if intf_data.get('mpls', {}).get('ldp', False):
                    enabled_interfaces.append(intf_name)
            
            # Alternative structure for some OS versions
            if not enabled_interfaces:
                for vrf_name, vrf_data in mpls_interfaces.get('vrf', {}).items():
                    for intf_name, intf_data in vrf_data.get('interfaces', {}).items():
                        if intf_data.get('enabled', False):
                            enabled_interfaces.append(intf_name)
            
            # Check expected interfaces
            expected_interfaces = EXPECTED_MPLS_CONFIG[device_name].get('enabled_interfaces', [])
            
            for expected_intf in expected_interfaces:
                # Normalize interface names for comparison
                expected_intf_norm = self._normalize_interface_name(expected_intf)
                
                # Check if the expected interface is enabled for MPLS
                intf_found = False
                for actual_intf in enabled_interfaces:
                    actual_intf_norm = self._normalize_interface_name(actual_intf)
                    if expected_intf_norm == actual_intf_norm:
                        intf_found = True
                        logger.info(f"{device_name}: MPLS enabled on expected interface {expected_intf}")
                        break
                
                if not intf_found:
                    self.failed(f"{device_name}: MPLS not enabled on expected interface {expected_intf}")
    
    @aetest.test
    def validate_mpls_forwarding(self, testbed):
        """Validate MPLS forwarding table"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected MPLS config
            if device_name not in EXPECTED_MPLS_CONFIG:
                continue
                
            logger.info(f"Validating MPLS forwarding for {device_name}")
            
            # Get MPLS forwarding table
            try:
                mpls_forwarding = device.parse('show mpls forwarding-table')
            except Exception as e:
                logger.warning(f"Could not parse MPLS forwarding table for {device_name}: {e}")
                continue
                
            # Count forwarding entries
            entry_count = 0
            
            # Navigate through the forwarding table structure
            for vrf_name, vrf_data in mpls_forwarding.get('vrf', {}).items():
                entry_count += len(vrf_data.get('local_label', {}))
            
            # Alternative structure
            if entry_count == 0:
                entry_count = len(mpls_forwarding.get('local_label', {}))
            
            # Check against minimum expected entries
            min_entries = EXPECTED_MPLS_CONFIG[device_name].get('forwarding_entries_min', 0)
            
            if entry_count < min_entries:
                self.failed(f"{device_name}: MPLS forwarding table has {entry_count} entries, "
                           f"expected at least {min_entries}")
            else:
                logger.info(f"{device_name}: MPLS forwarding table has {entry_count} entries, "
                           f"meeting minimum of {min_entries}")
    
    @aetest.test
    def validate_mpls_tunnels(self, testbed):
        """Validate MPLS TE tunnels if specified"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected MPLS config or no tunnel count
            if device_name not in EXPECTED_MPLS_CONFIG or 'tunnel_count' not in EXPECTED_MPLS_CONFIG[device_name]:
                continue
                
            logger.info(f"Validating MPLS tunnels for {device_name}")
            
            # Get MPLS tunnels
            try:
                mpls_tunnels = device.parse('show mpls traffic-eng tunnels')
            except Exception as e:
                logger.warning(f"Could not parse MPLS tunnels for {device_name}: {e}")
                continue
                
            # Count tunnels
            tunnel_count = 0
            
            # Navigate through the tunnel structure
            for tunnel_id, tunnel_data in mpls_tunnels.get('tunnels', {}).items():
                if tunnel_data.get('state', '').lower() == 'up':
                    tunnel_count += 1
            
            # Alternative structure
            if tunnel_count == 0:
                tunnel_count = len([t for t in mpls_tunnels.get('tunnel_id', {}).values() 
                                   if t.get('admin_state', '').lower() == 'up'])
            
            # Check against expected count
            expected_tunnels = EXPECTED_MPLS_CONFIG[device_name].get('tunnel_count', 0)
            
            if tunnel_count != expected_tunnels:
                self.failed(f"{device_name}: Found {tunnel_count} active MPLS tunnels, "
                           f"expected {expected_tunnels}")
            else:
                logger.info(f"{device_name}: Found expected number of MPLS tunnels: {tunnel_count}")
    
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
