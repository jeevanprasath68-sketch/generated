import os
import pytest
import datetime
from app import CampusDatabase

@pytest.fixture
def py_db(tmp_path):
    db_file = tmp_path / "test_campusfind.db"
    db = CampusDatabase(db_path=str(db_file))
    return db

def test_init_database(py_db):
    stats = py_db.get_stats()
    assert stats["total"] == 0
    assert stats["lost"] == 0
    assert stats["found"] == 0
    assert stats["claimed"] == 0

def test_add_item_success(py_db):
    item_data = {
        "title": "MacBook Pro",
        "description": "14-inch M2 Space Gray with stickers",
        "category": "Electronics",
        "status": "Lost",
        "location": "Library 3rd Floor",
        "reporter_name": "Alice Smith",
        "reporter_contact": "alice@college.edu"
    }
    item_id = py_db.add_item(item_data)
    assert item_id > 0

    stats = py_db.get_stats()
    assert stats["total"] == 1
    assert stats["lost"] == 1

def test_add_item_missing_field(py_db):
    item_data = {
        "title": "Incomplete Item",
        "description": "Missing required fields",
        "category": "Other",
        "status": "Found",
        "location": "",
        "reporter_name": "Bob",
        "reporter_contact": "bob@college.edu"
    }
    with pytest.raises(ValueError, match="Missing required field: location"):
        py_db.add_item(item_data)

def test_get_items_filtering_and_search(py_db):
    py_db.add_item({
        "title": "Scientific Calculator",
        "description": "Casio fx-991EX",
        "category": "Electronics",
        "status": "Lost",
        "location": "Science Hall",
        "reporter_name": "Charlie",
        "reporter_contact": "charlie@college.edu"
    })
    py_db.add_item({
        "title": "Dorm Room Keys",
        "description": "3 keys on a lanyard",
        "category": "Keys",
        "status": "Found",
        "location": "Quad",
        "reporter_name": "Diana",
        "reporter_contact": "diana@college.edu"
    })

    all_items = py_db.get_items()
    assert len(all_items) == 2

    # Test search query
    search_res = py_db.get_items(search_query="Casio")
    assert len(search_res) == 1
    assert search_res[0]["title"] == "Scientific Calculator"

    # Test category filter
    cat_res = py_db.get_items(category="Keys")
    assert len(cat_res) == 1
    assert cat_res[0]["category"] == "Keys"

    # Test status filter
    status_res = py_db.get_items(status="Lost")
    assert len(status_res) == 1
    assert status_res[0]["status"] == "Lost"

def test_update_claim(py_db):
    item_id = py_db.add_item({
        "title": "Student ID Card",
        "description": "ID #123456",
        "category": "ID & Cards",
        "status": "Found",
        "location": "Cafeteria",
        "reporter_name": "Security",
        "reporter_contact": "security@college.edu"
    })

    success = py_db.update_claim(item_id, "Claimed", "Picked up by owner with ID verification.")
    assert success is True

    items = py_db.get_items()
    assert items[0]["claim_status"] == "Claimed"
    assert items[0]["claim_notes"] == "Picked up by owner with ID verification."

    stats = py_db.get_stats()
    assert stats["claimed"] == 1