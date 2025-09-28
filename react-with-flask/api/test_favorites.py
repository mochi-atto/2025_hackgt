#!/usr/bin/env python3
"""
Quick smoke test for Favorites endpoints
"""

import requests

def test_favorites():
    base_url = "http://127.0.0.1:5001"
    user_id = "demo_user"

    print("\n⭐ Testing Favorites endpoints")

    # 1) List current favorites
    r = requests.get(f"{base_url}/api/favorites?user_id={user_id}")
    if r.status_code == 200:
        data = r.json()
        print(f"Favorites before: {data['total_count']}")
    else:
        print("List favorites failed:", r.text)
        return False

    # 2) Try adding a favorite by custom_food_id=1 (if exists)
    payload = {"user_id": user_id, "custom_food_id": 1, "display_name": "My leftover"}
    r = requests.post(f"{base_url}/api/favorites", json=payload)
    if r.status_code in (201, 409):
        print("Add favorite status:", r.status_code)
    else:
        print("Add favorite failed:", r.text)
        return False

    # 3) List again
    r = requests.get(f"{base_url}/api/favorites?user_id={user_id}")
    if r.status_code == 200:
        data = r.json()
        print(f"Favorites after: {data['total_count']}")
        if data['favorites']:
            fav_id = data['favorites'][0]['id']
        else:
            print("No favorites found after add; skipping delete")
            return True
    else:
        print("List favorites failed:", r.text)
        return False

    # 4) Delete one favorite
    r = requests.delete(f"{base_url}/api/favorites/{fav_id}?user_id={user_id}")
    if r.status_code == 200:
        print("Deleted favorite", fav_id)
    else:
        print("Delete favorite failed:", r.text)
        return False

    return True

if __name__ == "__main__":
    ok = test_favorites()
    print("✅ Favorites smoke test PASS" if ok else "❌ Favorites smoke test FAIL")