import socket
import json
import time
import threading
from typing import Optional, Callable
from tqdm import tqdm

from .file_handler import FileHandler, FileMetadata
from .tor_client import TorClient

class P2PTransfer:
    def __init__(self, tor_client: TorClient):
        self.tor_client = tor_client
        self.file_handler = FileHandler()
        self.is_listening = False
        self.current_transfers = {}
    
    def send_file(self, file_path: str, target_onion: str, target_port: int, 
                  password: Optional[str] = None) -> bool:
        """Send file to target onion address"""
        try:
            # Get file metadata
            metadata = self.file_handler.get_file_metadata(file_path)
            if not metadata:
                print("Failed to get file metadata")
                return False
            
            # Connect to target
            sock = self.tor_client.create_socket()
            if not sock:
                print("Failed to create Tor socket")
                return False
            
            # Connect through Tor to onion address
            sock.connect((target_onion, target_port))
            
            # Send metadata
            metadata_dict = {
                'filename': metadata.filename,
                'filesize': metadata.filesize,
                'chunks': metadata.chunks,
                'checksum': metadata.checksum,
                'chunk_size': metadata.chunk_size,
                'encrypted': password is not None,
                'action': 'send_file'
            }
            
            sock.send(json.dumps(metadata_dict).encode() + b'\n')
            
            # Wait for acknowledgment
            ack = sock.recv(1024).decode().strip()
            if ack != 'READY':
                print("Receiver not ready")
                sock.close()
                return False
            
            # Send file in chunks with progress bar
            with tqdm(total=metadata.filesize, unit='B', unit_scale=True, 
                     desc=f"Sending {metadata.filename}") as pbar:
                
                for chunk_index in range(metadata.chunks):
                    chunk_data = self.file_handler.read_chunk(file_path, chunk_index)
                    if not chunk_data:
                        print(f"Failed to read chunk {chunk_index}")
                        sock.close()
                        return False
                    
                    # Send chunk index and data
                    chunk_info = {
                        'index': chunk_index,
                        'size': len(chunk_data),
                        'final': chunk_index == metadata.chunks - 1
                    }
                    
                    sock.send(json.dumps(chunk_info).encode() + b'\n')
                    sock.send(chunk_data)
                    
                    # Wait for chunk acknowledgment
                    chunk_ack = sock.recv(1024).decode().strip()
                    if chunk_ack != f'CHUNK_{chunk_index}_OK':
                        print(f"Chunk {chunk_index} failed")
                        sock.close()
                        return False
                    
                    pbar.update(len(chunk_data))
            
            # Verify transfer completion
            sock.send(b'TRANSFER_COMPLETE\n')
            final_ack = sock.recv(1024).decode().strip()
            
            sock.close()
            
            if final_ack == 'SUCCESS':
                print("File transfer completed successfully")
                return True
            else:
                print("File transfer failed")
                return False
                
        except Exception as e:
            print(f"Error sending file: {e}")
            return False
    
    def start_receiver(self, port: int, download_dir: str = "./downloads",
                      on_file_received: Callable = None) -> bool:
        """Start listening for incoming file transfers"""
        try:
            # Create listening socket
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('0.0.0.0', port))
            listener.listen(5)
            
            self.is_listening = True
            print(f"Listening for incoming connections on port {port}...")
            
            while self.is_listening:
                try:
                    client_sock, addr = listener.accept()
                    print(f"Connection from {addr}")
                    
                    # Handle client in separate thread
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_sock, download_dir, on_file_received)
                    )
                    thread.daemon = True
                    thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {e}")
            
            listener.close()
            return True
            
        except Exception as e:
            print(f"Error starting receiver: {e}")
            return False
    
    def _handle_client(self, sock: socket.socket, download_dir: str, 
                      on_file_received: Callable = None):
        """Handle incoming client connection"""
        try:
            # Receive metadata
            metadata_data = b''
            while b'\n' not in metadata_data:
                chunk = sock.recv(1024)
                if not chunk:
                    return
                metadata_data += chunk
            
            metadata = json.loads(metadata_data.decode().strip())
            
            if metadata.get('action') == 'send_file':
                self._receive_file(sock, metadata, download_dir, on_file_received)
            
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            sock.close()
    
    def _receive_file(self, sock: socket.socket, metadata: dict, 
                     download_dir: str, on_file_received: Callable):
        """Receive file from sender"""
        try:
            filename = metadata['filename']
            filesize = metadata['filesize']
            total_chunks = metadata['chunks']
            expected_checksum = metadata['checksum']
            
            output_path = os.path.join(download_dir, filename)
            
            # Send ready signal
            sock.send(b'READY\n')
            
            # Create progress bar
            with tqdm(total=filesize, unit='B', unit_scale=True,
                     desc=f"Receiving {filename}") as pbar:
                
                received_chunks = 0
                while received_chunks < total_chunks:
                    # Receive chunk info
                    chunk_info_data = b''
                    while b'\n' not in chunk_info_data:
                        chunk = sock.recv(1024)
                        if not chunk:
                            break
                        chunk_info_data += chunk
                    
                    if not chunk_info_data:
                        break
                    
                    chunk_info = json.loads(chunk_info_data.decode().strip())
                    chunk_index = chunk_info['index']
                    chunk_size = chunk_info['size']
                    is_final = chunk_info.get('final', False)
                    
                    # Receive chunk data
                    chunk_data = b''
                    while len(chunk_data) < chunk_size:
                        remaining = chunk_size - len(chunk_data)
                        data = sock.recv(min(4096, remaining))
                        if not data:
                            break
                        chunk_data += data
                    
                    # Write chunk
                    if self.file_handler.write_chunk(output_path, chunk_index, chunk_data):
                        sock.send(f'CHUNK_{chunk_index}_OK\n'.encode())
                        received_chunks += 1
                        pbar.update(len(chunk_data))
                    else:
                        sock.send(f'CHUNK_{chunk_index}_FAIL\n'.encode())
                        break
                
                # Check for transfer completion
                completion_data = sock.recv(1024).decode().strip()
                if completion_data == 'TRANSFER_COMPLETE':
                    # Verify file
                    actual_checksum = self.file_handler._calculate_checksum(output_path)
                    if actual_checksum == expected_checksum:
                        sock.send(b'SUCCESS\n')
                        print(f"File received successfully: {output_path}")
                        
                        if on_file_received:
                            on_file_received(output_path, metadata)
                    else:
                        sock.send(b'CHECKSUM_MISMATCH\n')
                        print("File checksum mismatch!")
                else:
                    sock.send(b'TRANSFER_INCOMPLETE\n')
                    
        except Exception as e:
            print(f"Error receiving file: {e}")
