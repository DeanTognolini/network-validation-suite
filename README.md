# Network Validation Suite

A comprehensive set of pyATS tests for validating network device configurations and protocols.

## Overview

This suite provides automated testing for:

- Device Configuration (AAA, SSH, TTY, Users, Interfaces)
- Network Topology (CDP neighbors)
- OSPF Neighbor Validation
- BGP Peer Validation
- LDP Peer Validation
- MPLS Configuration and Operation

## Project Structure

```
network-validation-suite/
├── README.md                     # Project documentation
├── testbed.yaml                  # Network device definitions
├── network_validation_job.py     # Main job file
├── tests/                        # Test scripts directory
│   ├── config_validator.py       # Configuration validation
│   ├── topology_validator.py     # CDP neighbor validation
│   ├── ospf_validator.py         # OSPF validation
│   ├── bgp_validator.py          # BGP validation
│   ├── ldp_validator.py          # LDP validation
│   └── mpls_validator.py         # MPLS validation
├── config/                       # Expected configuration files
│   ├── expected_bgp_peers.yaml   # Expected BGP peers
│   ├── expected_ldp_peers.yaml   # Expected LDP peers
│   ├── expected_mpls_config.yaml # Expected MPLS config
│   └── expected_ospf_neighbors.yaml # Expected OSPF neighbors
├── results/                      # Test results directory (auto-created)
├── archive/                      # pyATS archives (auto-created)
└── requirements.txt              # Dependencies
```

## Requirements

- Python 3.6+
- pyATS and Genie
- Network devices with SSH access

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/network-validation-suite.git
cd network-validation-suite
```

2. Build the Docker image
```bash
docker build -t network-validation-suite .
```

3. Run the Docker container
```bash
docker run -it --network=host -v .:/app network-validation-suite bash
```

### Docker Compose (Optional)
```yaml
version: '3'
services:
  network-validation-suite:
    build: .
    network_mode: "host"
    volumes:
      - .:/app
    command: bash
```

Then run with:

```bash
docker-compose up -d
docker-compose exec network-validation-suite bash
```

## Setup

### 1. Testbed File

The `testbed.yaml` file describes your network devices and their topology. An example is provided that includes:

- Core routers (core-router-1, core-router-2)
- Edge routers (edge-router-1, edge-router-2, inet-edge)
- Distribution routers (distribution-router-1, distribution-router-2)
- Access routers (access-router-1 through access-router-4)
- Provider edge routers (pe-router-1, pe-router-2)
- Management router (mgmt-router)

The testbed file contains:
- Device definitions (OS, type, IP addresses, credentials)
- Interface definitions (names, IP addresses)
- Network topology (links between devices)

### 2. Expected Configuration Files

The `/config` directory contains YAML files that define the expected state of your network:

- **expected_bgp_peers.yaml** - Defines BGP peers and their expected states
- **expected_ldp_peers.yaml** - Defines LDP peers and their operational states
- **expected_mpls_config.yaml** - Defines MPLS interfaces and forwarding configuration
- **expected_ospf_neighbors.yaml** - Defines OSPF neighbor counts per process

## Running Tests

### Using the Job File (Recommended)

The `network_validation_job.py` file runs all tests sequentially:

```bash
pyats run job network_validation_job.py
```

This will:
- Connect to all devices in the testbed
- Run all validation tests
- Generate a consolidated HTML report

### Running Individual Tests

You can also run individual tests:

```bash
python -m tests.ospf_validator -testbed_file testbed.yaml
```

## Test Details

### Configuration Validator
Tests security configurations including:
- AAA configuration
- SSH settings
- TTY configurations
- User accounts
- Interface configurations

### Topology Validator
Verifies network topology using CDP:
- Validates CDP neighbors match expected topology
- Checks for unexpected neighbors
- Normalizes interface names for consistent comparison

### OSPF Validator
Validates OSPF neighbor relationships:
- Compares neighbor counts against expected values
- Verifies OSPF neighbor states (FULL/2WAY)
- Supports multiple OSPF processes

### BGP Validator
Validates BGP peering relationships:
- Verifies expected BGP peers exist
- Checks BGP session states
- Validates AS numbers
- Confirms routes are being exchanged

### LDP Validator
Validates MPLS LDP operations:
- Verifies LDP peers are operational
- Checks label bindings are exchanged
- Validates LDP is enabled on expected interfaces

### MPLS Validator
Validates MPLS configuration:
- Verifies MPLS is enabled on correct interfaces
- Checks forwarding table entry counts
- Validates MPLS TE tunnels if configured

## Customization

### Modifying Test Scripts

Each test script follows the same structure:
- `CommonSetup`: Connects to devices
- Test Case Classes: Contains various test methods
- `CommonCleanup`: Disconnects from devices

You can add new test methods or modify existing ones to meet your requirements.

### Adapting Configuration Files

Update the YAML configuration files in the `config/` directory to reflect your network's expected state. The examples provided show the structure, but should be customized for your environment.

## Test Reports

The pyATS framework generates detailed reports in the `archive` directory:
- HTML report with overall results
- Log files for each test
- Pass/fail status and detailed error messages

## Troubleshooting

- **Connection Issues**: Verify device credentials and SSH connectivity
- **Parsing Errors**: Some command outputs vary by OS version - check the device output
- **Test Failures**: Review logs in the archive directory for detailed error information
- **Path Issues**: Ensure configuration files are in the correct directories

## License

This project is licensed under the MIT License - see the LICENSE file for details.
