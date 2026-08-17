#!/usr/bin/env python3
"""
Generate Self-Signed SSL Certificate for Local Development

For production, use Let's Encrypt or a commercial CA.
"""

from OpenSSL import crypto
from pathlib import Path
import os

def generate_self_signed_cert(
    cert_dir="config/ssl",
    cert_file="cert.pem",
    key_file="key.pem",
    hostname="localhost"
):
    """Generate self-signed SSL certificate"""
    
    # Create certificate directory
    cert_path = Path(cert_dir)
    cert_path.mkdir(parents=True, exist_ok=True)
    
    # Generate key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    
    # Generate certificate
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "YourDaddy AI Assistant"
    cert.get_subject().OU = "Development"
    cert.get_subject().CN = hostname
    
    # Add Subject Alternative Names for multiple domains
    cert.add_extensions([
        crypto.X509Extension(
            b"subjectAltName",
            False,
            f"DNS:{hostname},DNS:127.0.0.1,DNS:localhost,IP:127.0.0.1".encode()
        ),
    ])
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    
    # Write certificate and key
    cert_file_path = cert_path / cert_file
    key_file_path = cert_path / key_file
    
    with open(cert_file_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_file_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    
    # Set permissions (owner read/write only)
    os.chmod(key_file_path, 0o600)
    os.chmod(cert_file_path, 0o644)
    
    print(f"✅ SSL Certificate generated:")
    print(f"   Certificate: {cert_file_path}")
    print(f"   Private Key: {key_file_path}")
    print(f"\n⚠️  This is a SELF-SIGNED certificate for development only!")
    print(f"   For production, use Let's Encrypt or a commercial CA.")
    
    return str(cert_file_path), str(key_file_path)


if __name__ == "__main__":
    generate_self_signed_cert()
