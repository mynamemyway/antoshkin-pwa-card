"""
Integration tests for concurrent user registration.

Tests race conditions and database locking under concurrent load.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models import User


class TestConcurrentRegistration:
    """Tests for concurrent user registration scenarios."""

    def test_concurrent_sms_requests_same_user(self, client, test_user, db):
        """
        Multiple SMS requests for the same user should not cause race conditions.
        
        Scenario: User clicks "Send SMS" multiple times quickly.
        Expected: All requests succeed, last code is valid.
        """
        results = []
        
        def send_sms_request():
            response = client.post("/api/send-sms", json={
                "phone": test_user.phone
            })
            return response.status_code
        
        # Send 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_sms_request) for _ in range(5)]
            for future in as_completed(futures):
                results.append(future.result())
        
        # All requests should succeed (200 OK)
        assert all(r == 200 for r in results), f"Some requests failed: {results}"
        
        # User should have a valid SMS code
        db.refresh(test_user)
        assert test_user.sms_code is not None
        assert test_user.sms_code_expires_at is not None

    def test_concurrent_registration_different_users(self, client, db, monkeypatch):
        """
        Multiple users registering simultaneously should not cause conflicts.
        
        Scenario: 10 users register at the same time.
        Expected: All users created successfully, no deadlocks.
        """
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        results = []
        phones = [f"+799900000{i:02d}" for i in range(10)]
        
        def register_user(phone):
            response = client.post("/api/register", json={
                "full_name": f"User {phone}",
                "phone": phone
            })
            return response.status_code
        
        # Register 10 users concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_user, phone) for phone in phones]
            for future in as_completed(futures):
                results.append(future.result())
        
        # All registrations should succeed
        assert all(r == 200 for r in results), f"Some registrations failed: {results}"
        
        # All users should exist in database
        for phone in phones:
            user = db.query(User).filter(User.phone == phone).first()
            assert user is not None, f"User {phone} not found in database"

    def test_concurrent_verify_same_user(self, client, test_user, db, monkeypatch):
        """
        Multiple verification attempts for the same user should be handled safely.
        
        Scenario: User clicks "Verify" multiple times quickly.
        Expected: First succeeds (200), others fail gracefully (400 - code cleared).
        No crashes or database corruption.
        """
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        # Set SMS code
        test_user.sms_code = "1234"
        test_user.sms_code_expires_at = None  # No expiration
        db.commit()
        
        # Store phone number (not the user object) to avoid session issues
        phone = test_user.phone
        
        results = []
        
        def verify_code():
            response = client.post("/api/verify", json={
                "phone": phone,
                "code": "1234"
            })
            return response.status_code
        
        # Send 5 concurrent verification requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(verify_code) for _ in range(5)]
            for future in as_completed(futures):
                results.append(future.result())
        
        # At least one should succeed (200), others get 400 (code already used)
        success_count = sum(1 for r in results if r == 200)
        fail_count = sum(1 for r in results if r == 400)
        
        assert success_count >= 1, "At least one verification should succeed"
        assert success_count + fail_count == 5, "All requests should complete (200 or 400)"
        
        # User should be verified
        db.refresh(test_user)
        assert test_user.is_verified is True
        assert test_user.sms_code is None  # Code cleared after verification

    def test_concurrent_login_same_user(self, client, test_user, db, monkeypatch):
        """
        Multiple login requests for the same user should not cause issues.
        
        Scenario: User clicks "Login" multiple times quickly.
        Expected: All requests succeed, last SMS code is valid.
        """
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        results = []
        
        def login_request():
            response = client.post("/api/login", json={
                "phone": test_user.phone
            })
            return response.status_code
        
        # Send 5 concurrent login requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(login_request) for _ in range(5)]
            for future in as_completed(futures):
                results.append(future.result())
        
        # All requests should succeed
        assert all(r == 200 for r in results), f"Some login requests failed: {results}"
        
        # User should have a valid SMS code
        db.refresh(test_user)
        assert test_user.sms_code is not None

    def test_database_write_contention(self, client, db, monkeypatch):
        """
        Test database behavior under concurrent write load.
        
        Scenario: 20 users update their profiles simultaneously.
        Expected: No deadlocks, all updates succeed.
        """
        monkeypatch.setattr('app.services.sms_service.settings.SMS_TEST_MODE', True)
        
        # Create test users
        users = []
        for i in range(20):
            user = User(
                full_name=f"User {i}",
                phone=f"+799900000{i:02d}",
                is_verified=False
            )
            db.add(user)
            users.append(user)
        db.commit()
        
        results = []
        
        def update_user(user_id):
            # Simulate profile update (send SMS = update user record)
            response = client.post("/api/send-sms", json={
                "phone": f"+799900000{user_id:02d}"
            })
            return response.status_code
        
        # Update 20 users concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(update_user, i) for i in range(20)]
            for future in as_completed(futures):
                results.append(future.result())
        
        # All updates should succeed
        assert all(r == 200 for r in results), f"Some updates failed: {results}"
        
        # All users should have SMS codes
        users_with_codes = db.query(User).filter(
            User.sms_code.isnot(None)
        ).count()
        assert users_with_codes == 20, "Not all users have SMS codes"
