#!/usr/bin/env python3
import requests
import io
from PIL import Image
import os

BACKEND_URL = "https://swapideas.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Create user and get token
signup_data = {
    "name": "Quick Test User",
    "username": f"quicktest_{os.urandom(4).hex()}",
    "email": f"quicktest_{os.urandom(4).hex()}@example.com",
    "password": "testpassword123"
}

print("Creating user...")
response = requests.post(f"{API_BASE}/signup", json=signup_data)
print(f"Signup status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    token = data.get("token")
    print(f"Got token: {token[:50]}...")
    
    # Auto-verify email
    headers = {"Authorization": f"Bearer {token}"}
    verify_response = requests.post(f"{API_BASE}/verify-email-auto", headers=headers)
    print(f"Verify status: {verify_response.status_code}")
    
    # Create test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    # Test idea creation without image first
    data = {
        'title': 'Test Idea without Image',
        'body': 'This is a test idea to verify basic functionality works correctly.'
    }
    
    # Test with JSON first (no files)
    print("Creating idea with JSON...")
    json_data = {
        'title': 'Test Idea JSON',
        'body': 'This is a test idea to verify JSON functionality works correctly.'
    }
    idea_response = requests.post(f"{API_BASE}/ideas", headers=headers, json=json_data)
    print(f"JSON status: {idea_response.status_code}")
    print(f"JSON response: {idea_response.text}")
    
    # Test form data without files
    print("Creating idea with form data...")
    form_data = {
        'title': 'Test Idea Form',
        'body': 'This is a test idea to verify form functionality works correctly.'
    }
    idea_response = requests.post(f"{API_BASE}/ideas", headers=headers, data=form_data)
    print(f"Form status: {idea_response.status_code}")
    print(f"Form response: {idea_response.text}")
    
    # Now test with image using multipart
    img_bytes.seek(0)  # Reset image buffer
    files = {
        'images': ('test.jpg', img_bytes, 'image/jpeg')
    }
    
    data = {
        'title': 'Test Idea with Image Upload',
        'body': 'This is a test idea to verify image upload functionality works correctly.'
    }
    
    print("Creating idea with image...")
    idea_response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
    print(f"Idea creation status: {idea_response.status_code}")
    print(f"Response: {idea_response.text}")
    
    if idea_response.status_code == 200:
        idea_data = idea_response.json()
        attachments = idea_data.get("attachments", [])
        print(f"Attachments: {attachments}")
        
        if attachments:
            # Test image access
            image_url = f"{BACKEND_URL}{attachments[0]}"
            print(f"Testing image URL: {image_url}")
            img_response = requests.get(image_url)
            print(f"Image access status: {img_response.status_code}")
            print(f"Content-Type: {img_response.headers.get('content-type')}")
else:
    print(f"Signup failed: {response.text}")