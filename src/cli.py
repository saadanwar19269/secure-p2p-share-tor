#!/usr/bin/env python3
import click
import os
import sys
from pathlib import Path

from .tor_client import TorClient
from .transfer import P2PTransfer
from .encryption import FileEncryptor
from .file_handler import FileHandler

@click.group()
@click.option('--tor-port', default=9050, help='Tor SOCKS port')
@click.option('--control-port', default=9051, help='Tor control port')
@click.pass_context
def cli(ctx, tor_port, control_port):
    """Secure P2P File Sharing over Tor"""
    ctx.ensure_object(dict)
    ctx.obj['tor_client'] = TorClient(tor_port, control_port)
    ctx.obj['transfer'] = P2PTransfer(ctx.obj['tor_client'])
    ctx.obj['encryptor'] = FileEncryptor()
    ctx.obj['file_handler'] = FileHandler()

@cli.command()
@click.pass_context
def start_tor(ctx):
    """Start Tor service"""
    if ctx.obj['tor_client'].start_tor():
        click.echo("✓ Tor started successfully")
    else:
        click.echo("✗ Failed to start Tor")
        sys.exit(1)

@cli.command()
@click.argument('file_path')
@click.argument('onion_address')
@click.argument('port', type=int)
@click.option('--password', help='Encryption password')
@click.pass_context
def send(ctx, file_path, onion_address, port, password):
    """Send file to onion address"""
    if not os.path.exists(file_path):
        click.echo(f"File not found: {file_path}")
        return
    
    # Ensure Tor is running
    if not ctx.obj['tor_client'].start_tor():
        click.echo("Failed to start Tor")
        return
    
    click.echo(f"Sending {file_path} to {onion_address}:{port}")
    
    if password:
        # Encrypt file before sending
        encrypted_path = f"{file_path}.encrypted"
        if ctx.obj['encryptor'].encrypt_file(file_path, encrypted_path, password):
            file_path = encrypted_path
            click.echo("File encrypted")
        else:
            click.echo("Failed to encrypt file")
            return
    
    if ctx.obj['transfer'].send_file(file_path, onion_address, port, password):
        click.echo("✓ File sent successfully")
    else:
        click.echo("✗ File send failed")

@cli.command()
@click.argument('port', type=int)
@click.option('--download-dir', default='./downloads', help='Download directory')
@click.pass_context
def receive(ctx, port, download_dir):
    """Start receiving files on specified port"""
    # Ensure Tor is running
    if not ctx.obj['tor_client'].start_tor():
        click.echo("Failed to start Tor")
        return
    
    Path(download_dir).mkdir(exist_ok=True)
    
    def on_file_received(file_path, metadata):
        click.echo(f"✓ File received: {file_path}")
        if metadata.get('encrypted'):
            click.echo("File is encrypted. Use 'decrypt' command to decrypt.")
    
    click.echo(f"Listening on port {port}. Press Ctrl+C to stop.")
    try:
        ctx.obj['transfer'].start_receiver(port, download_dir, on_file_received)
    except KeyboardInterrupt:
        click.echo("\nStopped listening")

@cli.command()
@click.argument('file_path')
@click.argument('password')
@click.option('--output', help='Output file path')
@click.pass_context
def decrypt(ctx, file_path, password, output):
    """Decrypt an encrypted file"""
    if not output:
        output = file_path.replace('.encrypted', '')
    
    if ctx.obj['encryptor'].decrypt_file(file_path, output, password):
        click.echo(f"✓ File decrypted: {output}")
        
        # Verify checksum
        checksum = ctx.obj['encryptor'].calculate_checksum(output)
        click.echo(f"File checksum: {checksum}")
    else:
        click.echo("✗ Decryption failed")

@cli.command()
@click.argument('file_path')
@click.pass_context
def checksum(ctx, file_path):
    """Calculate file checksum"""
    if not os.path.exists(file_path):
        click.echo("File not found")
        return
    
    checksum = ctx.obj['encryptor'].calculate_checksum(file_path)
    click.echo(f"SHA-256: {checksum}")

@cli.command()
@click.pass_context
def renew(ctx):
    """Renew Tor connection (get new IP)"""
    if ctx.obj['tor_client'].renew_connection():
        click.echo("✓ Tor connection renewed")
    else:
        click.echo("✗ Failed to renew Tor connection")

if __name__ == '__main__':
    cli()
