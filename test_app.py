import os
import pytest
import datetime
from app import ItemManager

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_campusfind.db"
    manager = ItemManager(db_path=str(db_file))
    return manager

def test_add_and_get_item(temp_db):
    item_data = {
        "title": "MacBook Pro",
        "category": "Electronics",
        "description": "Space Gray 14-inch M2",
        "location": "Student Union",
        "status": "Lost",
        "reporter_name": "Alice Smith",
        "reporter_contact": "alice@college.edu",
        "date_posted": datetime.date.today().isoformat()
    }
    
    item_id = temp_db.add_item(item_data)
    assert item_id > 0
    
    items = temp_db.get_items()
    assert len(items) == 1
    assert items[0]["title"] == "MacBook Pro"
    assert items[0]["category"] == "Electronics"
    assert items[0]["claim_status"] == "Unclaimed"

def test_missing_required_fields(temp_db):
    item_data = {
        "title": "Incomplete Item",
        "category": "Keys",
        "description": "Missing contact info",
        "location": "Library",
        "status": "Found",
        "reporter_name": "Bob",
        "reporter_contact": ""
    }
    
    with pytest.raises(ValueError, match="Missing required field"):
        temp_db.add_item(item_data)

def test_invalid_status(temp_db):
    item_data = {
        "title": "Bad Status Item",
        "category": "Other",
        "description": "Some description",
        "location": "Quad",
        "status": "Stolen",  # Invalid status
        "reporter_name": "Charlie",
        "reporter_contact": "charlie@college.edu"
    }
    
    with pytest.raises(ValueError, match="Status must be either 'Lost' or 'Found'"):
        temp_db.add_item(item_data)

def test_search_and_filter(temp_db):
    temp_db.add_item({
        "title": "Calculus Textbook",
        "category": "Books & Notes",
        "description": "Stewart Calculus 8th Edition",
        "location": "Science Hall",
        "status": "Lost",
        "reporter_name": "Dave",
        "reporter_contact": "dave@college.edu"
    })
    
    temp_db.add_item({
        "title": "Car Keys",
        "category": "Keys",
        "description": "Toyota fob with blue lanyard",
        "location": "Parking Lot C",
        "status": "Found",
        "reporter_name": "Eve",
        "reporter_contact": "eve@college.edu"
    })
    
    # Test search query
    results = temp_db.get_items(search_query="Toyota")
    assert len(results) == 1
    assert results[0]["title"] == "Car Keys"
    
    # Test category filter
    results_cat = temp_db.get_items(category="Books & Notes")
    assert len(results_cat) == 1
    assert results_cat[0]["title"] == "Calculus Textbook"
    
    # Test status filter
    results_status = temp_db.get_items(status="Found")
    assert len(results_status) == 1
    assert results_status[0]["title"] == "Car Keys"

def test_submit_and_update_claim(temp_db):
    item_id = temp_db.add_item({
        "title": "Blue Water Bottle",
        "category": "Other",
        "description": "HydroFlask 32oz",
        "location": "Gym",
        "status": "Found",
        "reporter_name": "Frank",
        "reporter_contact": "frank@college.edu"
    })
    
    # Submit claim
    success = temp_db.submit_claim(item_id, "Grace", "grace@college.edu", "Has a sticker on the bottom")
    assert success is True
    
    items = temp_db.get_items()
    assert items[0]["claim_status"] == "Pending Claim"
    assert items[0]["claimant_name"] == "Grace"
    
    # Update claim status
    success_update = temp_db.update_claim_status(item_id, "Resolved / Returned")
    assert success_update is True
    
    items_updated = temp_db.get_items()
    assert items_updated[0]["claim_status"] == "Resolved / Returned"

def test_database_reset(temp_db):
    temp_db.add_item({
        "title": "Umbrella",
        "category": "Clothing",
        "description": "Black compact umbrella",
        "location": "Student Center",
        "status": "Lost",
        "reporter_name": "Heidi",
        "reporter_contact": "heidi@college.edu"
    })
    assert len(temp_db.get_items()) == 1
    
    temp_db.reset_database()
    assert len(temp_db.get_items()) == 0