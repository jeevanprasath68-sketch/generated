import sqlite3
import datetime
from typing import List, Dict, Any, Optional
import streamlit as st

# ==========================================
# BUSINESS LOGIC & DATA ENGINE
# ==========================================

class CampusDatabase:
    def __init__(self, db_path: str = "campusfind.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    location TEXT NOT NULL,
                    date_reported TEXT NOT NULL,
                    reporter_name TEXT NOT NULL,
                    reporter_contact TEXT NOT NULL,
                    claim_status TEXT DEFAULT 'Unclaimed',
                    claim_notes TEXT DEFAULT ''
                )
                """
            )
            # Self-healing schema migration: add any missing columns if migrating an older database
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(items)")
            columns = [row[1] for row in cursor.fetchall()]
            if "claim_status" not in columns:
                cursor.execute("ALTER TABLE items ADD COLUMN claim_status TEXT DEFAULT 'Unclaimed'")
            if "claim_notes" not in columns:
                cursor.execute("ALTER TABLE items ADD COLUMN claim_notes TEXT DEFAULT ''")
            conn.commit()

    def reset_db(self) -> None:
        """Wipes all data and re-initializes fresh tables."""
        with self._get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS items")
            conn.commit()
        self._init_db()

    def add_item(self, data: Dict[str, Any]) -> int:
        required_fields = ['title', 'description', 'category', 'status', 'location', 'reporter_name', 'reporter_contact']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Missing required field: {field}")

        date_reported = data.get('date_reported', datetime.date.today().isoformat())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO items (title, description, category, status, location, date_reported, reporter_name, reporter_contact, claim_status, claim_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Unclaimed', '')
                """,
                (
                    data['title'],
                    data['description'],
                    data['category'],
                    data['status'],
                    data['location'],
                    date_reported,
                    data['reporter_name'],
                    data['reporter_contact']
                )
            )
            conn.commit()
            return cursor.lastrowid

    def get_items(self, search_query: str = "", category: str = "All", status: str = "All") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM items WHERE 1=1"
            params = []

            if search_query:
                query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
                like_term = f"%{search_query}%"
                params.extend([like_term, like_term, like_term])

            if category != "All":
                query += " AND category = ?"
                params.append(category)

            if status != "All":
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY date_reported DESC, id DESC"
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_claim(self, item_id: int, claim_status: str, claim_notes: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE items SET claim_status = ?, claim_notes = ? WHERE id = ?
                """,
                (claim_status, claim_notes, item_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            try:
                total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
                lost = conn.execute("SELECT COUNT(*) FROM items WHERE status='Lost'").fetchone()[0]
                found = conn.execute("SELECT COUNT(*) FROM items WHERE status='Found'").fetchone()[0]
                claimed = conn.execute("SELECT COUNT(*) FROM items WHERE claim_status='Claimed'").fetchone()[0]
            except sqlite3.OperationalError:
                # Self-heal schema if missing columns or tables
                self._init_db()
                total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
                lost = conn.execute("SELECT COUNT(*) FROM items WHERE status='Lost'").fetchone()[0]
                found = conn.execute("SELECT COUNT(*) FROM items WHERE status='Found'").fetchone()[0]
                claimed = conn.execute("SELECT COUNT(*) FROM items WHERE claim_status='Claimed'").fetchone()[0]
            return {
                "total": total,
                "lost": lost,
                "found": found,
                "claimed": claimed
            }

# ==========================================
# STREAMLIT USER INTERFACE
# ==========================================

def main():
    st.set_page_config(
        page_title="CampusFind - Lost & Found",
        page_icon="🎒",
        layout="wide"
    )

    db = CampusDatabase()

    # App Header
    st.title("🎒 CampusFind — College Lost & Found Portal")
    st.markdown("Welcome to the central hub for reporting, searching, and claiming lost items on campus.")

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ["Browse & Search", "Report Item", "Manage Claims / Status", "Dashboard Stats"])

    st.sidebar.divider()
    with st.sidebar.expander("⚙️ Database Management"):
        st.caption("Clear stale test data or re-initialize a fresh database.")
        if st.sidebar.button("🗑️ Reset Database / Clear All Data", use_container_width=True):
            db.reset_db()
            st.sidebar.success("Database wiped & schema re-initialized!")
            st.rerun()

    CATEGORIES = ["All", "Electronics", "Books & Notes", "ID & Cards", "Clothing", "Keys", "Bags", "Other"]
    STATUSES = ["All", "Lost", "Found"]

    if choice == "Browse & Search":
        st.header("🔍 Browse & Search Lost/Found Items")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_query = st.text_input("Search keywords", placeholder="e.g., iPhone, Calculator, Library...")
        with col2:
            selected_category = st.selectbox("Category", CATEGORIES)
        with col3:
            selected_status = st.selectbox("Item Status", STATUSES)

        items = db.get_items(search_query=search_query, category=selected_category, status=selected_status)

        st.markdown(f"**Found {len(items)} matching item(s)**")
        st.divider()

        if not items:
            st.info("No items found matching your criteria.")
        else:
            for item in items:
                with st.container():
                    cols = st.columns([3, 1, 1])
                    with cols[0]:
                        badge = "🔴 Lost" if item['status'] == 'Lost' else "🟢 Found"
                        st.subheader(f"{badge}: {item['title']}")
                        st.write(f"**Description:** {item['description']}")
                        st.write(f"📍 **Location:** {item['location']} | 🏷️ **Category:** {item['category']} | 📅 **Date:** {item['date_reported']}")
                    with cols[1]:
                        st.write(f"**Reporter:**\n{item['reporter_name']}\n{item['reporter_contact']}")
                    with cols[2]:
                        claim_badge = f"📌 {item['claim_status']}"
                        st.markdown(f"**Claim Status:**\n{claim_badge}")
                        if item['claim_notes']:
                            st.caption(f"Notes: {item['claim_notes']}")
                    st.divider()

    elif choice == "Report Item":
        st.header("📢 Report a Lost or Found Item")
        st.markdown("Please fill out the form accurately to help community members reconnect with their belongings.")

        with st.form("report_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Item Title*", placeholder="e.g., Blue Hydro Flask")
                category = st.selectbox("Category", [c for c in CATEGORIES if c != "All"])
                status = st.selectbox("Status", ["Lost", "Found"])
                location = st.text_input("Location (Lost or Found)*", placeholder="e.g., Student Union 2nd Floor")
            
            with col2:
                reporter_name = st.text_input("Your Name*", placeholder="e.g., Jane Doe")
                reporter_contact = st.text_input("Your Email / Phone*", placeholder="e.g., jane@college.edu")
                date_reported = st.date_input("Date", datetime.date.today())
                description = st.text_area("Detailed Description*", placeholder="Color, brand, distinguishing marks...")

            submitted = st.form_submit_button("Submit Report")

            if submitted:
                try:
                    item_data = {
                        "title": title,
                        "description": description,
                        "category": category,
                        "status": status,
                        "location": location,
                        "date_reported": date_reported.isoformat(),
                        "reporter_name": reporter_name,
                        "reporter_contact": reporter_contact
                    }
                    db.add_item(item_data)
                    st.success("✅ Item successfully reported and saved to database!")
                except ValueError as e:
                    st.error(f"❌ Error: {e}")

    elif choice == "Manage Claims / Status":
        st.header("🛠️ Manage Claim Status")
        st.markdown("Update the claim status of items as they are returned to their owners.")

        items = db.get_items()
        if not items:
            st.info("No items available in the system to manage.")
        else:
            item_options = {f"{i['id']}: {i['title']} ({i['status']})": i['id'] for i in items}
            selected_option = st.selectbox("Select Item", list(item_options.keys()))
            selected_id = item_options[selected_option]

            current_item = next(i for i in items if i['id'] == selected_id)

            with st.form("claim_form"):
                st.write(f"**Current Claim Status:** {current_item['claim_status']}")
                new_claim_status = st.selectbox("Update Claim Status", ["Unclaimed", "Pending Verification", "Claimed"])
                new_claim_notes = st.text_area("Claim Notes / Handover Details", value=current_item['claim_notes'])
                update_submitted = st.form_submit_button("Update Status")

                if update_submitted:
                    db.update_claim(selected_id, new_claim_status, new_claim_notes)
                    st.success("✅ Claim status successfully updated!")
                    st.rerun()

    elif choice == "Dashboard Stats":
        st.header("📊 Portal Analytics & Summary")
        stats = db.get_stats()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Items", stats["total"])
        col2.metric("Lost Items Reported", stats["lost"])
        col3.metric("Found Items Reported", stats["found"])
        col4.metric("Successfully Claimed", stats["claimed"])

        st.divider()
        st.markdown("### Quick Guidelines")
        st.markdown("""
        - **Lost an Item?** File a report immediately with detailed identifiers.
        - **Found an Item?** Drop it off at Campus Security or Student Services, and report it here.
        - **Claiming:** Provide proof of ownership (student ID, serial number) when contacting the reporter or administrator.
        """)

if __name__ == '__main__':
    main()