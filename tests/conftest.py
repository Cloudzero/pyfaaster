# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import os
import re
import sys
import time

import boto3
import docker
import pytest

LOCALSTACK_IMAGE = "localstack/localstack:0.7.3"


###################
# Helper Functions
###################
def connect_to_local_docker():
    def __ping__(client):
        client.ping()

    docker_client = docker.from_env()

    try:
        __ping__(docker_client)
    except (TimeoutError, ConnectionError):
        print("ERROR: Docker does not appear to be up and running. Please start docker and try again.")
        sys.exit(1)

    return docker_client


def extract_localstack_ports_by_service(container):
    # Extract service and port from any string like 'Starting mock S3 (http port 4572)...' in the logs
    logs = str(container.logs())
    results = re.findall(r'Starting mock ([\w]+).*? \(http port ([\d]+)\)', logs)

    # Map internal service port to docker published port
    return {x[0]: container.attrs['NetworkSettings']['Ports']['{}/tcp'.format(x[1])][0]['HostPort'] for x in results}


###################
# Fixtures
###################
@pytest.fixture(scope="session")
def docker_cleanup(request, docker_client):
    containers_before = docker_client.containers.list()
    containers_before_ids = [container.id for container in containers_before]

    def kill_new_containers():
        current_containers = docker_client.containers.list()
        for container in current_containers:
            if container.id not in containers_before_ids:
                print('Cleaning up docker container: {} ({})'.format(container.short_id, container.name))
                container.kill()
                container.remove()

    request.addfinalizer(kill_new_containers)
    return kill_new_containers


@pytest.fixture(scope="session")
def docker_client():
    client = connect_to_local_docker()
    return client


@pytest.fixture(scope="session")
def localstack(docker_client, docker_cleanup):
    SERVICES = "SERVICES=s3,dynamodb,lambda,sns"
    container = docker_client.containers.run(LOCALSTACK_IMAGE,
                                             publish_all_ports=True,
                                             name="reactor-cli-localstack",
                                             detach=True,
                                             environment=[SERVICES])
    logs = container.logs()
    try_count = 0
    while container.status != "running" or "Ready.".encode() not in logs:
        container.reload()
        logs = container.logs()
        try_count += 1
        time.sleep(0.5)
        if try_count > 40:
            break
    else:
        time.sleep(0.5)
        return extract_localstack_ports_by_service(container)

    pytest.fail("Could not create Localstack Docker container. Msg: {}".format(container.logs()))


@pytest.fixture(scope="function")
def dynamodb(localstack):
    dynamodb_port = localstack.get('DynamoDB')
    dynamodb_endpointurl = f'http://localhost:{dynamodb_port}'
    os.environ['DYNAMODB_ENDPOINTURL'] = dynamodb_endpointurl
    yield boto3.resource('dynamodb', endpoint_url=dynamodb_endpointurl)
    del os.environ['DYNAMODB_ENDPOINTURL']


@pytest.fixture(scope="function")
def s3(localstack):
    s3_port = localstack.get('S3')
    s3_endpointurl = f'http://localhost:{s3_port}'
    return s3_endpointurl
