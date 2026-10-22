import sqlite3
import datetime
from typing import List, Dict, Any, Optional
import streamlit as st

DB_PATH = "campusfind.db"

class ItemManager:
    """Business logic engine for managing items and claims with SQLite persistence."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT NOT NULL,
                reporter_name TEXT NOT NULL,
                reporter_contact TEXT NOT NULL,
                date_posted TEXT NOT NULL,
                claim_status TEXT DEFAULT 'Unclaimed',
                claimant_name TEXT DEFAULT '',
                claimant_contact TEXT DEFAULT '',
                claim_notes TEXT DEFAULT ''
            )
            """
        )
        conn.commit()
        
        # Self-healing migration: check for missing columns
        cursor.execute("PRAGMA table_info(items)")
        columns = [row["name"] for row in cursor.fetchall()]
        
        expected_columns = {
            "claim_status": "TEXT DEFAULT 'Unclaimed'",
            "claimant_name": "TEXT DEFAULT ''",
            "claimant_contact": "TEXT DEFAULT ''",
            "claim_notes": "TEXT DEFAULT ''"
        }
        
        for col, col_def in expected_columns.items():
            if col not in columns:
                cursor.execute(f"ALTER TABLE items ADD COLUMN {col} {col_def}")
                conn.commit()
                
        conn.close()

    def reset_database(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS items")
        conn.commit()
        conn.close()
        self._init_db()

    def add_item(self, data: Dict[str, Any]) -> int:
        required = ["title", "category", "description", "location", "status", "reporter_name", "reporter_contact"]
        for field in required:
            if not data.get(field):
                raise ValueError(f"Missing required field: {field}")
                
        if data["status"] not in ["Lost", "Found"]:
            raise ValueError("Status must be either 'Lost' or 'Found'")
            
        date_posted = data.get("date_posted", datetime.date.today().isoformat())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO items (title, category, description, location, status, reporter_name, reporter_contact, date_posted, claim_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["title"],
                data["category"],
                data["description"],
                data["location"],
                data["status"],
                data["reporter_name"],
                data["reporter_contact"],
                date_posted,
                "Unclaimed"
            )
        )
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return item_id

    def get_items(self, search_query: str = "", category: str = "All", status: str = "All") -> List[Dict[str, Any]]:
        self._init_db()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM items WHERE 1=1"
        params = []
        
        if search_query:
            query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
            q = f"%{search_query}%"
            params.extend([q, q, q])
            
        if category != "All":
            query += " AND category = ?"
            params.append(category)
            
        if status != "All":
            query += " AND status = ?"
            params.append(status)
            
        query += " ORDER BY date_posted DESC, id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def submit_claim(self, item_id: int, claimant_name: str, claimant_contact: str, claim_notes: str) -> bool:
        if not claimant_name or not claimant_contact:
            raise ValueError("Claimant name and contact are required.")
            
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE items 
            SET claim_status = 'Pending Claim', claimant_name = ?, claimant_contact = ?, claim_notes = ?
            WHERE id = ?
            """,
            (claimant_name, claimant_contact, claim_notes, item_id)
        )
        conn.commit()
        rowcount = cursor.rowcount
        conn.close()
        return rowcount > 0

    def update_claim_status(self, item_id: int, new_claim_status: str) -> bool:
        if new_claim_status not in ["Unclaimed", "Pending Claim", "Resolved / Returned"]:
            raise ValueError("Invalid claim status")
            
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE items SET claim_status = ? WHERE id = ?
            """,
            (new_claim_status, item_id)
        )
        conn.commit()
        rowcount = cursor.rowcount
        conn.close()
        return rowcount > 0


