import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import os
from typing import List, Dict, Any, Optional

DB_FILE = "campus_find.db"

class DatabaseEngine:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                location TEXT NOT NULL,
                date_lost_found TEXT NOT NULL,
                description TEXT,
                contact_info TEXT NOT NULL,
                claim_status TEXT DEFAULT 'Unclaimed',
                claim_details TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        
        # Defensive schema migration: ensure all expected columns exist
        expected_columns = {
            "title": "TEXT NOT NULL DEFAULT ''",
            "category": "TEXT NOT NULL DEFAULT 'Other'",
            "status": "TEXT NOT NULL DEFAULT 'Lost'",
            "location": "TEXT NOT NULL DEFAULT ''",
            "date_lost_found": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT DEFAULT ''",
            "contact_info": "TEXT NOT NULL DEFAULT ''",
            "claim_status": "TEXT DEFAULT 'Unclaimed'",
            "claim_details": "TEXT DEFAULT ''",
            "created_at": "TEXT NOT NULL DEFAULT ''"
        }
        
        cursor.execute("PRAGMA table_info(items)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_def in expected_columns.items():
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_def}")
        
        conn.commit()
        conn.close()

    def add_item(self, data: Dict[str, Any]) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO items (title, category, status, location, date_lost_found, description, contact_info, claim_status, claim_details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("title"),
            data.get("category"),
            data.get("status"),
            data.get("location"),
            data.get("date_lost_found"),
            data.get("description", ""),
            data.get("contact_info"),
            data.get("claim_status", "Unclaimed"),
            data.get("claim_details", ""),
            datetime.now().isoformat()
        ))
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return item_id

    def get_items(self, search: str = "", category: str = "All", status: str = "All", claim_status: str = "All") -> List[Dict[str, Any]]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = "SELECT * FROM items WHERE 1=1"
            params = []

            if search:
                query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
                like_term = f"%{search}%"
                params.extend([like_term, like_term, like_term])

            if category and category != "All":
                query += " AND category = ?"
                params.append(category)

            if status and status != "All":
                query += " AND status = ?"
                params.append(status)

            if claim_status and claim_status != "All":
                query += " AND claim_status = ?"
                params.append(claim_status)

            query += " ORDER BY id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            self.init_db()
            return self.get_items(search, category, status, claim_status)

    def update_claim(self, item_id: int, claim_status: str, claim_details: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE items SET claim_status = ?, claim_details = ? WHERE id = ?
        ''', (claim_status, claim_details, item_id))
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_item(self, item_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def reset_database(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.init_db()


class ItemValidator:
    @staticmethod
    def validate_item_submission(data: Dict[str, Any]) -> List[str]:
        errors = []
        if not data.get("title", "").strip():
            errors.append("Title is required.")
        if not data.get("category", "").strip():
            errors.append("Category is required.")
        if not data.get("location", "").strip():
            errors.append("Location is required.")
        if not data.get("contact_info", "").strip():
            errors.append("Contact Information is required.")
        return errors


def main():
    st.set_page_config(
        page_title="CampusFind — College Lost & Found Portal",
        page_icon="🎒",
        layout="wide"
    )

    db = DatabaseEngine()

    # Sidebar Navigation and DB Management
    st.sidebar.title("🎒 CampusFind")
    st.sidebar.markdown("Find what you lost, return what you found.")
    
    page = st.sidebar.radio("Navigation", ["Browse Portal", "Report Lost/Found Item", "Manage Claims & Items"])

    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Database Settings"):
        if st.button("Reset Database / Wipe All", type="primary"):
            db.reset_database()
            st.success("Database successfully reset!")
            st.rerun()

    categories = ["All", "Electronics", "ID / Cards", "Keys", "Clothing", "Books & Notes", "Bags / Wallets", "Other"]
    statuses = ["All", "Lost", "Found"]
    claim_statuses = ["All", "Unclaimed", "Claim Pending", "Resolved"]

    if page == "Browse Portal":
        st.title("🔍 Campus Lost & Found Portal")
        st.markdown("Search through items reported lost or found across campus.")

        # Metrics row
        all_items = db.get_items()
        total_items = len(all_items)
        lost_count = sum(1 for i in all_items if i['status'] == 'Lost')
        found_count = sum(1 for i in all_items if i['status'] == 'Found')
        resolved_count = sum(1 for i in all_items if i['claim_status'] == 'Resolved')

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Items", total_items)
        col2.metric("Lost Items", lost_count)
        col3.metric("Found Items", found_count)
        col4.metric("Resolved Claims", resolved_count)

        st.markdown("---")

        # Search and Filters
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            search_query = st.text_input("Search keyword", placeholder="e.g. iPhone, Keys...")
        with f_col2:
            sel_category = st.selectbox("Category", categories)
        with f_col3:
            sel_status = st.selectbox("Status", statuses)
        with f_col4:
            sel_claim = st.selectbox("Claim Status", claim_statuses)

        filtered_items = db.get_items(search=search_query, category=sel_category, status=sel_status, claim_status=sel_claim)

        st.markdown(f"### Results ({len(filtered_items)} items found)")

        if not filtered_items:
            st.info("No items match your search criteria.")
        else:
            for item in filtered_items:
                with st.container():
                    badge_color = "orange" if item["status"] == "Lost" else "green"
                    claim_color = "red" if item["claim_status"] == "Unclaimed" else ("blue" if item["claim_status"] == "Claim Pending" else "green")
                    
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"#### {item['title']} :blue-badge[{item['category']}] :orange-badge[{item['status']}] :violet-badge[{item['claim_status']}]")
                        st.write(f"📍 **Location:** {item['location']} | 📅 **Date:** {item['date_lost_found']}")
                        if item["description"]:
                            st.write(f"📝 {item['description']}")
                    with col_b:
                        st.markdown(f"**Contact:** `{item['contact_info']}`")
                        if item["claim_status"] != "Resolved":
                            if st.button(f"Claim / Inquire #{item['id']}", key=f"claim_btn_{item['id']}"):
                                st.session_state[f"claiming_{item['id']}"] = True
                        else:
                            st.success("Resolved ✓")

                    # Claim dialog expansion inline
                    if st.session_state.get(f"claiming_{item['id']}", False):
                        with st.form(key=f"claim_form_{item['id']}"):
                            st.markdown(f"**Submit Claim Details for Item #{item['id']}: {item['title']}**")
                            claimant_info = st.text_input("Your Name & Student ID / Email")
                            proof_details = st.text_area("Provide identifying details / proof of ownership")
                            sub_c1, sub_c2 = st.columns(2)
                            submit_claim = sub_c1.form_submit_button("Submit Claim Request")
                            cancel_claim = sub_c2.form_submit_button("Cancel")

                            if submit_claim:
                                if not claimant_info or not proof_details:
                                    st.error("Please provide both your identity and proof details.")
                                else:
                                    full_claim_info = f"Claimant: {claimant_info} | Proof: {proof_details}"
                                    db.update_claim(item["id"], "Claim Pending", full_claim_info)
                                    st.success("Claim submitted successfully! The finder/admin will review it.")
                                    st.session_state[f"claiming_{item['id']}"] = False
                                    st.rerun()
                            if cancel_claim:
                                st.session_state[f"claiming_{item['id']}"] = False
                                st.rerun()

                    st.divider()

    elif page == "Report Lost/Found Item":
        st.title("📝 Report a Lost or Found Item")
        st.markdown("Fill out the details below to list an item on CampusFind.")

        with st.form("report_form"):
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                title = st.text_input("Item Title / Name*")
                category = st.selectbox("Category", [c for c in categories if c != "All"])
                status = st.selectbox("Status", ["Lost", "Found"])
                date_lost_found = st.date_input("Date Lost / Found", datetime.now())
            with r_col2:
                location = st.text_input("Location (e.g. Library 2nd Floor, Student Union)*")
                contact_info = st.text_input("Contact Info (Email / Phone)*")
                description = st.text_area("Detailed Description (Color, Brand, Unique marks)")

            submitted = st.form_submit_button("Publish Item")

            if submitted:
                item_data = {
                    "title": title,
                    "category": category,
                    "status": status,
                    "location": location,
                    "date_lost_found": str(date_lost_found),
                    "description": description,
                    "contact_info": contact_info
                }
                errors = ItemValidator.validate_item_submission(item_data)
                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    item_id = db.add_item(item_data)
                    st.success(f"Item successfully reported with ID #{item_id}!")

    elif page == "Manage Claims & Items":
        st.title("⚙️ Manage Claims & Status")
        st.markdown("Review pending claims, update item status to resolved, or remove outdated entries.")

        items = db.get_items()
        if not items:
            st.info("No items in the database.")
        else:
            item_options = {f"#{item['id']} - {item['title']} ({item['status']}) [{item['claim_status']}]": item for item in items}
            selected_label = st.selectbox("Select Item to Manage", list(item_options.keys()))
            selected_item = item_options[selected_label]

            st.markdown(f"### Managing Item #{selected_item['id']}: {selected_item['title']}")
            st.write(f"**Category:** {selected_item['category']} | **Status:** {selected_item['status']}")
            st.write(f"**Location:** {selected_item['location']} | **Date:** {selected_item['date_lost_found']}")
            st.write(f"**Contact:** {selected_item['contact_info']}")
            st.write(f"**Description:** {selected_item['description']}")
            st.info(f"**Current Claim Status:** {selected_item['claim_status']}\n\n**Claim Details:** {selected_item['claim_details'] or 'None'}")

            m_col1, m_col2 = st.columns(2)
            with m_col1:
                new_claim_status = st.selectbox("Update Claim Status", ["Unclaimed", "Claim Pending", "Resolved"], index=["Unclaimed", "Claim Pending", "Resolved"].index(selected_item['claim_status']) if selected_item['claim_status'] in ["Unclaimed", "Claim Pending", "Resolved"] else 0)
                update_notes = st.text_input("Claim Resolution Notes", value=selected_item['claim_details'] or "")
                if st.button("Update Claim Status"):
                    db.update_claim(selected_item['id'], new_claim_status, update_notes)
                    st.success("Claim status updated successfully!")
                    st.rerun()

            with m_col2:
                st.markdown("### Danger Zone")
                if st.button("Delete Item", type="primary"):
                    db.delete_item(selected_item['id'])
                    st.success("Item deleted successfully!")
                    st.rerun()


if __name__ == '__main__':
    main()