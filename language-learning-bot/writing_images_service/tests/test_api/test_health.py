"""
Tests for health API routes.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.health import router

# Create test app
app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestHealthRoutes:
    
    def test_health_check_success(self):
        """Test basic health check success."""
        # Execute
        response = client.get("/health")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "writing_image_service"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "version" in data
    
    @patch('app.api.routes.health.datetime')
    def test_health_check_error(self, mock_datetime):
        """Test health check with error."""
        # Setup
        mock_datetime.now.side_effect = Exception("Test error")
        
        # Execute
        response = client.get("/health")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Test error" in data["error"]
    
    @patch('os.makedirs')
    @patch('os.access')
    def test_detailed_health_check_success(self, mock_access, mock_makedirs):
        """Test detailed health check success."""
        # Setup
        mock_access.return_value = True
        
        # Execute
        response = client.get("/health/detailed")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "system" in data
        assert "configuration" in data
        assert data["components"]["temp_directory"] == "ok"
    
    @patch('os.makedirs', side_effect=Exception("Directory error"))
    def test_detailed_health_check_temp_dir_error(self, mock_makedirs):
        """Test detailed health check with temp directory error."""
        # Execute
        response = client.get("/health/detailed")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"  # Still healthy, just component issue
        assert "error: Directory error" in data["components"]["temp_directory"]
    
    @patch('os.makedirs')
    @patch('builtins.open')
    @patch('os.remove')
    def test_readiness_check_success(self, mock_remove, mock_open, mock_makedirs):
        """Test readiness check success."""
        # Execute
        response = client.get("/health/ready")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["temp_directory"] == "writable"
        assert data["checks"]["image_generation"] == "available"
    
    @patch('os.makedirs', side_effect=Exception("Write error"))
    def test_readiness_check_error(self, mock_makedirs):
        """Test readiness check with error."""
        # Execute
        response = client.get("/health/ready")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_ready"
        assert "Write error" in data["error"]
    
    @patch('os.getpid')
    def test_liveness_check_success(self, mock_getpid):
        """Test liveness check success."""
        # Setup
        mock_getpid.return_value = 12345
        
        # Execute
        response = client.get("/health/live")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["pid"] == 12345
    
    @patch('os.getpid', side_effect=Exception("PID error"))
    def test_liveness_check_error(self, mock_getpid):
        """Test liveness check with error."""
        # Execute
        response = client.get("/health/live")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dead"
        assert "PID error" in data["error"]
        