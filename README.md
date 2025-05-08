# Network Validation Suite

A comprehensive set of pyATS tests for validating network device configurations and protocols.

## Overview

This suite provides automated testing for:

- OSPF Neighbor Validation
- LDP Neighbor Validation
- BGP Peer Validation (IOS-XE)

Work in progress:
- BGP Peer Validation (IOS-XR)
- Device Configuration (AAA, SSH, TTY, Users, Interfaces)
- Network Topology (CDP neighbors)
- MPLS Configuration and Operation

## Requirements

All you need is the [Docker Engine](https://docs.docker.com/engine/install/) installed.

## Installation

1. Clone this repository:

```bash
git clone https://github.com/DeanTognolini/network-validation-suite.git
cd network-validation-suite
```

2. Build the Docker image
```bash
docker build -t network-validation-suite .
```

3. Run the Docker container
```bash
docker run -it --rm -v .:/app -p 8080:8080 network-validation-suite bash
```

## Setup

### 1. Testbed File

The `testbed.yaml` file is stored in the `config` dir and describes your network devices and their topology. An example is provided.

The testbed file contains:
- Device definitions (OS, type, IP addresses, credentials)
- Interface definitions (names, IP addresses)
- Network topology (links between devices)

In the testbed.yaml file, change `username` to work with your environment. The password will be requested at runtime.

### 2. Define expected states

In each of the test folders contains the pyATS testscript, in here define the expected state of your network. An example is provided within each test script.

Example:
```python
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
```

## Running Tests

### Using the Job Files

Example using the `ospf_nei_check` test.

```bash
pyats run job ospf_nei_check/ospf_nei_check_job.py --testbed testbed.yaml
```

This will:
- Connect to all devices in the testbed
- Run all validation tests
- Generate a HTML report

## Test Details

### OSPF Validator
Validates OSPF neighbor relationships:
- Compares neighbor counts against expected values
- Verifies OSPF neighbor states (FULL/2WAY)

### LDP Validator
Validates MPLS LDP operations:
- Verifies LDP peers are operational

## Viewing the Test Reports

The pyATS framework generates detailed reports in the `/root/.pyats/archive` directory by default.

The reports contain:
- HTML report with overall results
- Log files for each test
- Pass/fail status and detailed error messages

To view the reports, run the `pyats logs view --host 0.0.0.0 --p 8080`, and navigate to http://localhost:8080 in your hosts web browser. Note that if you have specified a port other than `8080` you need to connect to the port you have set during the `docker run`.

## Troubleshooting

- **Connection Issues**: Verify device credentials and SSH connectivity
- **Test Failures**: Review logs in the archive directory for detailed error information
- **Path Issues**: Ensure configuration files are in the correct directories

## License

This project is licensed under the MIT License - see the LICENSE file for details.
