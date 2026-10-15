import pytest
import os
from datetime import date
from app import DatabaseManager, MatchingEngine, DB_NAME

@pytest.fixture
def temp_db():
    test_db_name = "test_campusfind.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)
    db = DatabaseManager(db_path=test_db_name)
    yield db
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

def test_item_creation_and_persistence(temp_db):
    # Test happy path item creation and database persistence retrieval
    item_id = temp_db.add_item(
        title="Calculus Textbook",
        description="Hardcover 8th edition with blue cover",
        category="Books & Notes",
        status="Lost",
        location="Library",
        date_reported=str(date.today()),
        contact_info="student@college.edu"
    )
    assert item_id > 0
    
    items = temp_db.get_all_items()
    assert len(items) == 1
    assert items[0]["title"] == "Calculus Textbook"
    assert items[0]["category"] == "Books & Notes"
    assert items[0]["status"] == "Lost"

def test_invalid_item_creation(temp_db):
    # Test input validation and expected exceptions for empty fields or invalid status
    with pytest.raises(ValueError):
        temp_db.add_item(
            title="",
            description="Description",
            category="Electronics",
            status="Lost",
            location="Library",
            date_reported="2023-10-01",
            contact_info="test@test.com"
        )
        
    with pytest.raises(ValueError):
        temp_db.add_item(
            title="Valid Title",
            description="Description",
            category="Electronics",
            status="InvalidStatus",
            location="Library",
            date_reported="2023-10-01",
            contact_info="test@test.com"
        )

def test_status_update_and_deletion(temp_db):
    item_id = temp_db.add_item(
        title="iPhone 13",
        description="Black case, cracked screen protector",
        category="Electronics",
        status="Lost",
        location="Student Union",
        date_reported=str(date.today()),
        contact_info="phone@college.edu"
    )
    
    # Test status change
    success = temp_db.update_status(item_id, "Claimed/Resolved")
    assert success is True
    items = temp_db.get_all_items()
    assert items[0]["status"] == "Claimed/Resolved"
    
    # Test deletion
    del_success = temp_db.delete_item(item_id)
    assert del_success is True
    assert len(temp_db.get_all_items()) == 0

def test_statistics_calculation(temp_db):
    temp_db.add_item("Keys", "Dorm keys", "Keys", "Lost", "Quad", str(date.today()), "a@b.com")
    temp_db.add_item("Wallet", "Brown leather", "Bags & Wallets", "Found", "Library", str(date.today()), "c@d.com")
    temp_db.add_item("Bottle", "Hydro flask", "Water Bottles", "Claimed/Resolved", "Dining Commons", str(date.today()), "e@f.com")
    
    stats = temp_db.get_statistics()
    assert stats["total"] == 3
    assert stats["unresolved"] == 2
    assert stats["resolved"] == 1

def test_matching_algorithm():
    item_lost = {
        "id": 1,
        "title": "Silver MacBook Pro",
        "description": "Lost silver laptop with stickers in library",
        "category": "Electronics",
        "status": "Lost",
        "location": "Library",
        "date_reported": "2023-10-01",
        "contact_info": "lost@college.edu"
    }
    
    item_found = {
        "id": 2,
        "title": "Apple MacBook Pro",
        "description": "Found silver laptop inside library study room",
        "category": "Electronics",
        "status": "Found",
        "location": "Library",
        "date_reported": "2023-10-02",
        "contact_info": "found@college.edu"
    }
    
    score = MatchingEngine.calculate_match_score(item_lost, item_found)
    assert score >= 70.0  # High match expected for category, location, and keywords
    
    # Same status items should return 0 score
    item_lost_2 = item_found.copy()
    item_lost_2["status"] = "Lost"
    zero_score = MatchingEngine.calculate_match_score(item_lost, item_lost_2)
    assert zero_score == 0.0

def test_empty_search_and_matching(temp_db):
    # Test matching with empty database
    matches = MatchingEngine.find_potential_matches(temp_db.get_all_items())
    assert len(matches) == 0

    # Test statistics on empty database
    stats = temp_db.get_statistics()
    assert stats["total"] == 0
    assert stats["unresolved"] == 0
    assert stats["resolved"] == 0