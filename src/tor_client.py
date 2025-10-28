import socket
import subprocess
import time
import logging
from stem import Signal
from stem.control import Controller
from typing import Optional, Tuple

class TorClient:
    def __init__(self, tor_port: int = 9050, control_port: int = 9051):
        self.tor_port = tor_port
        self.control_port = control_port
        self.controller: Optional[Controller] = None
        self.logger = logging.getLogger(__name__)
    
    def start_tor(self) -> bool:
        """Start Tor process if not running"""
        try:
            # Check if Tor is already running
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', self.tor_port))
            sock.close()
            
            if result == 0:
                self.logger.info("Tor is already running")
                return True
            
            # Try to start Tor
            self.logger.info("Starting Tor...")
            process = subprocess.Popen([
                'tor', '--SocksPort', str(self.tor_port),
                '--ControlPort', str(self.control_port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for Tor to start
            for _ in range(30):
                time.sleep(1)
                if self._check_tor_running():
                    self.logger.info("Tor started successfully")
                    return True
            
            self.logger.error("Failed to start Tor")
            return False
            
        except Exception as e:
            self.logger.error(f"Error starting Tor: {e}")
            return False
    
    def _check_tor_running(self) -> bool:
        """Check if Tor is running and ready"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', self.tor_port))
            sock.close()
            return result == 0
        except:
            return False
    
    def connect_controller(self, password: str = None) -> bool:
        """Connect to Tor control port"""
        try:
            self.controller = Controller.from_port(port=self.control_port)
            if password:
                self.controller.authenticate(password=password)
            else:
                self.controller.authenticate()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Tor controller: {e}")
            return False
    
    def renew_connection(self) -> bool:
        """Renew Tor circuit (get new IP)"""
        if not self.controller:
            return False
        
        try:
            self.controller.signal(Signal.NEWNYM)
            time.sleep(5)  # Wait for circuit to rebuild
            return True
        except Exception as e:
            self.logger.error(f"Failed to renew Tor connection: {e}")
            return False
    
    def create_socket(self) -> Optional[socket.socket]:
        """Create a socket that routes through Tor"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(('127.0.0.1', self.tor_port))
            return sock
        except Exception as e:
            self.logger.error(f"Failed to create Tor socket: {e}")
            return None
