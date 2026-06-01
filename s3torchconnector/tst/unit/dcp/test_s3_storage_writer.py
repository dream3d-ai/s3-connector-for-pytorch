#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  // SPDX-License-Identifier: BSD

import pytest
from s3torchconnector import S3ClientConfig
from s3torchconnector.dcp import S3StorageWriter

TEST_REGION = "eu-east-1"
TEST_BUCKET = "test-bucket"
TEST_KEY = "test-key.txt"
TEST_PATH = f"s3://{TEST_BUCKET}/{TEST_KEY}"


@pytest.mark.parametrize("thread_count", [1, 2, 4, 8, 16])
def test_s3storage_writer_thread_count(thread_count):
    storage_writer = S3StorageWriter(
        region=TEST_REGION, path=TEST_PATH, thread_count=thread_count
    )
    assert storage_writer.thread_count == thread_count


def test_s3storage_writer_thread_count_defaults_to_one():
    storage_writer = S3StorageWriter(region=TEST_REGION, path=TEST_PATH)
    assert storage_writer.thread_count == 1


def test_s3storage_writer_direct_s3_compatible_config():
    writer = S3StorageWriter(
        region=TEST_REGION,
        path=TEST_PATH,
        endpoint_url="https://direct.example.com",
        access_key_id="direct-access-key-id",
        secret_access_key="direct-secret-access-key",
        part_size=64 * 1024 * 1024,
        force_path_style=True,
        s3client_config=S3ClientConfig(
            endpoint_url="https://config.example.com",
            access_key_id="config-access-key-id",
            secret_access_key="config-secret-access-key",
            part_size=16 * 1024 * 1024,
            force_path_style=False,
        ),
    )

    assert (
        writer.fs._client.s3client_config.endpoint_url == "https://direct.example.com"
    )
    assert writer.fs._client.s3client_config.access_key_id == "direct-access-key-id"
    assert (
        writer.fs._client.s3client_config.secret_access_key
        == "direct-secret-access-key"
    )
    assert writer.fs._client.s3client_config.part_size == 64 * 1024 * 1024
    assert writer.fs._client.s3client_config.force_path_style is True
