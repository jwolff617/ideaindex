#!/usr/bin/env python3
"""
Backend API Testing for Idea Index Platform
Tests image upload and serving functionality
"""

import requests
import json
import io
from PIL import Image
import os
import sys

# Backend URL from environment
BACKEND_URL = "https://swapideas.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class TestResults:
    def __init__(self):
        self.results = []
        self.auth_token = None
        self.test_user_id = None
        self.test_idea_id = None
        
    def add_result(self, test_name, success, message, details=None):
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        })
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")

def create_test_image(filename="test_image.jpg", format="JPEG"):
    """Create a small test image in memory"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

def test_user_authentication(results):
    """Test user signup and login"""
    print("\n=== Testing User Authentication ===")
    
    # Test signup
    signup_data = {
        "name": "Test User Image",
        "username": f"testuser_img_{os.urandom(4).hex()}",
        "email": f"testimg_{os.urandom(4).hex()}@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{API_BASE}/signup", json=signup_data)
        if response.status_code == 200:
            data = response.json()
            results.auth_token = data.get("token")
            results.test_user_id = data.get("user", {}).get("id")
            results.add_result("User Signup", True, "User created successfully", {"user_id": results.test_user_id})
        else:
            results.add_result("User Signup", False, f"Signup failed: {response.status_code}", {"response": response.text})
            return False
    except Exception as e:
        results.add_result("User Signup", False, f"Signup error: {str(e)}")
        return False
    
    # Auto-verify email for testing
    try:
        headers = {"Authorization": f"Bearer {results.auth_token}"}
        response = requests.post(f"{API_BASE}/verify-email-auto", headers=headers)
        if response.status_code == 200:
            results.add_result("Email Verification", True, "Email auto-verified")
        else:
            results.add_result("Email Verification", False, f"Auto-verify failed: {response.status_code}")
    except Exception as e:
        results.add_result("Email Verification", False, f"Auto-verify error: {str(e)}")
    
    return results.auth_token is not None

def test_create_idea_with_image(results):
    """Test creating an idea with image upload"""
    print("\n=== Testing Create Idea with Image ===")
    
    if not results.auth_token:
        results.add_result("Create Idea with Image", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Create test image
    test_image = create_test_image("test_idea.jpg")
    
    # Prepare multipart form data
    files = {
        'images': ('test_idea.jpg', test_image, 'image/jpeg')
    }
    
    data = {
        'title': 'Test Idea with Image Upload',
        'body': 'This is a test idea to verify image upload functionality works correctly.',
        'tags': 'test,image,upload'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            idea_data = response.json()
            results.test_idea_id = idea_data.get("id")
            attachments = idea_data.get("attachments", [])
            
            if attachments and len(attachments) > 0:
                attachment_path = attachments[0]
                if attachment_path.startswith("/api/uploads/"):
                    results.add_result("Create Idea with Image", True, 
                                     f"Idea created with correct attachment path: {attachment_path}",
                                     {"idea_id": results.test_idea_id, "attachments": attachments})
                    return attachment_path
                else:
                    results.add_result("Create Idea with Image", False, 
                                     f"Attachment path incorrect: {attachment_path} (should start with /api/uploads/)")
            else:
                results.add_result("Create Idea with Image", False, "No attachments found in response")
        else:
            results.add_result("Create Idea with Image", False, 
                             f"Request failed: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("Create Idea with Image", False, f"Error: {str(e)}")
    
    return False

def test_image_serving(results, image_path):
    """Test that uploaded images are accessible via HTTP"""
    print("\n=== Testing Image Serving ===")
    
    if not image_path:
        results.add_result("Image Serving", False, "No image path to test")
        return False
    
    # Construct full image URL
    image_url = f"{BACKEND_URL}{image_path}"
    
    try:
        response = requests.get(image_url)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                results.add_result("Image Serving", True, 
                                 f"Image accessible at {image_url}",
                                 {"content_type": content_type, "size": len(response.content)})
                return True
            else:
                results.add_result("Image Serving", False, 
                                 f"Wrong content type: {content_type}")
        else:
            results.add_result("Image Serving", False, 
                             f"Image not accessible: {response.status_code}")
    except Exception as e:
        results.add_result("Image Serving", False, f"Error accessing image: {str(e)}")
    
    return False

def test_create_comment_with_image(results):
    """Test creating a comment with image upload"""
    print("\n=== Testing Create Comment with Image ===")
    
    if not results.auth_token or not results.test_idea_id:
        results.add_result("Create Comment with Image", False, "Missing auth token or idea ID")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Create test image for comment
    test_image = create_test_image("test_comment.png", "PNG")
    
    files = {
        'images': ('test_comment.png', test_image, 'image/png')
    }
    
    data = {
        'body': 'This is a test comment with an image attachment.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas/{results.test_idea_id}/comments", 
                               headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            comment_data = response.json()
            attachments = comment_data.get("attachments", [])
            
            if attachments and len(attachments) > 0:
                attachment_path = attachments[0]
                if attachment_path.startswith("/api/uploads/"):
                    results.add_result("Create Comment with Image", True, 
                                     f"Comment created with correct attachment: {attachment_path}",
                                     {"comment_id": comment_data.get("id"), "attachments": attachments})
                    return attachment_path
                else:
                    results.add_result("Create Comment with Image", False, 
                                     f"Comment attachment path incorrect: {attachment_path}")
            else:
                results.add_result("Create Comment with Image", False, "No attachments in comment response")
        else:
            results.add_result("Create Comment with Image", False, 
                             f"Comment creation failed: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("Create Comment with Image", False, f"Error: {str(e)}")
    
    return False

def test_migration_endpoint(results):
    """Test the image path migration endpoint"""
    print("\n=== Testing Migration Endpoint ===")
    
    if not results.auth_token:
        results.add_result("Migration Endpoint", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    try:
        response = requests.post(f"{API_BASE}/migrate-image-paths", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", "")
            results.add_result("Migration Endpoint", True, 
                             f"Migration completed: {message}")
            return True
        else:
            results.add_result("Migration Endpoint", False, 
                             f"Migration failed: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("Migration Endpoint", False, f"Migration error: {str(e)}")
    
    return False

def test_retrieve_idea_attachments(results):
    """Test retrieving idea and verifying attachment URLs"""
    print("\n=== Testing Retrieve Idea and Attachments ===")
    
    if not results.test_idea_id:
        results.add_result("Retrieve Idea Attachments", False, "No test idea ID available")
        return False
    
    try:
        response = requests.get(f"{API_BASE}/ideas/{results.test_idea_id}")
        
        if response.status_code == 200:
            idea_data = response.json()
            attachments = idea_data.get("attachments", [])
            
            if attachments:
                all_correct = True
                accessible_count = 0
                
                for attachment in attachments:
                    if not attachment.startswith("/api/uploads/"):
                        all_correct = False
                        results.add_result("Retrieve Idea Attachments", False, 
                                         f"Incorrect attachment path: {attachment}")
                        break
                    
                    # Test if attachment is accessible
                    image_url = f"{BACKEND_URL}{attachment}"
                    try:
                        img_response = requests.get(image_url)
                        if img_response.status_code == 200:
                            accessible_count += 1
                    except:
                        pass
                
                if all_correct:
                    results.add_result("Retrieve Idea Attachments", True, 
                                     f"All {len(attachments)} attachments have correct paths, {accessible_count} accessible",
                                     {"attachments": attachments})
                    return True
            else:
                results.add_result("Retrieve Idea Attachments", False, "No attachments found in retrieved idea")
        else:
            results.add_result("Retrieve Idea Attachments", False, 
                             f"Failed to retrieve idea: {response.status_code}")
    except Exception as e:
        results.add_result("Retrieve Idea Attachments", False, f"Error: {str(e)}")
    
    return False

def test_multiple_image_formats(results):
    """Test uploading different image formats"""
    print("\n=== Testing Multiple Image Formats ===")
    
    if not results.auth_token:
        results.add_result("Multiple Image Formats", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    formats = [
        ("test.jpg", "JPEG", "image/jpeg"),
        ("test.png", "PNG", "image/png")
    ]
    
    success_count = 0
    
    for filename, format_type, mime_type in formats:
        test_image = create_test_image(filename, format_type)
        
        files = {
            'images': (filename, test_image, mime_type)
        }
        
        data = {
            'title': f'Test {format_type} Image Upload',
            'body': f'Testing {format_type} format image upload.'
        }
        
        try:
            response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
            
            if response.status_code == 200:
                idea_data = response.json()
                attachments = idea_data.get("attachments", [])
                
                if attachments and attachments[0].startswith("/api/uploads/"):
                    success_count += 1
                    results.add_result(f"Upload {format_type} Image", True, 
                                     f"{format_type} image uploaded successfully")
                else:
                    results.add_result(f"Upload {format_type} Image", False, 
                                     f"{format_type} image upload failed - no valid attachment")
            else:
                results.add_result(f"Upload {format_type} Image", False, 
                                 f"{format_type} upload failed: {response.status_code}")
        except Exception as e:
            results.add_result(f"Upload {format_type} Image", False, 
                             f"{format_type} upload error: {str(e)}")
    
    overall_success = success_count == len(formats)
    results.add_result("Multiple Image Formats", overall_success, 
                     f"{success_count}/{len(formats)} formats uploaded successfully")
    
    return overall_success

def main():
    """Run all image upload and serving tests"""
    print("🧪 Starting Backend Image Upload and Serving Tests")
    print(f"Backend URL: {BACKEND_URL}")
    
    results = TestResults()
    
    # Test sequence
    auth_success = test_user_authentication(results)
    
    if auth_success:
        image_path = test_create_idea_with_image(results)
        
        if image_path:
            test_image_serving(results, image_path)
        
        comment_image_path = test_create_comment_with_image(results)
        if comment_image_path:
            test_image_serving(results, comment_image_path)
        
        test_migration_endpoint(results)
        test_retrieve_idea_attachments(results)
        test_multiple_image_formats(results)
    
    # Print summary
    print("\n" + "="*60)
    print("🏁 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results.results if r["success"])
    total = len(results.results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Show failed tests
    failed_tests = [r for r in results.results if not r["success"]]
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['test']}: {test['message']}")
    
    # Return results for programmatic use
    return results

if __name__ == "__main__":
    results = main()
    
    # Exit with error code if any tests failed
    failed_count = sum(1 for r in results.results if not r["success"])
    sys.exit(failed_count)