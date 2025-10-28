import os
import json
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass
from tqdm import tqdm

@dataclass
class FileMetadata:
    filename: str
    filesize: int
    chunks: int
    checksum: str
    chunk_size: int = 1024 * 1024  # 1MB chunks
    encrypted: bool = False

class FileHandler:
    def __init__(self, chunk_size: int = 1024 * 1024):
        self.chunk_size = chunk_size
    
    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """Get metadata for file including chunk information"""
        try:
            if not os.path.exists(file_path):
                return None
            
            filesize = os.path.getsize(file_path)
            chunks = (filesize + self.chunk_size - 1) // self.chunk_size
            
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            return FileMetadata(
                filename=os.path.basename(file_path),
                filesize=filesize,
                chunks=chunks,
                checksum=checksum,
                chunk_size=self.chunk_size
            )
        except Exception as e:
            print(f"Error getting file metadata: {e}")
            return None
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def read_chunk(self, file_path: str, chunk_index: int) -> Optional[bytes]:
        """Read specific chunk from file"""
        try:
            with open(file_path, 'rb') as f:
                f.seek(chunk_index * self.chunk_size)
                chunk_data = f.read(self.chunk_size)
                return chunk_data
        except Exception as e:
            print(f"Error reading chunk {chunk_index}: {e}")
            return None
    
    def write_chunk(self, file_path: str, chunk_index: int, data: bytes) -> bool:
        """Write chunk to file at specific position"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'ab' if chunk_index > 0 else 'wb') as f:
                if chunk_index > 0:
                    # Seek to position for writing
                    f.seek(chunk_index * self.chunk_size)
                f.write(data)
                f.flush()
            
            return True
        except Exception as e:
            print(f"Error writing chunk {chunk_index}: {e}")
            return False
    
    def get_missing_chunks(self, file_path: str, total_chunks: int) -> List[int]:
        """Get list of chunks that need to be downloaded"""
        missing_chunks = []
        for i in range(total_chunks):
            # Check if chunk exists and has correct size
            expected_size = min(self.chunk_size, 
                              os.path.getsize(file_path) - i * self.chunk_size) \
                          if os.path.exists(file_path) else self.chunk_size
            
            chunk_path = f"{file_path}.chunk{i}"
            if not os.path.exists(chunk_path) or \
               os.path.getsize(chunk_path) != expected_size:
                missing_chunks.append(i)
        
        return missing_chunks
    
    def reassemble_file(self, temp_dir: str, output_path: str, total_chunks: int) -> bool:
        """Reassemble file from chunks"""
        try:
            with open(output_path, 'wb') as outfile:
                for i in tqdm(range(total_chunks), desc="Reassembling"):
                    chunk_path = os.path.join(temp_dir, f"chunk{i}")
                    if os.path.exists(chunk_path):
                        with open(chunk_path, 'rb') as infile:
                            outfile.write(infile.read())
                        os.remove(chunk_path)  # Clean up chunk
                    else:
                        print(f"Missing chunk {i}")
                        return False
            return True
        except Exception as e:
            print(f"Error reassembling file: {e}")
            return False
