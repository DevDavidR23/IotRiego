"""Test all 4 control endpoints using requests library with local Django server."""
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ApiRiego.settings')
django.setup()

base = 'http://127.0.0.1:8000'

print("=" * 60)
print("TESTING 4 CONTROL ENDPOINTS")
print("=" * 60)
print()

# Test 1: POST /api/control/control/ (control device)
print("TEST 1: POST /api/control/control/")
print("-" * 60)
try:
    response = requests.post(f'{base}/api/control/control/', 
        json={"dispositivo": "bomba", "estado": "ON"},
        timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Content: {response.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")
print()

# Test 2: POST /api/control/control/motor/ (motor)
print("TEST 2: POST /api/control/control/motor/")
print("-" * 60)
try:
    response = requests.post(f'{base}/api/control/control/motor/', 
        json={"duracion": 10},
        timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Content: {response.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")
print()

# Test 3: POST /api/control/control/read-sensor/ (read sensor)
print("TEST 3: POST /api/control/control/read-sensor/")
print("-" * 60)
try:
    response = requests.post(f'{base}/api/control/control/read-sensor/', 
        json={},
        timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Content: {response.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")
print()

# Test 4: GET /api/control/control/health/ (health)
print("TEST 4: GET /api/control/control/health/")
print("-" * 60)
try:
    response = requests.get(f'{base}/api/control/control/health/', 
        timeout=5)
    print(f"  Status: {response.status_code}")
    print(f"  Content: {response.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")
print()

print("=" * 60)
print("RESUMEN")
print("=" * 60)