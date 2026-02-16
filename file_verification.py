#!/usr/bin/env python3
"""
File Verification Module for Windows LAN File Share
Provides checksum verification and resume download capabilities
"""

import os
import hashlib
import json
from pathlib import Path

class FileVerifier:
    """Handle file integrity verification using checksums"""
    
    @staticmethod
    def calculate_checksum(file_path, algorithm='sha256', chunk_size=8192):
        """
        Calculate checksum for a file
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (sha256, md5, sha1)
            chunk_size: Size of chunks to read
            
        Returns:
            Hexadecimal checksum string
        """
        if algorithm == 'sha256':
            hasher = hashlib.sha256()
        elif algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha1':
            hasher = hashlib.sha1()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            raise Exception(f"Failed to calculate checksum: {str(e)}")
    
    @staticmethod
    def verify_file(file_path, expected_checksum, algorithm='sha256'):
        """
        Verify file integrity against expected checksum
        
        Args:
            file_path: Path to the file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm used
            
        Returns:
            Tuple of (is_valid, actual_checksum)
        """
        try:
            actual_checksum = FileVerifier.calculate_checksum(file_path, algorithm)
            is_valid = actual_checksum.lower() == expected_checksum.lower()
            return is_valid, actual_checksum
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def calculate_partial_checksum(file_path, start_byte, end_byte, algorithm='sha256'):
        """
        Calculate checksum for a portion of a file
        
        Args:
            file_path: Path to the file
            start_byte: Starting byte position
            end_byte: Ending byte position
            algorithm: Hash algorithm
            
        Returns:
            Hexadecimal checksum string
        """
        if algorithm == 'sha256':
            hasher = hashlib.sha256()
        elif algorithm == 'md5':
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha1()
        
        try:
            with open(file_path, 'rb') as f:
                f.seek(start_byte)
                remaining = end_byte - start_byte
                chunk_size = 8192
                
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    remaining -= len(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            raise Exception(f"Failed to calculate partial checksum: {str(e)}")

class ResumeManager:
    """Manage resume information for interrupted downloads"""
    
    def __init__(self, resume_dir=None):
        if resume_dir is None:
            resume_dir = os.path.join(os.path.expanduser("~"), ".lan_file_share", "resume")
        
        self.resume_dir = resume_dir
        os.makedirs(self.resume_dir, exist_ok=True)
    
    def save_resume_info(self, download_id, info):
        """
        Save resume information for a download
        
        Args:
            download_id: Unique identifier for the download
            info: Dictionary containing resume information
        """
        resume_file = os.path.join(self.resume_dir, f"{download_id}.json")
        
        try:
            with open(resume_file, 'w') as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            print(f"Failed to save resume info: {e}")
    
    def load_resume_info(self, download_id):
        """
        Load resume information for a download
        
        Args:
            download_id: Unique identifier for the download
            
        Returns:
            Resume information dictionary or None
        """
        resume_file = os.path.join(self.resume_dir, f"{download_id}.json")
        
        if not os.path.exists(resume_file):
            return None
        
        try:
            with open(resume_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load resume info: {e}")
            return None
    
    def delete_resume_info(self, download_id):
        """
        Delete resume information after successful download
        
        Args:
            download_id: Unique identifier for the download
        """
        resume_file = os.path.join(self.resume_dir, f"{download_id}.json")
        
        try:
            if os.path.exists(resume_file):
                os.remove(resume_file)
        except Exception as e:
            print(f"Failed to delete resume info: {e}")
    
    def get_partial_file_size(self, file_path):
        """
        Get size of partially downloaded file
        
        Args:
            file_path: Path to the partial file
            
        Returns:
            File size in bytes or 0 if file doesn't exist
        """
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
    
    def can_resume(self, download_id, file_path, total_size):
        """
        Check if a download can be resumed
        
        Args:
            download_id: Unique identifier for the download
            file_path: Path to the partial file
            total_size: Total expected file size
            
        Returns:
            Tuple of (can_resume, bytes_downloaded)
        """
        resume_info = self.load_resume_info(download_id)
        
        if resume_info is None:
            return False, 0
        
        partial_size = self.get_partial_file_size(file_path)
        
        # Verify resume info matches
        if (resume_info.get('total_size') == total_size and 
            resume_info.get('downloaded') == partial_size and
            partial_size > 0 and partial_size < total_size):
            return True, partial_size
        
        return False, 0

class ChunkVerifier:
    """Verify individual chunks in multi-threaded downloads"""
    
    @staticmethod
    def verify_chunk(chunk_file, expected_size, expected_checksum=None):
        """
        Verify a downloaded chunk
        
        Args:
            chunk_file: Path to chunk file
            expected_size: Expected chunk size
            expected_checksum: Optional checksum to verify
            
        Returns:
            Tuple of (is_valid, actual_size, actual_checksum)
        """
        if not os.path.exists(chunk_file):
            return False, 0, None
        
        actual_size = os.path.getsize(chunk_file)
        
        # Size verification
        if actual_size != expected_size:
            return False, actual_size, None
        
        # Checksum verification (if provided)
        if expected_checksum:
            try:
                actual_checksum = FileVerifier.calculate_checksum(chunk_file, 'md5')
                if actual_checksum.lower() != expected_checksum.lower():
                    return False, actual_size, actual_checksum
            except Exception:
                return False, actual_size, None
        
        return True, actual_size, None
    
    @staticmethod
    def merge_and_verify_chunks(chunk_files, output_file, expected_total_size, expected_checksum=None):
        """
        Merge chunks and verify the result
        
        Args:
            chunk_files: List of chunk file paths in order
            output_file: Path for merged output file
            expected_total_size: Expected total file size
            expected_checksum: Optional checksum for verification
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Merge chunks
            total_written = 0
            with open(output_file, 'wb') as output:
                for chunk_file in chunk_files:
                    if not os.path.exists(chunk_file):
                        return False, f"Chunk file missing: {chunk_file}"
                    
                    with open(chunk_file, 'rb') as chunk:
                        data = chunk.read()
                        output.write(data)
                        total_written += len(data)
            
            # Verify size
            if total_written != expected_total_size:
                return False, f"Size mismatch: expected {expected_total_size}, got {total_written}"
            
            # Verify checksum if provided
            if expected_checksum:
                actual_checksum = FileVerifier.calculate_checksum(output_file, 'sha256')
                if actual_checksum.lower() != expected_checksum.lower():
                    return False, f"Checksum mismatch: file may be corrupted"
            
            return True, None
            
        except Exception as e:
            return False, f"Merge failed: {str(e)}"

def generate_file_metadata(file_path):
    """
    Generate metadata for a file including checksums
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file metadata
    """
    try:
        file_size = os.path.getsize(file_path)
        
        metadata = {
            'path': file_path,
            'size': file_size,
            'sha256': FileVerifier.calculate_checksum(file_path, 'sha256'),
            'md5': FileVerifier.calculate_checksum(file_path, 'md5'),
            'modified': os.path.getmtime(file_path)
        }
        
        return metadata
    except Exception as e:
        return {'error': str(e)}

def verify_download(downloaded_file, expected_size, expected_checksum=None, algorithm='sha256'):
    """
    Verify a completed download
    
    Args:
        downloaded_file: Path to downloaded file
        expected_size: Expected file size
        expected_checksum: Expected checksum (optional)
        algorithm: Hash algorithm to use
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check if file exists
    if not os.path.exists(downloaded_file):
        return False, "File does not exist"
    
    # Verify size
    actual_size = os.path.getsize(downloaded_file)
    if actual_size != expected_size:
        return False, f"Size mismatch: expected {expected_size}, got {actual_size}"
    
    # Verify checksum if provided
    if expected_checksum:
        is_valid, actual_checksum = FileVerifier.verify_file(
            downloaded_file, 
            expected_checksum, 
            algorithm
        )
        
        if not is_valid:
            return False, f"Checksum verification failed"
    
    return True, "File verified successfully"
