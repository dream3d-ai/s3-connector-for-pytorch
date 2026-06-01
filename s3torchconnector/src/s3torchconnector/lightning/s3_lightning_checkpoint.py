#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  // SPDX-License-Identifier: BSD

from packaging import version
from typing import Optional, Dict, Any

import lightning
import torch

from lightning.pytorch.plugins.io import CheckpointIO

from .._s3client import S3Client, S3ClientConfig, resolve_s3client_config
from .._s3dataset_common import parse_s3_uri
from .._user_agent import UserAgent


class S3LightningCheckpoint(CheckpointIO):
    """A checkpoint manager for S3 using the :class:`CheckpointIO` interface."""

    def __init__(
        self,
        region: str,
        s3client_config: Optional[S3ClientConfig] = None,
        endpoint: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        part_size: Optional[int] = None,
        force_path_style: Optional[bool] = None,
    ):
        """Initialize an S3-backed Lightning checkpoint plugin.

        Args:
            region (str): S3 region or provider-specific signing region used for requests.
                For S3-compatible object stores, this can be a value such as "auto" or "eu-north1".
            s3client_config (Optional[S3ClientConfig]): Optional S3ClientConfig with parameters for the
                S3 client.
            endpoint (Optional[str]): Custom S3 endpoint. Prefer endpoint_url for new code.
            endpoint_url (Optional[str]): Endpoint URL of an S3-compatible object store.
            access_key_id (Optional[str]): Static access key ID for S3 authentication.
            secret_access_key (Optional[str]): Static secret access key for S3 authentication.
            part_size (Optional[int]): Multipart upload/download part size in bytes.
            force_path_style (Optional[bool]): Whether to force path-style addressing.
        """
        self.region = region
        s3client_config = resolve_s3client_config(
            s3client_config,
            endpoint=endpoint,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            part_size=part_size,
            force_path_style=force_path_style,
        )
        user_agent = UserAgent(["lightning", lightning.__version__])
        self._client = S3Client(
            region,
            user_agent=user_agent,
            s3client_config=s3client_config,
        )

    def save_checkpoint(
        self,
        checkpoint: Dict[str, Any],
        # We only support `str` arguments for `path`, as `Path` is explicitly for local filesystems
        path: str,  # type: ignore
        storage_options: Optional[Any] = None,
    ) -> None:
        """Save model/training states as a checkpoint file through state-dump and upload to S3.

        Args:
            checkpoint (Dict[str, Any]): Containing model and trainer state
            path (str): Write-target S3 uri
            storage_options: Optional parameters when saving the model/training states.
        """
        self._validate_path(path)
        bucket, key = parse_s3_uri(path)
        with self._client.put_object(bucket, key) as s3writer:
            torch.save(checkpoint, s3writer)

    def load_checkpoint(
        self,
        # We only support `str` arguments for `path`, as `Path` is explicitly for local filesystems
        path: str,  # type: ignore
        map_location: Optional[Any] = None,
        weights_only: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Load checkpoint from an S3 location when resuming or loading ckpt for test/validate/predict stages.

        Args:
            path (str): S3 uri to checkpoint
            map_location: A function, :class:`torch.device`, string or a dict specifying how to remap storage locations.
            weights_only: If True, only loads tensors and primitive types (safer). If False, allows loading
                arbitrary Python objects (less secure). If None, uses PyTorch Lightning default behavior.
                See https://docs.pytorch.org/docs/main/notes/serialization.html for details.

        Returns:
            Dict[str, Any]: The loaded checkpoint

        Raises:
            S3Exception: An error occurred accessing S3.
        """
        self._validate_path(path)
        bucket, key = parse_s3_uri(path)
        s3reader = self._client.get_object(bucket, key)
        # FIXME - io.BufferedIOBase and typing.IO aren't compatible
        #  See https://github.com/python/typeshed/issues/6077

        # Maintain backward compatibility: Default to False for Lightning <2.6, and None for Lightning>=2.6.
        # - Lightning >=2.6 lets PyTorch decide on default behavior. weights_only can now be set through Trainer.{fit,validate,test,predict}.
        # - Lightning <2.6 defaults to weights_only=False: https://github.com/Lightning-AI/pytorch-lightning/blob/release/2.5.x/src/lightning/fabric/utilities/cloud_io.py#L37
        if weights_only is None:
            if version.parse(lightning.__version__) < version.parse("2.6.0"):
                weights_only = False

        # Note in PyTorch <2.4, torch.load() requires non optional bool - however None acts as False in
        # `if weights_only:` checks (default for PyTorch <2.6 or Lightning <2.6) for backwards compatibility.
        # As mitigation, users can set TORCH_FORCE_WEIGHTS_ONLY_LOAD (0 or 1) to control weights_only behavior.

        return torch.load(s3reader, map_location, weights_only=weights_only)  # type: ignore

    def remove_checkpoint(
        self,
        # We only support `str` arguments for `path`, as `Path` is explicitly for local filesystems
        path: str,  # type: ignore
    ) -> None:
        """Remove checkpoint file from the S3 uri.

        Args:
            path (str): S3 uri to checkpoint

        Raises:
            S3Exception: An error occurred accessing S3.
        """
        self._validate_path(path)
        bucket, key = parse_s3_uri(path)
        self._client.delete_object(bucket, key)

    def teardown(self) -> None:
        """This method is called to teardown the process."""
        pass

    @staticmethod
    def _validate_path(path: str) -> None:
        if not isinstance(path, str):
            raise TypeError(
                f"{type(path).__name__!r} is not a supported type for 'path'. Must be a string formatted as an S3 uri."
            )
