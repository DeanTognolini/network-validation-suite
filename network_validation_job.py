#!/usr/bin/env python
"""
Network Validation Job
=====================
This job file runs all the network validation test scripts in sequence.
It generates a consolidated report for all test cases.
"""

import os
import logging
from pyats.easypy import run

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(runtime):
    """
    Main function that runs all the test scripts
    :param runtime: Runtime object provided by pyATS
    """
    # Set the testbed file
    testbed_file = os.path.join(os.path.dirname(__file__), 'testbed.yaml')
    
    # Set paths to test scripts
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    # Set the results directory
    result_dir = os.path.join('results', runtime.directory)
    os.makedirs(result_dir, exist_ok=True)
    
    logger.info("Starting Network Validation Tests")
    
    # Run configuration validator
    run(testscript=os.path.join(tests_dir, 'config_validator.py'), 
        testbed=testbed_file,
        runtime=runtime,
        taskid='Configuration Validation')
    
    # Run topology validator
    run(testscript=os.path.join(tests_dir, 'topology_validator.py'), 
        testbed=testbed_file,
        runtime=runtime,
        taskid='Topology Validation')
    
    # Run OSPF validator
    run(testscript=os.path.join(tests_dir, 'ospf_validator.py'), 
        testbed=testbed_file,
        runtime=runtime,
        taskid='OSPF Validation')
    
    # Run BGP validator
    run(testscript=os.path.join(tests_dir, 'bgp_validator.py'), 
        testbed=testbed_file,
        runtime=runtime,
        taskid='BGP Validation')
    
    # Run LDP validator
    run(testscript=os.path.join(tests_dir, 'ldp_validator.py'), 
        testbed=testbed_file,
        runtime=runtime,
        taskid='LDP Validation')
    
    # Run MPLS validator
    run(testscript=os.path.join(tests_dir, 'mpls_validator.py'), 
        testbed=testbed_file,
        runtime=runtime,
        taskid='MPLS Validation')
    
    logger.info("All Network Validation Tests Completed")
