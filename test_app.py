import pytest
import os
from app import DatabaseEngine, ItemValidator

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_campus.db"
    engine = DatabaseEngine(db_path=str(db_file))
    return engine

def test_database_initialization(test_db):
    items = test_db.get_items()
    assert isinstance(items, list)
    assert len(items) == 0

def test_add_and_retrieve_item(test_db):
    item_data = {
        "title": "MacBook Pro 14",
        "category": "Electronics",
        "status": "Lost",
        "location": "Library 3rd Floor",
        "date_lost_found": "2023-10-25",
        "description": "Space gray with stickers on lid",
        "contact_info": "student@college.edu"
    }
    item_id = test_db.add_item(item_data)
    assert item_id > 0

    items = test_db.get_items()
    assert len(items) == 1
    assert items[0]["title"] == "MacBook Pro 14"
    assert items[0]["category"] == "Electronics"
    assert items[0]["status"] == "Lost"
    assert items[0]["claim_status"] == "Unclaimed"

def test_item_validator():
    # Valid item data
    valid_data = {
        "title": "Calculus Textbook",
        "category": "Books & Notes",
        "location": "Science Hall",
        "contact_info": "mathwiz@college.edu"
    }
    assert ItemValidator.validate_item_submission(valid_data) == []

    # Invalid item data (missing required fields)
    invalid_data = {
        "title": "",
        "category": "",
        "location": "",
        "contact_info": ""
    }
    errors = ItemValidator.validate_item_submission(invalid_data)
    assert len(errors) == 4
    assert "Title is required." in errors
    assert "Category is required." in errors

def test_update_claim(test_db):
    item_data = {
        "title": "Campus Dorm Key",
        "category": "Keys",
        "status": "Found",
        "location": "Cafeteria",
        "date_lost_found": "2023-10-26",
        "description": "Room 402 key with blue lanyard",
        "contact_info": "security@college.edu"
    }
    item_id = test_db.add_item(item_data)
    
    success = test_db.update_claim(item_id, "Claim Pending", "Claimant: John Doe (ID: 12345)")
    assert success is True

    items = test_db.get_items()
    assert items[0]["claim_status"] == "Claim Pending"
    assert "John Doe" in items[0]["claim_details"]

def test_delete_item(test_db):
    item_data = {
        "title": "Water Bottle",
        "category": "Other",
        "status": "Lost",
        "location": "Gym",
        "date_lost_found": "2023-10-27",
        "contact_info": "gym@college.edu"
    }
    item_id = test_db.add_item(item_data)
    assert len(test_db.get_items()) == 1

    success = test_db.delete_item(item_id)
    assert success is True
    assert len(test_db.get_items()) == 0