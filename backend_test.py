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
BACKEND_URL = "https://brainstorm-hub-215.preview.emergentagent.com"
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
    
    # Prepare multipart form data - need to pass all data as form fields
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

def test_edge_cases(results):
    """Test edge cases that might cause 'Failed to post idea' error"""
    print("\n=== Testing Edge Cases ===")
    
    if not results.auth_token:
        results.add_result("Edge Cases", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Test 1: Body text less than 10 characters (should fail)
    print("\n--- Testing short body text ---")
    test_image = create_test_image("test_short.jpg")
    files = {'images': ('test_short.jpg', test_image, 'image/jpeg')}
    data = {
        'title': 'Short Body Test',
        'body': 'Short'  # Less than 10 characters
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        if response.status_code == 400:
            results.add_result("Short Body Validation", True, "Correctly rejected short body text")
        else:
            results.add_result("Short Body Validation", False, 
                             f"Should have rejected short body, got: {response.status_code}")
    except Exception as e:
        results.add_result("Short Body Validation", False, f"Error: {str(e)}")
    
    # Test 2: No authentication token (should fail)
    print("\n--- Testing no auth token ---")
    test_image = create_test_image("test_noauth.jpg")
    files = {'images': ('test_noauth.jpg', test_image, 'image/jpeg')}
    data = {
        'title': 'No Auth Test',
        'body': 'This should fail due to no authentication token provided.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", files=files, data=data)  # No headers
        if response.status_code == 401 or response.status_code == 403:
            results.add_result("No Auth Token", True, "Correctly rejected request without auth")
        else:
            results.add_result("No Auth Token", False, 
                             f"Should have rejected no auth, got: {response.status_code}")
    except Exception as e:
        results.add_result("No Auth Token", False, f"Error: {str(e)}")
    
    # Test 3: Image upload without body text
    print("\n--- Testing image without body ---")
    test_image = create_test_image("test_nobody.jpg")
    files = {'images': ('test_nobody.jpg', test_image, 'image/jpeg')}
    data = {
        'title': 'Image Only Test'
        # No body field
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        if response.status_code == 400:
            results.add_result("Image Without Body", True, "Correctly rejected missing body")
        else:
            results.add_result("Image Without Body", False, 
                             f"Should have rejected missing body, got: {response.status_code}")
    except Exception as e:
        results.add_result("Image Without Body", False, f"Error: {str(e)}")
    
    # Test 4: Large image file (create 5MB image)
    print("\n--- Testing large image file ---")
    try:
        large_img = Image.new('RGB', (2000, 2000), color='blue')
        large_img_bytes = io.BytesIO()
        large_img.save(large_img_bytes, format='JPEG', quality=95)
        large_img_bytes.seek(0)
        
        files = {'images': ('large_test.jpg', large_img_bytes, 'image/jpeg')}
        data = {
            'title': 'Large Image Test',
            'body': 'Testing upload of a large image file to see if it causes issues.'
        }
        
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data, timeout=30)
        if response.status_code == 200:
            results.add_result("Large Image Upload", True, "Large image uploaded successfully")
        else:
            results.add_result("Large Image Upload", False, 
                             f"Large image upload failed: {response.status_code}", 
                             {"response": response.text[:500]})
    except Exception as e:
        results.add_result("Large Image Upload", False, f"Large image error: {str(e)}")

def test_specific_user_scenario(results):
    """Test the exact scenario described in the review request"""
    print("\n=== Testing Specific User Scenario ===")
    
    if not results.auth_token:
        results.add_result("User Scenario Test", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Create the exact test case from the review request
    test_image = create_test_image("user_test_image.jpg")
    files = {'images': ('user_test_image.jpg', test_image, 'image/jpeg')}
    
    data = {
        'title': 'New Test Image Post',
        'body': 'This is a test post with an image attachment to verify upload functionality is working correctly'
    }
    
    try:
        print(f"Making request to: {API_BASE}/ideas")
        print(f"Headers: Authorization: Bearer {results.auth_token[:20]}...")
        print(f"Data: {data}")
        print(f"Files: {list(files.keys())}")
        
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            idea_data = response.json()
            results.add_result("User Scenario Test", True, 
                             "Successfully created idea matching user scenario",
                             {"idea_id": idea_data.get("id"), "attachments": idea_data.get("attachments")})
            
            # Verify the image is accessible
            attachments = idea_data.get("attachments", [])
            if attachments:
                image_url = f"{BACKEND_URL}{attachments[0]}"
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    results.add_result("User Scenario Image Access", True, 
                                     f"Image accessible at {image_url}")
                else:
                    results.add_result("User Scenario Image Access", False, 
                                     f"Image not accessible: {img_response.status_code}")
        else:
            error_text = response.text
            results.add_result("User Scenario Test", False, 
                             f"Failed to post idea: {response.status_code}",
                             {"response": error_text, "headers": dict(response.headers)})
            
            # This is the exact error the user is experiencing
            print(f"❌ REPRODUCING USER ERROR: {response.status_code}")
            print(f"Response body: {error_text}")
            
    except Exception as e:
        results.add_result("User Scenario Test", False, f"Request error: {str(e)}")

def test_form_data_parsing(results):
    """Test different ways of sending form data to identify parsing issues"""
    print("\n=== Testing Form Data Parsing ===")
    
    if not results.auth_token:
        results.add_result("Form Data Parsing", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Test 1: Using requests.post with files and data (current method)
    print("\n--- Testing files + data method ---")
    test_image = create_test_image("form_test1.jpg")
    files = {'images': ('form_test1.jpg', test_image, 'image/jpeg')}
    data = {
        'title': 'Form Test 1',
        'body': 'Testing form data parsing with files and data parameters.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        if response.status_code == 200:
            results.add_result("Files + Data Method", True, "Form parsing successful")
        else:
            results.add_result("Files + Data Method", False, 
                             f"Form parsing failed: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("Files + Data Method", False, f"Error: {str(e)}")
    
    # Test 2: Check if missing title causes issues
    print("\n--- Testing missing title ---")
    test_image = create_test_image("form_test2.jpg")
    files = {'images': ('form_test2.jpg', test_image, 'image/jpeg')}
    data = {
        # 'title': 'Missing Title Test',  # Intentionally missing
        'body': 'Testing what happens when title is missing from form data.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        if response.status_code == 400:
            results.add_result("Missing Title Validation", True, "Correctly rejected missing title")
        else:
            results.add_result("Missing Title Validation", False, 
                             f"Should reject missing title, got: {response.status_code}")
    except Exception as e:
        results.add_result("Missing Title Validation", False, f"Error: {str(e)}")

def test_frontend_integration_scenarios(results):
    """Test scenarios that might cause frontend 'Failed to post idea' errors"""
    print("\n=== Testing Frontend Integration Scenarios ===")
    
    if not results.auth_token:
        results.add_result("Frontend Integration", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Test 1: Empty file upload (common frontend issue)
    print("\n--- Testing empty file upload ---")
    files = {'images': ('', io.BytesIO(b''), 'image/jpeg')}  # Empty file
    data = {
        'title': 'Empty File Test',
        'body': 'Testing what happens with empty file upload from frontend.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        if response.status_code == 200:
            results.add_result("Empty File Upload", True, "Empty file handled gracefully")
        else:
            results.add_result("Empty File Upload", False, 
                             f"Empty file caused error: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("Empty File Upload", False, f"Error: {str(e)}")
    
    # Test 2: Invalid file type
    print("\n--- Testing invalid file type ---")
    invalid_file = io.BytesIO(b'This is not an image file')
    files = {'images': ('test.txt', invalid_file, 'text/plain')}
    data = {
        'title': 'Invalid File Type Test',
        'body': 'Testing upload of non-image file to see backend response.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        results.add_result("Invalid File Type", True, 
                         f"Invalid file handled with status: {response.status_code}")
    except Exception as e:
        results.add_result("Invalid File Type", False, f"Error: {str(e)}")
    
    # Test 3: Multiple images (test array handling)
    print("\n--- Testing multiple images ---")
    image1 = create_test_image("multi1.jpg")
    image2 = create_test_image("multi2.png", "PNG")
    
    files = [
        ('images', ('multi1.jpg', image1, 'image/jpeg')),
        ('images', ('multi2.png', image2, 'image/png'))
    ]
    data = {
        'title': 'Multiple Images Test',
        'body': 'Testing upload of multiple images to verify array handling.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
        if response.status_code == 200:
            idea_data = response.json()
            attachments = idea_data.get("attachments", [])
            results.add_result("Multiple Images Upload", True, 
                             f"Multiple images uploaded: {len(attachments)} attachments")
        else:
            results.add_result("Multiple Images Upload", False, 
                             f"Multiple images failed: {response.status_code}")
    except Exception as e:
        results.add_result("Multiple Images Upload", False, f"Error: {str(e)}")
    
    # Test 4: Malformed Authorization header
    print("\n--- Testing malformed auth header ---")
    bad_headers = {"Authorization": "Bearer invalid_token_format"}
    test_image = create_test_image("auth_test.jpg")
    files = {'images': ('auth_test.jpg', test_image, 'image/jpeg')}
    data = {
        'title': 'Auth Test',
        'body': 'Testing with malformed authorization header.'
    }
    
    try:
        response = requests.post(f"{API_BASE}/ideas", headers=bad_headers, files=files, data=data)
        if response.status_code == 401:
            results.add_result("Malformed Auth Header", True, "Correctly rejected invalid token")
        else:
            results.add_result("Malformed Auth Header", False, 
                             f"Should reject invalid token, got: {response.status_code}")
    except Exception as e:
        results.add_result("Malformed Auth Header", False, f"Error: {str(e)}")

def test_cors_and_headers(results):
    """Test CORS and header-related issues that might affect frontend"""
    print("\n=== Testing CORS and Headers ===")
    
    # Test 1: OPTIONS preflight request
    print("\n--- Testing OPTIONS preflight ---")
    try:
        response = requests.options(f"{API_BASE}/ideas")
        results.add_result("OPTIONS Preflight", True, 
                         f"OPTIONS request handled: {response.status_code}")
    except Exception as e:
        results.add_result("OPTIONS Preflight", False, f"OPTIONS error: {str(e)}")
    
    # Test 2: Check CORS headers
    print("\n--- Testing CORS headers ---")
    try:
        response = requests.get(f"{API_BASE}/ideas")
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        results.add_result("CORS Headers", True, 
                         f"CORS headers present: {cors_headers}")
    except Exception as e:
        results.add_result("CORS Headers", False, f"CORS check error: {str(e)}")

def create_test_profile_image(width=800, height=600, format="JPEG", color='blue'):
    """Create a test image for profile picture testing with specific dimensions"""
    img = Image.new('RGB', (width, height), color=color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

def create_png_with_transparency():
    """Create a PNG image with transparency for testing RGBA to RGB conversion"""
    img = Image.new('RGBA', (300, 300), (255, 0, 0, 0))  # Transparent red
    # Add some opaque content
    for x in range(100, 200):
        for y in range(100, 200):
            img.putpixel((x, y), (0, 255, 0, 255))  # Opaque green square
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_profile_picture_authentication(results):
    """Test profile picture upload authentication requirements"""
    print("\n=== Testing Profile Picture Authentication ===")
    
    # Test 1: Upload without authentication (should fail with 401)
    test_image = create_test_profile_image()
    files = {'image': ('profile_test.jpg', test_image, 'image/jpeg')}
    
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", files=files)
        if response.status_code == 401:
            results.add_result("Profile Upload No Auth", True, "Correctly rejected request without authentication")
        else:
            results.add_result("Profile Upload No Auth", False, 
                             f"Should reject no auth, got: {response.status_code}")
    except Exception as e:
        results.add_result("Profile Upload No Auth", False, f"Error: {str(e)}")
    
    # Test 2: Upload with invalid token (should fail with 401)
    invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
    test_image = create_test_profile_image()
    files = {'image': ('profile_test.jpg', test_image, 'image/jpeg')}
    
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=invalid_headers, files=files)
        if response.status_code == 401:
            results.add_result("Profile Upload Invalid Token", True, "Correctly rejected invalid token")
        else:
            results.add_result("Profile Upload Invalid Token", False, 
                             f"Should reject invalid token, got: {response.status_code}")
    except Exception as e:
        results.add_result("Profile Upload Invalid Token", False, f"Error: {str(e)}")

def test_profile_picture_upload_success(results):
    """Test successful profile picture upload cases"""
    print("\n=== Testing Profile Picture Upload Success Cases ===")
    
    if not results.auth_token:
        results.add_result("Profile Picture Upload", False, "No auth token available")
        return None
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Test 1: Upload JPEG image
    print("\n--- Testing JPEG upload ---")
    test_image = create_test_profile_image(600, 800, "JPEG", 'red')  # Portrait orientation
    files = {'image': ('profile_test.jpg', test_image, 'image/jpeg')}
    
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
        
        if response.status_code == 200:
            data = response.json()
            avatar_url = data.get('avatar_url')
            
            if avatar_url and avatar_url.startswith('/api/uploads/profile_'):
                results.add_result("Profile JPEG Upload", True, 
                                 f"JPEG profile picture uploaded successfully: {avatar_url}")
                
                # Test if image is accessible
                image_full_url = f"{BACKEND_URL}{avatar_url}"
                img_response = requests.get(image_full_url)
                if img_response.status_code == 200:
                    results.add_result("Profile JPEG Serving", True, 
                                     f"Profile image accessible at {image_full_url}")
                    return avatar_url
                else:
                    results.add_result("Profile JPEG Serving", False, 
                                     f"Profile image not accessible: {img_response.status_code}")
            else:
                results.add_result("Profile JPEG Upload", False, 
                                 f"Invalid avatar_url format: {avatar_url}")
        else:
            results.add_result("Profile JPEG Upload", False, 
                             f"JPEG upload failed: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("Profile JPEG Upload", False, f"Error: {str(e)}")
    
    return None

def test_profile_picture_png_transparency(results):
    """Test PNG with transparency handling (RGBA to RGB conversion)"""
    print("\n=== Testing PNG Transparency Handling ===")
    
    if not results.auth_token:
        results.add_result("PNG Transparency", False, "No auth token available")
        return None
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Create PNG with transparency
    png_image = create_png_with_transparency()
    files = {'image': ('profile_transparent.png', png_image, 'image/png')}
    
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
        
        if response.status_code == 200:
            data = response.json()
            avatar_url = data.get('avatar_url')
            
            if avatar_url and avatar_url.endswith('.jpg'):  # Should be converted to JPEG
                results.add_result("PNG Transparency Conversion", True, 
                                 f"PNG with transparency converted to JPEG: {avatar_url}")
                
                # Verify the image is accessible and properly converted
                image_full_url = f"{BACKEND_URL}{avatar_url}"
                img_response = requests.get(image_full_url)
                if img_response.status_code == 200:
                    content_type = img_response.headers.get('content-type', '')
                    if 'jpeg' in content_type.lower():
                        results.add_result("PNG to JPEG Conversion", True, 
                                         f"PNG properly converted to JPEG format")
                    else:
                        results.add_result("PNG to JPEG Conversion", False, 
                                         f"Wrong content type: {content_type}")
                    return avatar_url
                else:
                    results.add_result("PNG Transparency Serving", False, 
                                     f"Converted image not accessible: {img_response.status_code}")
            else:
                results.add_result("PNG Transparency Conversion", False, 
                                 f"PNG not converted to JPEG: {avatar_url}")
        else:
            results.add_result("PNG Transparency Conversion", False, 
                             f"PNG upload failed: {response.status_code}", {"response": response.text})
    except Exception as e:
        results.add_result("PNG Transparency Conversion", False, f"Error: {str(e)}")
    
    return None

def test_profile_picture_aspect_ratios(results):
    """Test different aspect ratios to verify center crop functionality"""
    print("\n=== Testing Profile Picture Aspect Ratios ===")
    
    if not results.auth_token:
        results.add_result("Aspect Ratio Tests", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    test_cases = [
        ("landscape", 1200, 600, "Landscape image (2:1 ratio)"),
        ("portrait", 400, 800, "Portrait image (1:2 ratio)"),
        ("square", 500, 500, "Square image (1:1 ratio)"),
        ("wide", 1600, 400, "Very wide image (4:1 ratio)")
    ]
    
    success_count = 0
    
    for name, width, height, description in test_cases:
        test_image = create_test_profile_image(width, height, "JPEG", 'purple')
        files = {'image': (f'profile_{name}.jpg', test_image, 'image/jpeg')}
        
        try:
            response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
            
            if response.status_code == 200:
                data = response.json()
                avatar_url = data.get('avatar_url')
                
                if avatar_url:
                    # Verify the processed image is accessible
                    image_full_url = f"{BACKEND_URL}{avatar_url}"
                    img_response = requests.get(image_full_url)
                    
                    if img_response.status_code == 200:
                        success_count += 1
                        results.add_result(f"Aspect Ratio {name.title()}", True, 
                                         f"{description} processed successfully")
                    else:
                        results.add_result(f"Aspect Ratio {name.title()}", False, 
                                         f"{description} not accessible after processing")
                else:
                    results.add_result(f"Aspect Ratio {name.title()}", False, 
                                     f"{description} upload returned no avatar_url")
            else:
                results.add_result(f"Aspect Ratio {name.title()}", False, 
                                 f"{description} upload failed: {response.status_code}")
        except Exception as e:
            results.add_result(f"Aspect Ratio {name.title()}", False, f"{description} error: {str(e)}")
    
    overall_success = success_count == len(test_cases)
    results.add_result("All Aspect Ratios", overall_success, 
                     f"{success_count}/{len(test_cases)} aspect ratios processed successfully")

def test_profile_picture_validation(results):
    """Test file validation and error cases"""
    print("\n=== Testing Profile Picture Validation ===")
    
    if not results.auth_token:
        results.add_result("Profile Validation", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Test 1: Non-image file (should fail with 400)
    print("\n--- Testing non-image file ---")
    text_file = io.BytesIO(b'This is not an image file, it is plain text.')
    files = {'image': ('not_image.txt', text_file, 'text/plain')}
    
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
        if response.status_code == 400:
            results.add_result("Non-Image File Validation", True, "Correctly rejected non-image file")
        else:
            results.add_result("Non-Image File Validation", False, 
                             f"Should reject non-image, got: {response.status_code}")
    except Exception as e:
        results.add_result("Non-Image File Validation", False, f"Error: {str(e)}")
    
    # Test 2: Corrupted image file
    print("\n--- Testing corrupted image ---")
    corrupted_data = io.BytesIO(b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01corrupted_data_here')
    files = {'image': ('corrupted.jpg', corrupted_data, 'image/jpeg')}
    
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
        if response.status_code in [400, 500]:
            results.add_result("Corrupted Image Validation", True, 
                             f"Correctly handled corrupted image: {response.status_code}")
        else:
            results.add_result("Corrupted Image Validation", False, 
                             f"Unexpected response to corrupted image: {response.status_code}")
    except Exception as e:
        results.add_result("Corrupted Image Validation", False, f"Error: {str(e)}")
    
    # Test 3: Very large file (>10MB)
    print("\n--- Testing large file ---")
    try:
        # Create a large image (approximately 12MB when saved)
        large_img = Image.new('RGB', (4000, 3000), color='yellow')
        large_img_bytes = io.BytesIO()
        large_img.save(large_img_bytes, format='JPEG', quality=95)
        large_img_bytes.seek(0)
        
        files = {'image': ('large_profile.jpg', large_img_bytes, 'image/jpeg')}
        
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files, timeout=30)
        
        if response.status_code == 200:
            results.add_result("Large File Upload", True, "Large file processed successfully")
        elif response.status_code == 413:  # Payload too large
            results.add_result("Large File Validation", True, "Large file correctly rejected")
        else:
            results.add_result("Large File Upload", False, 
                             f"Large file handling unexpected: {response.status_code}")
    except Exception as e:
        results.add_result("Large File Upload", False, f"Large file error: {str(e)}")
    
    # Test 4: Missing image field
    print("\n--- Testing missing image field ---")
    try:
        response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers)  # No files
        if response.status_code == 422:  # Unprocessable Entity (FastAPI validation error)
            results.add_result("Missing Image Field", True, "Correctly rejected missing image field")
        else:
            results.add_result("Missing Image Field", False, 
                             f"Should reject missing image, got: {response.status_code}")
    except Exception as e:
        results.add_result("Missing Image Field", False, f"Error: {str(e)}")

def test_profile_picture_database_update(results):
    """Test that user's avatar_url is updated in database"""
    print("\n=== Testing Database Update ===")
    
    if not results.auth_token:
        results.add_result("Database Update", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # First, get current user info to check avatar_url before upload
    try:
        user_response = requests.get(f"{API_BASE}/me", headers=headers)
        if user_response.status_code != 200:
            results.add_result("Database Update", False, "Could not fetch user info")
            return
        
        user_before = user_response.json()
        avatar_before = user_before.get('avatar_url', '')
        
        # Upload a new profile picture
        test_image = create_test_profile_image(400, 400, "JPEG", 'green')
        files = {'image': ('db_test_profile.jpg', test_image, 'image/jpeg')}
        
        upload_response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
        
        if upload_response.status_code == 200:
            upload_data = upload_response.json()
            new_avatar_url = upload_data.get('avatar_url')
            
            # Fetch user info again to verify database update
            user_response_after = requests.get(f"{API_BASE}/me", headers=headers)
            if user_response_after.status_code == 200:
                user_after = user_response_after.json()
                avatar_after = user_after.get('avatar_url', '')
                
                if avatar_after == new_avatar_url and avatar_after != avatar_before:
                    results.add_result("Database Avatar Update", True, 
                                     f"User avatar_url updated correctly: {new_avatar_url}")
                    
                    # Verify the URL format is correct
                    if new_avatar_url.startswith('/api/uploads/profile_') and new_avatar_url.endswith('.jpg'):
                        results.add_result("Avatar URL Format", True, 
                                         f"Avatar URL format correct: /api/uploads/profile_{{user_id}}_{{uuid}}.jpg")
                    else:
                        results.add_result("Avatar URL Format", False, 
                                         f"Avatar URL format incorrect: {new_avatar_url}")
                else:
                    results.add_result("Database Avatar Update", False, 
                                     f"Avatar URL not updated. Before: {avatar_before}, After: {avatar_after}, Expected: {new_avatar_url}")
            else:
                results.add_result("Database Avatar Update", False, 
                                 "Could not fetch user info after upload")
        else:
            results.add_result("Database Avatar Update", False, 
                             f"Profile upload failed: {upload_response.status_code}")
    except Exception as e:
        results.add_result("Database Avatar Update", False, f"Error: {str(e)}")

def test_existing_user_credentials(results):
    """Test with the specific user credentials mentioned in the review request"""
    print("\n=== Testing with Existing User Credentials ===")
    
    # Try to login with testuser@example.com / password123
    login_data = {
        "email": "testuser@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{API_BASE}/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            existing_token = data.get("token")
            existing_user = data.get("user", {})
            
            results.add_result("Existing User Login", True, 
                             f"Successfully logged in as {existing_user.get('email')}")
            
            # Test profile picture upload with existing user
            if existing_token:
                headers = {"Authorization": f"Bearer {existing_token}"}
                test_image = create_test_profile_image(600, 600, "JPEG", 'orange')
                files = {'image': ('existing_user_profile.jpg', test_image, 'image/jpeg')}
                
                upload_response = requests.post(f"{API_BASE}/upload-profile-picture", headers=headers, files=files)
                
                if upload_response.status_code == 200:
                    upload_data = upload_response.json()
                    avatar_url = upload_data.get('avatar_url')
                    results.add_result("Existing User Profile Upload", True, 
                                     f"Profile picture uploaded for existing user: {avatar_url}")
                    
                    # Verify image is accessible
                    if avatar_url:
                        image_full_url = f"{BACKEND_URL}{avatar_url}"
                        img_response = requests.get(image_full_url)
                        if img_response.status_code == 200:
                            results.add_result("Existing User Image Access", True, 
                                             f"Profile image accessible for existing user")
                        else:
                            results.add_result("Existing User Image Access", False, 
                                             f"Profile image not accessible: {img_response.status_code}")
                else:
                    results.add_result("Existing User Profile Upload", False, 
                                     f"Profile upload failed for existing user: {upload_response.status_code}")
        else:
            results.add_result("Existing User Login", False, 
                             f"Could not login with testuser@example.com: {response.status_code}")
    except Exception as e:
        results.add_result("Existing User Login", False, f"Error: {str(e)}")

def test_profile_picture_comprehensive(results):
    """Run comprehensive profile picture upload tests"""
    print("\n" + "="*60)
    print("🖼️  PROFILE PICTURE UPLOAD TESTING")
    print("="*60)
    
    # Test authentication requirements
    test_profile_picture_authentication(results)
    
    # Test successful upload cases
    avatar_url = test_profile_picture_upload_success(results)
    
    # Test PNG transparency handling
    test_profile_picture_png_transparency(results)
    
    # Test different aspect ratios (center crop verification)
    test_profile_picture_aspect_ratios(results)
    
    # Test validation and error cases
    test_profile_picture_validation(results)
    
    # Test database update
    test_profile_picture_database_update(results)
    
    # Test with existing user credentials
    test_existing_user_credentials(results)

def main():
    """Run all image upload and serving tests"""
    print("🧪 Starting Comprehensive Backend Image Upload Tests")
    print(f"Backend URL: {BACKEND_URL}")
    print("Testing the complete image upload flow including Profile Picture Upload")
    
    results = TestResults()
    
    # Test sequence - start with basic functionality
    auth_success = test_user_authentication(results)
    
    if auth_success:
        # PROFILE PICTURE UPLOAD TESTS (NEW FEATURE)
        test_profile_picture_comprehensive(results)
        
        # Basic functionality tests (existing)
        image_path = test_create_idea_with_image(results)
        
        if image_path:
            test_image_serving(results, image_path)
        
        comment_image_path = test_create_comment_with_image(results)
        if comment_image_path:
            test_image_serving(results, comment_image_path)
        
        test_migration_endpoint(results)
        test_retrieve_idea_attachments(results)
        test_multiple_image_formats(results)
        
        # Comprehensive edge case and error testing
        test_edge_cases(results)
        test_specific_user_scenario(results)
        test_form_data_parsing(results)
        test_frontend_integration_scenarios(results)
        test_cors_and_headers(results)
    
    # Print summary
    print("\n" + "="*60)
    print("🏁 COMPREHENSIVE TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results.results if r["success"])
    total = len(results.results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Show failed tests with details
    failed_tests = [r for r in results.results if not r["success"]]
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['test']}: {test['message']}")
            if test.get('details'):
                print(f"    Details: {test['details']}")
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    # Return results for programmatic use
    return results

if __name__ == "__main__":
    results = main()
    
    # Exit with error code if any tests failed
    failed_count = sum(1 for r in results.results if not r["success"])
    sys.exit(failed_count)