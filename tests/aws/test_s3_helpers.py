# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import botocore.session
import pytest
from botocore.stub import Stubber

from pyfaaster.aws.s3_helpers import verify_bucket_access


@pytest.mark.unit
def test_verify_bucket_access():
    bucket_name = 'bucket'
    s3 = botocore.session.get_session().create_client('s3')

    expected_response = {}
    expected_parameters = {'Bucket': 'bucket'}

    with Stubber(s3) as stubber:
        stubber.add_response('head_bucket', expected_response, expected_parameters)
        response = verify_bucket_access(s3, bucket_name)
        assert response
