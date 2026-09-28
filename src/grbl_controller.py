"""GRBL Controller - Serial communication with GRBL CNC machines."""

from __future__ import annotations

import re
import threading
import time
from typing import Callable, Optional

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class GRBLController:
    """Handle serial communication with GRBL machine."""
    
    def __init__(self, port: str = "", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.connected = False
        self.is_running = False
        self.status = "Disconnected"
        self.position = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.state = "Idle"
        
        # Callbacks
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_position_change: Optional[Callable[[dict], None]] = None
        self.on_state_change: Optional[Callable[[str], None]] = None
        self.on_line_received: Optional[Callable[[str], None]] = None
    
    @staticmethod
    def list_ports() -> list[str]:
        """List available serial ports."""
        if not HAS_SERIAL:
            return []
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            return sorted(ports)
        except Exception:
            return []
    
    def connect(self) -> bool:
        """Connect to GRBL machine."""
        if not HAS_SERIAL:
            self.status = "Serial library not installed"
            return False
        
        if not self.port:
            self.status = "No port selected"
            return False
        
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for controller reset
            
            # Clear buffer
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # Get initial status
            self.send_command("?")
            
            self.connected = True
            self.status = f"Connected to {self.port}"
            self._call_callback(self.on_status_change, self.status)
            
            return True
        except Exception as e:
            self.status = f"Connection failed: {str(e)}"
            self._call_callback(self.on_status_change, self.status)
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from GRBL machine."""
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        
        self.connected = False
        self.status = "Disconnected"
        self._call_callback(self.on_status_change, self.status)
        return True
    
    def send_command(self, command: str) -> bool:
        """Send command to GRBL."""
        if not self.connected or not self.ser:
            self.status = "Not connected"
            return False
        
        try:
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'
            
            self.ser.write(command.encode())
            self.status = f"Sent: {command.strip()}"
            self._call_callback(self.on_status_change, self.status)
            return True
        except Exception as e:
            self.status = f"Send failed: {str(e)}"
            self._call_callback(self.on_status_change, self.status)
            return False
    
    def send_gcode_file(self, filepath: str) -> bool:
        """Send G-code file to GRBL line by line."""
        if not self.connected or not self.ser:
            self.status = "Not connected"
            return False
        
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            self.is_running = True
            sent = 0
            
            for line_num, line in enumerate(lines, 1):
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Send command
                if not self.send_command(line):
                    break
                
                # Wait for response
                response = self._read_response()
                if response:
                    self._call_callback(self.on_line_received, response)
                
                sent += 1
                self.status = f"Sent {sent}/{len([l for l in lines if l.strip() and not l.strip().startswith(';')])}"
                self._call_callback(self.on_status_change, self.status)
            
            self.is_running = False
            self.status = "G-code complete"
            self._call_callback(self.on_status_change, self.status)
            return True
        except Exception as e:
            self.is_running = False
            self.status = f"G-code error: {str(e)}"
            self._call_callback(self.on_status_change, self.status)
            return False
    
    def emergency_stop(self) -> bool:
        """Emergency stop (Ctrl+X)."""
        if self.connected:
            self.send_command("\x18")  # Ctrl+X
            self.is_running = False
            self.status = "Emergency stop"
            self._call_callback(self.on_status_change, self.status)
            return True
        return False
    
    def reset(self) -> bool:
        """Reset GRBL (Ctrl+Z)."""
        if self.connected:
            self.send_command("\x19")  # Ctrl+Z
            time.sleep(0.5)
            self.send_command("?")
            return True
        return False
    
    def unlock(self) -> bool:
        """Unlock GRBL ($X)."""
        return self.send_command("$X")
    
    def home(self) -> bool:
        """Home GRBL ($H)."""
        return self.send_command("$H")
    
    def get_status(self) -> bool:
        """Request status."""
        return self.send_command("?")
    
    def _read_response(self) -> Optional[str]:
        """Read response from GRBL."""
        if not self.ser:
            return None
        
        try:
            if self.ser.in_waiting > 0:
                response = self.ser.readline().decode().strip()
                self._parse_response(response)
                return response
        except Exception:
            pass
        return None
    
    def _parse_response(self, response: str):
        """Parse GRBL response."""
        # Parse position: <Idle|WPos:10.000,20.000,0.000|FS:0,0>
        if response.startswith('<') and response.endswith('>'):
            # Status response
            parts = response[1:-1].split('|')
            if parts:
                self.state = parts[0]
                self._call_callback(self.on_state_change, self.state)
            
            # Parse position
            for part in parts[1:]:
                if part.startswith('WPos:'):
                    try:
                        coords = part[5:].split(',')
                        self.position = {
                            "X": float(coords[0]) if len(coords) > 0 else 0.0,
                            "Y": float(coords[1]) if len(coords) > 1 else 0.0,
                            "Z": float(coords[2]) if len(coords) > 2 else 0.0,
                        }
                        self._call_callback(self.on_position_change, self.position)
                    except (ValueError, IndexError):
                        pass
    
    def _call_callback(self, callback: Optional[Callable], *args):
        """Call callback safely."""
        if callback:
            try:
                callback(*args)
            except Exception:
                pass
