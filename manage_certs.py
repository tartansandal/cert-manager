#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Certificate manager based on Certbot, using Consul for certificate storage.

This script is intended to be run as a cron job or a "consul watch" client.  It retrieves domains
it is supposed to request certificates for from Consul, requests certificates for domain groups that
don't have one yet and removes unused certificates.

Certificates are requested using Certbot.
"""

import argparse
import logging
import pathlib
import sys

import consul

from cert_manager import CertificateManager
from cert_manager.certbot import CertbotClient
from cert_manager.backends import ConsulCertificateStorage, ConsulDomainConfiguration
from cert_manager.utils import configure_logger

logger = logging.getLogger()


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser with more useful config file syntax."""

    def convert_arg_line_to_args(self, arg_line):
        """Treat each space-separated word as a separate argument."""
        return arg_line.split()


def parse_command_line(args):
    """Parse the command-line arguments."""
    parser = ArgumentParser(fromfile_prefix_chars="@")
    parser.add_argument("--contact-email", required=True)
    parser.add_argument("--letsencrypt-use-staging", action="store_true")
    parser.add_argument("--log-level", default="info")
    parser.add_argument("--additional-domain", action="append")
    parser.add_argument("--consul-ocim-prefix", default="ocim/instances")
    parser.add_argument("--consul-certs-prefix", default="certs")
    parser.add_argument("--webroot-path", default="/var/www/certbot")
    parser.add_argument("--consul-token")
    parser.add_argument("--deploy-hook")
    return parser.parse_args(args)


def main(args):
    """Parse command line, run certificate manager."""
    config = parse_command_line(args)
    configure_logger(logger, config.log_level.upper())
    cert_manager_dir = pathlib.Path(__file__).resolve().parent
    pipfile_location = cert_manager_dir.joinpath('Pipfile')
    if not config.deploy_hook:
        pipenv_prefix_command = 'PIPENV_PIPFILE={} /usr/local/bin/pipenv run python '
        deploy_cert_command = "{}/deploy_cert.py --log-level '{}' --consul-certs-prefix '{}'"
        config.deploy_hook = (pipenv_prefix_command + deploy_cert_command).format(
                str(pipfile_location), str(cert_manager_dir), config.log_level, config.consul_certs_prefix
        )
    certbot_client = CertbotClient(
        contact_email=config.contact_email,
        webroot_path=config.webroot_path,
        deploy_hook=config.deploy_hook,
        letsencrypt_use_staging=config.letsencrypt_use_staging,
    )
    consul_client = consul.Consul(token=config.consul_token)
    manager = CertificateManager(
        certbot_client,
        ConsulDomainConfiguration(config.consul_ocim_prefix, consul_client=consul_client),
        ConsulCertificateStorage(config.consul_certs_prefix, consul_client=consul_client),
        config.additional_domain,
    )
    manager.run()


if __name__ == "__main__":
    main(sys.argv[1:])
