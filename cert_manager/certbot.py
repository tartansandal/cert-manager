"""The main CertificateManager class that interacts with Certbot."""

import logging
import pathlib
import subprocess


logger = logging.getLogger(__name__)


class CertbotClient:
    """A client to interact with Certbot."""

    def __init__(self, contact_email=None, webroot_path=None, deploy_hook=None,
                 letsencrypt_use_staging=None):
        """Initialize the Certbot client."""
        self.contact_email = contact_email
        self.webroot_path = webroot_path
        self.deploy_hook = deploy_hook
        self.letsencrypt_use_staging = letsencrypt_use_staging

    def request_cert(self, domains):
        """Request a new SSL certificate from Let's Encrypt."""
        command = [
            "certbot", "certonly",
            "--email", self.contact_email,
            "--webroot",
            "--webroot-path", self.webroot_path,
            "--non-interactive",
            "--agree-tos",
            "--keep",
            "--allow-subset-of-names",
            "--deploy-hook", self.deploy_hook,
            "--cert-name", domains[0],
        ]
        if self.letsencrypt_use_staging:
            command.append("--staging")
        for domain in domains:
            command += ["--domain", domain]
        result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if result.returncode == 0:
            logger.info(
                "Successfully obtained a new certificate for these domains:\n    %s",
                "\n    ".join(domains),
            )
        else:
            logger.error(
                "Failed to obtain a new certificate for these domains:\n    %s\n%s",
                "\n    ".join(domains),
                result.stderr,
            )

    def get_cert_data_from_live_dir(self, live_dir):
        """Load the PEM data from the given Certbot live directory.

        The directory must be a pathlib.Path object.
        """
        fullchain = (live_dir / "fullchain.pem").read_bytes()
        privkey = (live_dir / "privkey.pem").read_bytes()
        return fullchain + privkey

    def get_cert_data(self, main_domain):
        """Load the PEM data from Certbot's output directory."""
        live_dir = pathlib.Path("/etc/letsencrypt/live", main_domain)
        return self.get_cert_data_from_live_dir(live_dir)

    def remove_cert(self, main_domain):
        """Remove a certificate from Certbot and the backend storage."""
        command = [
            "certbot", "delete",
            "--cert-name", main_domain,
        ]
        result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if result.returncode == 0:
            logger.info(
                "Successfully deleted the certificate for %s from Certbot.", main_domain
            )
        else:
            logger.error(
                "Failed to delete the certificate for %s from Certbot:\n%s",
                main_domain,
                result.stderr,
            )

    def list_certs(self):
        """List the certificate names of all certificates currently managed by Certbot."""
        result = subprocess.run(
            ["certbot", "certificates"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.returncode != 0:
            logger.error("Listing certificates managed by Certbot failed:\n%s", result.stderr)
            return []
        return [
            line.partition(": ")[-1]
            for line in result.stdout.splitlines()
            if "Certificate Name:" in line
        ]
