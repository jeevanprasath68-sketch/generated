import os
import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Date, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# --- DATABASE & ORM SETUP ---
Base = declarative_base()

class DBItem(Base):
    __tablename__ = 'lost_found_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    date_lost_found = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default='Lost')  # 'Lost', 'Found', 'Claimed'
    description = Column(Text, nullable=True)
    contact_email = Column(String(120), nullable=False)
    claim_details = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "location": self.location,
            "date_lost_found": self.date_lost_found,
            "status": self.status,
            "description": self.description,
            "contact_email": self.contact_email,
            "claim_details": self.claim_details
        }

class LostFoundEngine:
    def __init__(self, db_path: str = "sqlite:///campusfind.db"):
        self.engine = create_engine(db_path, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def add_item(self, data: Dict[str, Any]) -> int:
        session = self.SessionLocal()
        try:
            db_item = DBItem(
                title=data['title'],
                category=data['category'],
                location=data['location'],
                date_lost_found=data['date_lost_found'],
                status=data['status'],
                description=data.get('description', ''),
                contact_email=data['contact_email']
            )
            session.add(db_item)
            session.commit()
            session.refresh(db_item)
            return db_item.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_items(self, search_query: str = "", category: str = "All", status: str = "All") -> List[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            query = session.query(DBItem)
            
            if status != "All":
                query = query.filter(DBItem.status == status)
            
            if category != "All":
                query = query.filter(DBItem.category == category)
                
            if search_query:
                sq = f"%{search_query}%"
                query = query.filter(
                    (DBItem.title.ilike(sq)) |
                    (DBItem.description.ilike(sq)) |
                    (DBItem.location.ilike(sq))
                )
                
            items = query.order_by(DBItem.date_lost_found.desc()).all()
            return [item.to_dict() for item in items]
        finally:
            session.close()

    def submit_claim(self, item_id: int, claim_details: str) -> bool:
        session = self.SessionLocal()
        try:
            item = session.query(DBItem).filter(DBItem.id == item_id).first()
            if item:
                item.claim_details = claim_details
                item.status = "Claimed"
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# --- STREAMLIT UI ----
def main():
    st.set_page_config(
        page_title="CampusFind — College Lost & Found Portal",
        page_icon="🎒",
        layout="wide"
    )
    
    # Initialize Engine
    if 'engine' not in st.session_state:
        st.session_state.engine = LostFoundEngine()
        
    engine: LostFoundEngine = st.session_state.engine

    st.title("🎒 CampusFind — College Lost & Found Portal")
    st.markdown("Welcome to the official campus hub to report, search, and claim lost or found belongings! ✨")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ["Browse & Search Items", "Report Lost/Found Item", "Claim Dashboard"])

    # CATEGORIES
    categories = ["All", "Electronics", "IDs & Cards", "Books & Notes", "Clothing & Accessories", "Keys", "Others"]
    statuses = ["All", "Lost", "Found", "Claimed"]

    if choice == "Browse & Search Items":
        st.header("🔍 Browse & Search Items")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_query = st.text_input("Search keywords (title, description, location)", "")
        with col2:
            selected_cat = st.selectbox("Filter by Category", categories)
        with col3:
            selected_status = st.selectbox("Filter by Status", statuses)
            
        items = engine.get_items(search_query=search_query, category=selected_cat, status=selected_status)
        
        # KPIs
        total_items = len(items)
        lost_count = sum(1 for i in items if i['status'] == 'Lost')
        found_count = sum(1 for i in items if i['status'] == 'Found')
        claimed_count = sum(1 for i in items if i['status'] == 'Claimed')
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Matching Items", total_items)
        kpi2.metric("Lost", lost_count)
        kpi3.metric("Found", found_count)
        kpi4.metric("Claimed", claimed_count)
        
        st.divider()
        
        if not items:
            st.info("No items found matching your criteria.")
        else:
            for item in items:
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        status_badge = f"🟢 {item['status']}" if item['status'] == 'Found' else (f"🔴 {item['status']}" if item['status'] == 'Lost' else f"🔵 {item['status']}")
                        st.subheader(f"{item['title']} [{status_badge}]")
                        st.markdown(f"**Category:** {item['category']} | **Location:** {item['location']} | **Date:** {item['date_lost_found']}")
                        if item['description']:
                            st.write(f"{item['description']}")
                        st.caption(f"Contact: {item['contact_email']}")
                    with col_b:
                        if item['status'] != 'Claimed':
                            if st.button(f"Claim / Info #{item['id']}", key=f"btn_{item['id']}"):
                                st.session_state['claiming_item_id'] = item['id']
                        else:
                            st.success("Item Claimed")
                    st.markdown("---")

    elif choice == "Report Lost/Found Item":
        st.header("📝 Report a Lost or Found Item")
        
        with st.form("report_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Item Title (e.g., Blue HydroFlask, Student ID)", "")
                category = st.selectbox("Category", categories[1:])
                location = st.text_input("Location (e.g., Library 2nd Floor, Science Hall)", "")
            with col2:
                status = st.selectbox("Status", ["Lost", "Found"])
                date_lost_found = st.date_input("Date", value=date.today())
                contact_email = st.text_input("Your Campus Email", "")
                
            description = st.text_area("Detailed Description (Serial numbers, distinguishing marks, etc.)", "")
            
            submitted = st.form_submit_button("Submit Report")
            if submitted:
                if not title or not location or not contact_email:
                    st.error("Please fill out all required fields (Title, Location, Email).")
                else:
                    try:
                        new_id = engine.add_item({
                            "title": title,
                            "category": category,
                            "location": location,
                            "date_lost_found": date_lost_found,
                            "status": status,
                            "description": description,
                            "contact_email": contact_email
                        })
                        st.success(f"Success! Your item has been logged with ID #{new_id}.")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

    elif choice == "Claim Dashboard":
        st.header("🏷️ Item Claim Verification")
        st.markdown("Have you found your lost item listed on CampusFind? Submit a claim request here for verification by campus security or the finder.")
        
        # Allow picking item ID or pre-selected from browse
        default_id = st.session_state.get('claiming_item_id', 1)
        
        all_active_items = [i for i in engine.get_items(status="All") if i['status'] != 'Claimed']
        if not all_active_items:
            st.info("No unclaimed items available to claim right now.")
        else:
            item_options = {f"#{item['id']} - {item['title']} ({item['status']})": item['id'] for item in all_active_items}
            selected_label = st.selectbox("Select Item to Claim", list(item_options.keys()))
            target_id = item_options[selected_label]
            
            # Show target item details
            selected_item = next((i for i in all_active_items if i['id'] == target_id), None)
            if selected_item:
                st.info(f"**Selected:** {selected_item['title']} | **Location:** {selected_item['location']} | **Contact:** {selected_item['contact_email']}")
            
            with st.form("claim_form"):
                claim_details = st.text_area("Proof of Ownership / Verification Details (e.g., student ID number, unique scratches, contents inside bag)", "")
                claim_submit = st.form_submit_button("Submit Claim")
                
                if claim_submit:
                    if not claim_details.strip():
                        st.error("Please provide ownership details for verification.")
                    else:
                        success = engine.submit_claim(target_id, claim_details)
                        if success:
                            st.success("Claim submitted successfully! The finder or campus office will contact you via email.")
                            if 'claiming_item_id' in st.session_state:
                                del st.session_state['claiming_item_id']
                        else:
                            st.error("Failed to submit claim. Item may no longer exist.")

if __name__ == '__main__':
    main()