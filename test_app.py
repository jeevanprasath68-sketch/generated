import pytest
from datetime import date
from app import LostFoundEngine

@pytest.fixture
def test_engine(tmp_path):
    db_file = tmp_path / "test_campusfind.db"
    engine = LostFoundEngine(db_path=f"sqlite:///{db_file}")
    return engine

def test_add_item_happy_path(test_engine):
    item_data = {
        "title": "MacBook Pro 14",
        "category": "Electronics",
        "location": "Student Union",
        "date_lost_found": date(2023, 10, 25),
        "status": "Lost",
        "description": "Space gray with sticker on lid",
        "contact_email": "student@campus.edu"
    }
    item_id = test_engine.add_item(item_data)
    assert item_id == 1
    
    items = test_engine.get_items()
    assert len(items) == 1
    assert items[0]['title'] == "MacBook Pro 14"
    assert items[0]['status'] == "Lost"

def test_get_items_filtering_and_search(test_engine):
    test_engine.add_item({
        "title": "Calculus Textbook",
        "category": "Books & Notes",
        "location": "Library",
        "date_lost_found": date(2023, 10, 26),
        "status": "Found",
        "description": "Stewart 8th edition",
        "contact_email": "finder@campus.edu"
    })
    test_engine.add_item({
        "title": "Calculus Notes",
        "category": "Books & Notes",
        "location": "Science Hall",
        "date_lost_found": date(2023, 10, 27),
        "status": "Lost",
        "description": "Loose leaf binder",
        "contact_email": "student2@campus.edu"
    })
    
    # Test search query
    results = test_engine.get_items(search_query="Calculus")
    assert len(results) == 2
    
    # Test category filter
    results_cat = test_engine.get_items(category="Books & Notes")
    assert len(results_cat) == 2
    
    # Test status filter
    results_status = test_engine.get_items(status="Found")
    assert len(results_status) == 1
    assert results_status[0]['title'] == "Calculus Textbook"

def test_submit_claim(test_engine):
    item_id = test_engine.add_item({
        "title": "Campus Dorm Key",
        "category": "Keys",
        "location": "Quad",
        "date_lost_found": date(2023, 10, 28),
        "status": "Found",
        "description": "Key ring with blue strap",
        "contact_email": "security@campus.edu"
    })
    
    success = test_engine.submit_claim(item_id, "Room 402 key tag attached")
    assert success is True
    
    items = test_engine.get_items(status="Claimed")
    assert len(items) == 1
    assert items[0]['status'] == "Claimed"
    assert items[0]['claim_details'] == "Room 402 key tag attached"

def test_submit_claim_invalid_id(test_engine):
    success = test_engine.submit_claim(999, "Invalid claim")
    assert success is False

def test_add_item_missing_required_fields(test_engine):
    with pytest.raises(Exception):
        # Missing mandatory 'title'
        test_engine.add_item({
            "category": "Electronics",
            "location": "Library",
            "date_lost_found": date(2023, 10, 25),
            "status": "Lost",
            "contact_email": "test@campus.edu"
        })