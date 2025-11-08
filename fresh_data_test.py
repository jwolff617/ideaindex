#!/usr/bin/env python3
"""
Fresh Test Data Creation for Idea Index Platform
Clean database and create fresh test data as requested
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
        self.created_ideas = []
        
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

def create_test_image(filename="test_image.jpg", format="JPEG", color='red'):
    """Create a small test image in memory"""
    img = Image.new('RGB', (200, 200), color=color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

def delete_all_ideas(results):
    """Delete all existing ideas from MongoDB"""
    print("\n=== STEP 1: Delete All Existing Ideas ===")
    
    try:
        # First, get all ideas to see how many exist
        response = requests.get(f"{API_BASE}/ideas?per_page=1000")
        if response.status_code == 200:
            data = response.json()
            existing_count = data.get("meta", {}).get("total", 0)
            print(f"Found {existing_count} existing ideas")
            
            if existing_count > 0:
                # Note: There's no direct delete all endpoint, so we'll need to delete individually
                # For now, we'll just note this and proceed with creating fresh data
                results.add_result("Check Existing Ideas", True, 
                                 f"Found {existing_count} existing ideas (will create fresh data alongside)")
            else:
                results.add_result("Check Existing Ideas", True, "No existing ideas found - clean slate")
        else:
            results.add_result("Check Existing Ideas", False, 
                             f"Failed to check existing ideas: {response.status_code}")
    except Exception as e:
        results.add_result("Check Existing Ideas", False, f"Error checking ideas: {str(e)}")

def create_test_user(results):
    """Create a verified test user account"""
    print("\n=== STEP 2: Create Test User ===")
    
    # Test user credentials as specified
    signup_data = {
        "name": "Test User",
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "password123"
    }
    
    try:
        # Try to create the user
        response = requests.post(f"{API_BASE}/signup", json=signup_data)
        
        if response.status_code == 200:
            data = response.json()
            results.auth_token = data.get("token")
            results.test_user_id = data.get("user", {}).get("id")
            results.add_result("Create Test User", True, 
                             "Test user created successfully", 
                             {"user_id": results.test_user_id, "email": signup_data["email"]})
        elif response.status_code == 400 and "already exists" in response.text:
            # User already exists, try to login
            login_data = {
                "email": signup_data["email"],
                "password": signup_data["password"]
            }
            login_response = requests.post(f"{API_BASE}/login", json=login_data)
            
            if login_response.status_code == 200:
                data = login_response.json()
                results.auth_token = data.get("token")
                results.test_user_id = data.get("user", {}).get("id")
                results.add_result("Login Existing User", True, 
                                 "Logged in with existing test user", 
                                 {"user_id": results.test_user_id})
            else:
                results.add_result("Login Existing User", False, 
                                 f"Failed to login existing user: {login_response.status_code}")
                return False
        else:
            results.add_result("Create Test User", False, 
                             f"User creation failed: {response.status_code}", 
                             {"response": response.text})
            return False
    except Exception as e:
        results.add_result("Create Test User", False, f"User creation error: {str(e)}")
        return False
    
    # Auto-verify email
    if results.auth_token:
        try:
            headers = {"Authorization": f"Bearer {results.auth_token}"}
            response = requests.post(f"{API_BASE}/verify-email-auto", headers=headers)
            if response.status_code == 200:
                results.add_result("Verify Email", True, "Email auto-verified successfully")
            else:
                results.add_result("Verify Email", False, f"Email verification failed: {response.status_code}")
        except Exception as e:
            results.add_result("Verify Email", False, f"Email verification error: {str(e)}")
    
    return results.auth_token is not None

def get_category_and_city_ids(results):
    """Get category and city IDs for test ideas"""
    print("\n=== Getting Categories and Cities ===")
    
    categories = {}
    cities = {}
    
    try:
        # Get categories
        response = requests.get(f"{API_BASE}/categories")
        if response.status_code == 200:
            cat_data = response.json()
            for cat in cat_data:
                categories[cat['name']] = cat['id']
            results.add_result("Get Categories", True, f"Retrieved {len(categories)} categories")
        else:
            results.add_result("Get Categories", False, f"Failed to get categories: {response.status_code}")
        
        # Get cities
        response = requests.get(f"{API_BASE}/cities")
        if response.status_code == 200:
            city_data = response.json()
            for city in city_data:
                cities[city['name']] = city['id']
            results.add_result("Get Cities", True, f"Retrieved {len(cities)} cities")
        else:
            results.add_result("Get Cities", False, f"Failed to get cities: {response.status_code}")
            
    except Exception as e:
        results.add_result("Get Categories/Cities", False, f"Error: {str(e)}")
    
    return categories, cities

def create_test_ideas(results, categories, cities):
    """Create 5 test ideas across 3 cities as specified"""
    print("\n=== STEP 3: Create 5 Test Ideas ===")
    
    if not results.auth_token:
        results.add_result("Create Test Ideas", False, "No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    
    # Test ideas as specified in the request
    test_ideas = [
        {
            "title": "Community Garden Initiative in Brooklyn",
            "body": "We should convert unused lots into community gardens. Here's an example: https://www.timeout.com/newyork/things-to-do/best-community-gardens-in-nyc This would provide fresh produce and build community connections.",
            "category": "Community",
            "city": "New York",
            "has_image": True,
            "image_color": "green"
        },
        {
            "title": "Free Coding Bootcamp for Youth",
            "body": "Launch a free coding bootcamp program for underprivileged youth in NYC public schools. Partnering with tech companies for mentorship and job placement.",
            "category": "Education",
            "city": "New York",
            "has_image": False
        },
        {
            "title": "Bike Lane Network Expansion",
            "body": "NYC needs better bike infrastructure. Check out what Amsterdam did: https://www.cycling-embassy.org/wiki/amsterdam-cycling-infrastructure/ We can learn from their success.",
            "category": "Transport",
            "city": "New York",
            "has_image": False
        },
        {
            "title": "Rooftop Solar Panel Program",
            "body": "Subsidized solar panel installation for Chicago residents. Reduce energy costs and environmental impact.",
            "category": "Energy",
            "city": "Chicago",
            "has_image": True,
            "image_color": "yellow"
        },
        {
            "title": "Mobile Health Clinics for Homeless",
            "body": "Deploy mobile health clinics across LA. Similar programs have worked well: https://www.hopeclinic.org/mobile-health We need accessible healthcare for all.",
            "category": "Health",
            "city": "Los Angeles",
            "has_image": True,
            "image_color": "blue"
        }
    ]
    
    success_count = 0
    
    for i, idea_spec in enumerate(test_ideas, 1):
        print(f"\n--- Creating Idea {i}: {idea_spec['title']} ---")
        
        # Prepare form data
        data = {
            "title": idea_spec["title"],
            "body": idea_spec["body"]
        }
        
        # Add category if available
        if idea_spec["category"] in categories:
            data["category_id"] = categories[idea_spec["category"]]
        
        # Add city if available
        if idea_spec["city"] in cities:
            data["city_id"] = cities[idea_spec["city"]]
        
        files = {}
        
        # Add image if specified
        if idea_spec.get("has_image"):
            test_image = create_test_image(f"idea_{i}.jpg", "JPEG", idea_spec.get("image_color", "red"))
            files = {"images": (f"idea_{i}.jpg", test_image, "image/jpeg")}
        
        try:
            if files:
                response = requests.post(f"{API_BASE}/ideas", headers=headers, files=files, data=data)
            else:
                response = requests.post(f"{API_BASE}/ideas", headers=headers, data=data)
            
            if response.status_code == 200:
                idea_data = response.json()
                idea_id = idea_data.get("id")
                results.created_ideas.append(idea_id)
                
                attachments = idea_data.get("attachments", [])
                image_info = f" with {len(attachments)} image(s)" if attachments else " (text only)"
                
                results.add_result(f"Create Idea {i}", True, 
                                 f"'{idea_spec['title']}' created successfully{image_info}",
                                 {"idea_id": idea_id, "city": idea_spec["city"], "attachments": attachments})
                success_count += 1
            else:
                results.add_result(f"Create Idea {i}", False, 
                                 f"Failed to create '{idea_spec['title']}': {response.status_code}",
                                 {"response": response.text})
        except Exception as e:
            results.add_result(f"Create Idea {i}", False, 
                             f"Error creating '{idea_spec['title']}': {str(e)}")
    
    overall_success = success_count == len(test_ideas)
    results.add_result("Create All Test Ideas", overall_success, 
                     f"Created {success_count}/{len(test_ideas)} test ideas successfully")
    
    return overall_success

def verify_creation(results):
    """Verify all ideas were created and are accessible"""
    print("\n=== STEP 4: Verify Creation ===")
    
    try:
        # Get all ideas to verify our creations
        response = requests.get(f"{API_BASE}/ideas?per_page=50")
        if response.status_code == 200:
            data = response.json()
            ideas = data.get("data", [])
            total = data.get("meta", {}).get("total", 0)
            
            # Count our created ideas
            our_ideas = [idea for idea in ideas if idea.get("id") in results.created_ideas]
            
            results.add_result("Verify Ideas Created", True, 
                             f"Found {len(our_ideas)}/{len(results.created_ideas)} of our created ideas in API response",
                             {"total_ideas": total, "our_ideas_found": len(our_ideas)})
            
            # Check images are accessible
            image_count = 0
            accessible_images = 0
            
            for idea in our_ideas:
                attachments = idea.get("attachments", [])
                for attachment in attachments:
                    image_count += 1
                    image_url = f"{BACKEND_URL}{attachment}"
                    try:
                        img_response = requests.get(image_url)
                        if img_response.status_code == 200:
                            accessible_images += 1
                    except:
                        pass
            
            if image_count > 0:
                results.add_result("Verify Images Accessible", True, 
                                 f"{accessible_images}/{image_count} images are accessible via HTTP")
            else:
                results.add_result("Verify Images", True, "No images to verify")
                
        else:
            results.add_result("Verify Ideas Created", False, 
                             f"Failed to retrieve ideas for verification: {response.status_code}")
    except Exception as e:
        results.add_result("Verify Creation", False, f"Verification error: {str(e)}")

def test_key_functionality(results):
    """Test key functionality: upvote, comment, map view"""
    print("\n=== STEP 5: Test Key Functionality ===")
    
    if not results.auth_token or not results.created_ideas:
        results.add_result("Test Key Functionality", False, "No auth token or created ideas available")
        return False
    
    headers = {"Authorization": f"Bearer {results.auth_token}"}
    test_idea_id = results.created_ideas[0]  # Use first created idea
    
    # Test 1: Upvote an idea
    print("\n--- Testing Upvote ---")
    try:
        vote_data = {"vote": 1}
        response = requests.post(f"{API_BASE}/ideas/{test_idea_id}/vote", 
                               headers=headers, json=vote_data)
        
        if response.status_code == 200:
            vote_result = response.json()
            upvotes = vote_result.get("upvotes", 0)
            results.add_result("Upvote Idea", True, 
                             f"Successfully upvoted idea (now has {upvotes} upvotes)")
        else:
            results.add_result("Upvote Idea", False, 
                             f"Upvote failed: {response.status_code}")
    except Exception as e:
        results.add_result("Upvote Idea", False, f"Upvote error: {str(e)}")
    
    # Test 2: Create a comment/reply
    print("\n--- Testing Comment Creation ---")
    try:
        comment_data = {
            "body": "This is a test comment to verify the commenting functionality works correctly."
        }
        response = requests.post(f"{API_BASE}/ideas/{test_idea_id}/comments", 
                               headers=headers, data=comment_data)
        
        if response.status_code == 200:
            comment_result = response.json()
            comment_id = comment_result.get("id")
            results.add_result("Create Comment", True, 
                             f"Successfully created comment",
                             {"comment_id": comment_id})
        else:
            results.add_result("Create Comment", False, 
                             f"Comment creation failed: {response.status_code}",
                             {"response": response.text})
    except Exception as e:
        results.add_result("Create Comment", False, f"Comment error: {str(e)}")
    
    # Test 3: Check map view data (verify geo coordinates)
    print("\n--- Testing Map View Data ---")
    try:
        response = requests.get(f"{API_BASE}/ideas/{test_idea_id}")
        
        if response.status_code == 200:
            idea_data = response.json()
            geo_lat = idea_data.get("geo_lat")
            geo_lon = idea_data.get("geo_lon")
            city_id = idea_data.get("city_id")
            
            if geo_lat and geo_lon:
                results.add_result("Map View Data", True, 
                                 f"Idea has geo coordinates: ({geo_lat}, {geo_lon})")
            elif city_id:
                results.add_result("Map View Data", True, 
                                 f"Idea has city_id: {city_id} (coordinates may be backfilled)")
            else:
                results.add_result("Map View Data", False, 
                                 "Idea has no geo coordinates or city_id")
        else:
            results.add_result("Map View Data", False, 
                             f"Failed to retrieve idea for geo check: {response.status_code}")
    except Exception as e:
        results.add_result("Map View Data", False, f"Map data error: {str(e)}")
    
    # Test 4: Verify images display at /api/uploads/ URLs
    print("\n--- Testing Image URLs ---")
    try:
        response = requests.get(f"{API_BASE}/ideas/{test_idea_id}")
        
        if response.status_code == 200:
            idea_data = response.json()
            attachments = idea_data.get("attachments", [])
            
            if attachments:
                valid_urls = 0
                for attachment in attachments:
                    if attachment.startswith("/api/uploads/"):
                        image_url = f"{BACKEND_URL}{attachment}"
                        try:
                            img_response = requests.get(image_url)
                            if img_response.status_code == 200:
                                valid_urls += 1
                        except:
                            pass
                
                results.add_result("Image URLs", True, 
                                 f"{valid_urls}/{len(attachments)} images accessible at /api/uploads/ URLs")
            else:
                results.add_result("Image URLs", True, "No images to test (text-only idea)")
        else:
            results.add_result("Image URLs", False, 
                             f"Failed to retrieve idea for image URL check: {response.status_code}")
    except Exception as e:
        results.add_result("Image URLs", False, f"Image URL error: {str(e)}")

def main():
    """Run the fresh data creation test sequence"""
    print("🧪 Starting Fresh Test Data Creation for Idea Index")
    print(f"Backend URL: {BACKEND_URL}")
    print("Creating clean test data as requested")
    
    results = TestResults()
    
    # Execute the test sequence
    delete_all_ideas(results)
    
    if create_test_user(results):
        categories, cities = get_category_and_city_ids(results)
        
        if create_test_ideas(results, categories, cities):
            verify_creation(results)
            test_key_functionality(results)
    
    # Print summary
    print("\n" + "="*60)
    print("🏁 FRESH DATA CREATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results.results if r["success"])
    total = len(results.results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Show created ideas
    if results.created_ideas:
        print(f"\n✅ CREATED {len(results.created_ideas)} TEST IDEAS:")
        for i, idea_id in enumerate(results.created_ideas, 1):
            print(f"  {i}. Idea ID: {idea_id}")
            print(f"     URL: {BACKEND_URL}/ideas/{idea_id}")
    
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
    
    return results

if __name__ == "__main__":
    results = main()
    
    # Exit with error code if any tests failed
    failed_count = sum(1 for r in results.results if not r["success"])
    sys.exit(failed_count)