def main():
    st.set_page_config(
        page_title="CampusFind - College Lost & Found Portal",
        page_icon="🎒",
        layout="wide"
    )
    
    manager = ItemManager()

    st.sidebar.title("🎒 Navigation & Tools")
    page = st.sidebar.radio("Go to", ["Browse Portal", "Report Item / Hand-in", "Admin / Claims Portal"])
    
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Database Management"):
        if st.button("Reset Database / Clear All Data", type="secondary"):
            manager.reset_database()
            st.success("Database successfully wiped and re-initialized!")
            st.rerun()
            
    if page == "Browse Portal":
        st.title("🎒 CampusFind — Lost & Found Portal")
        st.markdown("Search and filter through items reported lost or found across campus. Claim items that belong to you!")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_query = st.text_input("🔍 Search keywords", "", placeholder="e.g., iPhone, keys, blue backpack")
        with col2:
            categories = ["All", "Electronics", "Keys", "ID / Cards", "Books & Notes", "Clothing", "Bags", "Other"]
            selected_category = st.selectbox("📁 Category", categories)
        with col3:
            statuses = ["All", "Lost", "Found"]
            selected_status = st.selectbox("📌 Status", statuses)
            
        items = manager.get_items(search_query=search_query, category=selected_category, status=selected_status)
        
        # KPIs
        total_items = len(manager.get_items())
        lost_count = len([i for i in manager.get_items() if i["status"] == "Lost"])
        found_count = len([i for i in manager.get_items() if i["status"] == "Found"])
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Portal Items", total_items)
        kpi2.metric("Reported Lost", lost_count)
        kpi3.metric("Reported Found / Handed In", found_count)
        st.markdown("---")
        
        if not items:
            st.info("No items match your search criteria.")
        else:
            for item in items:
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 2])
                    badge_color = "orange" if item["status"] == "Lost" else "green"
                    c1.markdown(f"### {item['title']} :orange_book:")
                    c1.markdown(f"**Category:** `{item['category']}` | **Status:** :{badge_color}[**{item['status']}**]")
                    c1.markdown(f"**Description:** {item['description']}")
                    
                    c2.markdown(f"📍 **Location:** {item['location']}")
                    c2.markdown(f"📅 **Date Posted:** {item['date_posted']}")
                    c2.markdown(f"🏷️ **Claim State:** `{item['claim_status']}`")
                    
                    with c3:
                        with st.expander("View Contact & Claim"):
                            st.write(f"**Reporter:** {item['reporter_name']}")
                            st.write(f"**Contact:** {item['reporter_contact']}")
                            
                            if item["claim_status"] == "Unclaimed":
                                with st.form(key=f"claim_form_{item['id']}"):
                                    st.markdown("**Submit Claim / Proof**")
                                    c_name = st.text_input("Your Name", key=f"c_name_{item['id']}")
                                    c_contact = st.text_input("Your Phone/Email", key=f"c_contact_{item['id']}")
                                    c_notes = st.text_area("Identifying details / Proof", key=f"c_notes_{item['id']}")
                                    submitted = st.form_submit_button("Submit Claim")
                                    if submitted:
                                        try:
                                            manager.submit_claim(item["id"], c_name, c_contact, c_notes)
                                            st.success("Claim submitted! The reporter will review it.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(str(e))
                            else:
                                st.info(f"Claim Status: {item['claim_status']}")
                                if item["claimant_name"]:
                                    st.write(f"**Claimant:** {item['claimant_name']}")
                    st.markdown("---")
                    
    elif page == "Report Item / Hand-in":
        st.title("📝 Report Lost or Found Item")
        st.markdown("Fill out the details below if you lost something on campus or found an item and handed it in.")
        
        with st.form("report_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Item Title / Name", placeholder="e.g., TI-84 Calculator")
                category = st.selectbox("Category", ["Electronics", "Keys", "ID / Cards", "Books & Notes", "Clothing", "Bags", "Other"])
                status = st.selectbox("Report Type", ["Lost", "Found"])
                location = st.text_input("Location Last Seen / Found", placeholder="e.g., Library 2nd Floor")
            with col2:
                reporter_name = st.text_input("Your Full Name")
                reporter_contact = st.text_input("Your Phone Number or Campus Email")
                date_posted = st.date_input("Date", datetime.date.today())
                
            description = st.text_area("Detailed Description", placeholder="Color, brand, distinguishing marks, serial number, etc.")
            
            submitted = st.form_submit_button("Publish Report")
            if submitted:
                try:
                    item_data = {
                        "title": title,
                        "category": category,
                        "description": description,
                        "location": location,
                        "status": status,
                        "reporter_name": reporter_name,
                        "reporter_contact": reporter_contact,
                        "date_posted": date_posted.isoformat()
                    }
                    manager.add_item(item_data)
                    st.success("Item successfully posted to CampusFind portal!")
                except Exception as e:
                    st.error(f"Error submitting report: {e}")
                    
    elif page == "Admin / Claims Portal":
        st.title("🛠️ Admin & Claim Moderation")
        st.markdown("Review active claims and update item resolution statuses.")
        
        items = manager.get_items()
        pending_items = [i for i in items if i["claim_status"] != "Unclaimed"]
        
        if not pending_items:
            st.info("No pending or resolved claims found in the database.")
        else:
            for item in pending_items:
                with st.container():
                    st.markdown(f"### Item #{item['id']}: {item['title']} ({item['status']})")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Category:** {item['category']}")
                        st.write(f"**Location:** {item['location']}")
                        st.write(f"**Claim State:** `{item['claim_status']}`")
                    with c2:
                        st.write(f"**Claimant:** {item['claimant_name']} ({item['claimant_contact']})")
                        st.write(f"**Proof / Notes:** {item['claim_notes']}")
                        
                    new_state = st.selectbox(
                        "Update Claim Status",
                        ["Unclaimed", "Pending Claim", "Resolved / Returned"],
                        index=["Unclaimed", "Pending Claim", "Resolved / Returned"].index(item["claim_status"]),
                        key=f"status_update_{item['id']}"
                    )
                    if st.button("Save Status", key=f"save_status_{item['id']}"):
                        manager.update_claim_status(item["id"], new_state)
                        st.success(f"Updated item #{item['id']} claim status to {new_state}!")
                        st.rerun()
                    st.markdown("---")

if __name__ == '__main__':
    main()