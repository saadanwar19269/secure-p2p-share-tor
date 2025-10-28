## Usage Examples

1. Start Tor and listen for files:

p2pshare start-tor

p2pshare receive 9050

2. Send a file:


p2pshare send document.pdf target.onion 9050 --password "secure123"

3. Decrypt received file:

p2pshare decrypt document.pdf.encrypted "secure123"

Key Features

Tor Integration: All traffic routed through Tor for anonymity

End-to-End Encryption: AES-256-CBC encryption with PBKDF2 key derivation

Resume Capability: Chunk-based transfer with resume support

Checksum Verification: SHA-256 integrity checking

Progress Tracking: Real-time transfer progress with tqdm

CLI Interface: User-friendly command-line interface

Security Notes

Tor provides anonymity but consider additional VPN for extra privacy

Use strong passwords for encryption

Verify checksums after transfer

The tool is designed for legitimate file sharing only

This implementation provides a solid foundation for secure P2P file sharing with all the requested features and room for expansion.
