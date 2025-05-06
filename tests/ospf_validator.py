"""
OSPF Neighbor Validator Test Script
====================================
This script validates OSPF neighbors against expected values.
You can define expected number of neighbors per device and validate them.
"""

import logging
import yaml
from pyats import aetest
from genie.testbed import load

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define expected OSPF relationships
# This can be loaded from a separate YAML file for flexibility
EXPECTED_OSPF_NEIGHBORS = {
    # Format: 'device_name': {'process_id': expected_count}
    'router1': {'1': 2},  # Router1 should have 2 neighbors in process 1
    'router2': {'1': 3},  # Router2 should have 3 neighbors in process 1
    'router3': {'1': 2, '2': 1}  # Router3 has 2 neighbors in process 1, 1 in process 2
}

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all devices in the testbed"""
        testbed.connect(log_stdout=False)
    
    @aetest.subsection
    def prepare_testbed(self, testbed):
        """Prepare testbed and load configurations"""
        # Load expected OSPF neighbors from file if available
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'expected_bgp_peers.yaml')
            with open(config_path, 'r') as f:
                expected_ospf = yaml.safe_load(f)
                if expected_ospf:
                    global EXPECTED_OSPF_NEIGHBORS
                    EXPECTED_OSPF_NEIGHBORS = expected_ospf
                    logger.info("Loaded expected OSPF neighbor configuration from file")
        except FileNotFoundError:
            logger.info("No custom OSPF neighbor file found, using default expectations")
        except Exception as e:
            logger.error(f"Error loading OSPF neighbor file: {e}")
        
        # Log the expected OSPF configuration
        logger.info(f"Expected OSPF neighbors: {yaml.dump(EXPECTED_OSPF_NEIGHBORS)}")
        
        # Check device connectivity
        for device_name, device in testbed.devices.items():
            if not device.connected:
                self.failed(f"Failed to connect to {device_name}")
            logger.info(f"Successfully connected to {device_name}")

class OSPFNeighborValidator(aetest.Testcase):
    """Test case to validate OSPF neighbors"""
    
    @aetest.test
    def validate_ospf_neighbors_count(self, testbed):
        """Validate OSPF neighbor counts against expected values"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected OSPF config
            if device_name not in EXPECTED_OSPF_NEIGHBORS:
                logger.info(f"No OSPF expectations defined for {device_name}, skipping")
                continue
                
            logger.info(f"Validating OSPF neighbors for {device_name}")
            
            # Get OSPF neighbors
            try:
                ospf_neighbors = device.parse('show ip ospf neighbor')
            except Exception as e:
                self.failed(f"Failed to parse OSPF neighbors for {device_name}: {e}")
                continue
                
            # Check if any OSPF data was returned
            if not ospf_neighbors:
                self.failed(f"No OSPF data found for {device_name}")
                continue
                
            # Count neighbors per process
            actual_counts = {}
            
            # Parse OSPF output - structure might differ based on OS
            # This handles IOS-style output
            for process_id, process_data in ospf_neighbors.get('instance', {}).items():
                # Initialize process counter if not exists
                if process_id not in actual_counts:
                    actual_counts[process_id] = 0
                    
                # Count neighbors for this process
                for vrf_data in process_data.get('vrf', {}).values():
                    for area_data in vrf_data.get('areas', {}).values():
                        for intf_data in area_data.get('interfaces', {}).values():
                            actual_counts[process_id] += len(intf_data.get('neighbors', {}))
            
            # If no neighbors found, try alternative parsing structure
            if not actual_counts:
                # Try alternative parsing structure (different OS variants)
                for area_id, area_data in ospf_neighbors.get('areas', {}).items():
                    for intf_name, intf_data in area_data.get('interfaces', {}).items():
                        process_id = intf_data.get('process_id', '1')  # Default to 1 if not specified
                        
                        # Initialize process counter if not exists
                        if process_id not in actual_counts:
                            actual_counts[process_id] = 0
                            
                        # Count neighbors
                        actual_counts[process_id] += len(intf_data.get('neighbors', {}))
            
            # Log actual counts
            logger.info(f"{device_name} OSPF neighbor counts: {actual_counts}")
            
            # Compare with expected counts
            expected_counts = EXPECTED_OSPF_NEIGHBORS[device_name]
            
            for process_id, expected_count in expected_counts.items():
                actual_count = actual_counts.get(process_id, 0)
                
                if actual_count != expected_count:
                    self.failed(f"{device_name}: Process {process_id} has {actual_count} neighbors, "
                               f"expected {expected_count}")
                else:
                    logger.info(f"{device_name}: Process {process_id} has expected number of neighbors: {actual_count}")
    
    @aetest.test
    def validate_ospf_neighbor_states(self, testbed):
        """Validate that all OSPF neighbors are in FULL state (or 2WAY for DROTHER on broadcast networks)"""
        for device_name, device in testbed.devices.items():
            # Skip devices with no expected OSPF config
            if device_name not in EXPECTED_OSPF_NEIGHBORS:
                continue
                
            logger.info(f"Validating OSPF neighbor states for {device_name}")
            
            # Get OSPF neighbors
            try:
                ospf_neighbors = device.parse('show ip ospf neighbor')
            except Exception as e:
                self.failed(f"Failed to parse OSPF neighbors for {device_name}: {e}")
                continue
                
            # Check if any OSPF data was returned
            if not ospf_neighbors:
                continue
                
            # Check neighbor states
            neighbor_issues = []
            
            # Handle IOS-style output
            for process_id, process_data in ospf_neighbors.get('instance', {}).items():
                for vrf_name, vrf_data in process_data.get('vrf', {}).items():
                    for area_id, area_data in vrf_data.get('areas', {}).items():
                        for intf_name, intf_data in area_data.get('interfaces', {}).items():
                            network_type = intf_data.get('network_type', '')
                            
                            for nbr_id, nbr_data in intf_data.get('neighbors', {}).items():
                                state = nbr_data.get('state', '')
                                
                                # For broadcast or NBMA networks, DR/BDR should be FULL, others can be 2WAY
                                if network_type.lower() in ['broadcast', 'nbma']:
                                    if nbr_data.get('priority', 0) == 0:  # Not a DR or BDR eligible
                                        valid_states = ['full', '2way']
                                    else:
                                        valid_states = ['full']
                                else:
                                    valid_states = ['full']
                                    
                                if state.lower() not in valid_states:
                                    neighbor_issues.append(
                                        f"Process {process_id}, Interface {intf_name}, Neighbor {nbr_id}: "
                                        f"State is {state}, expected one of {valid_states}"
                                    )
            
            # If no neighbors found in first structure, try alternative parsing
            if not neighbor_issues and 'areas' in ospf_neighbors:
                for area_id, area_data in ospf_neighbors.get('areas', {}).items():
                    for intf_name, intf_data in area_data.get('interfaces', {}).items():
                        network_type = intf_data.get('network_type', '')
                        
                        for nbr_id, nbr_data in intf_data.get('neighbors', {}).items():
                            state = nbr_data.get('state', '')
                            
                            # For broadcast or NBMA networks, DR/BDR should be FULL, others can be 2WAY
                            if network_type.lower() in ['broadcast', 'nbma']:
                                if nbr_data.get('priority', 0) == 0:  # Not a DR or BDR eligible
                                    valid_states = ['full', '2way']
                                else:
                                    valid_states = ['full']
                            else:
                                valid_states = ['full']
                                
                            if state.lower() not in valid_states:
                                neighbor_issues.append(
                                    f"Interface {intf_name}, Neighbor {nbr_id}: "
                                    f"State is {state}, expected one of {valid_states}"
                                )
            
            # Report any issues
            if neighbor_issues:
                self.failed(f"{device_name} OSPF neighbor state issues:\n" + "\n".join(neighbor_issues))
            else:
                logger.info(f"{device_name}: All OSPF neighbors in correct states")

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
