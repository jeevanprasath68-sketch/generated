import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from typing import List, Dict, Any, Optional
import re

DB_NAME = "campusfind.db"

class DatabaseManager:
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        conn = self.get_connection()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    location TEXT NOT NULL,
                    date_reported TEXT NOT NULL,
                    contact_info TEXT NOT NULL
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def add_item(self, title: str, description: str, category: str, status: str, location: str, date_reported: str, contact_info: str) -> int:
        if not title.strip() or not description.strip() or not contact_info.strip():
            raise ValueError("Title, description, and contact info cannot be empty.")
        if status not in ["Lost", "Found", "Claimed/Resolved"]:
            raise ValueError("Invalid status specified.")
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO items (title, description, category, status, location, date_reported, contact_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title.strip(), description.strip(), category, status, location.strip(), str(date_reported), contact_info.strip()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_status(self, item_id: int, new_status: str) -> bool:
        if new_status not in ["Lost", "Found", "Claimed/Resolved"]:
            raise ValueError("Invalid status specified.")
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET status = ? WHERE id = ?", (new_status, item_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_item(self, item_id: int) -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all_items(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items ORDER BY date_reported DESC, id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, int]:
        items = self.get_all_items()
        total = len(items)
        unresolved = sum(1 for i in items if i["status"] in ["Lost", "Found"])
        resolved = sum(1 for i in items if i["status"] == "Claimed/Resolved")
        return {
            "total": total,
            "unresolved": unresolved,
            "resolved": resolved
        }

class MatchingEngine:
    @staticmethod
    def calculate_match_score(item_a: Dict[str, Any], item_b: Dict[str, Any]) -> float:
        if item_a["status"] == item_b["status"]:
            return 0.0
        
        score = 0.0
        
        if item_a["category"].lower() == item_b["category"].lower():
            score += 40.0
            
        loc_a = item_a["location"].lower()
        loc_b = item_b["location"].lower()
        if loc_a == loc_b or loc_a in loc_b or loc_b in loc_a:
            score += 30.0
            
        words_a = set(re.findall(r'\w+', (item_a["title"] + " " + item_a["description"]).lower()))
        words_b = set(re.findall(r'\w+', (item_b["title"] + " " + item_b["description"]).lower()))
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'with', 'my', 'is', 'lost', 'found'}
        words_a -= stop_words
        words_b -= stop_words
        
        if words_a and words_b:
            intersection = words_a.intersection(words_b)
            union = words_a.union(words_b)
            jaccard = len(intersection) / len(union)
            score += jaccard * 30.0
            
        return round(score, 2)

    @classmethod
    def find_potential_matches(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        matches = []
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a = items[i]
                item_b = items[j]
                score = cls.calculate_match_score(item_a, item_b)
                if score >= 35.0:
                    matches.append({
                        "item_1": item_a,
                        "item_2": item_b,
                        "score": score
                    })
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches

CATEGORIES = ["Electronics", "Keys", "ID / Cards", "Clothing", "Books & Notes", "Bags & Wallets", "Water Bottles", "Other"]
LOCATIONS = ["Library", "Student Union", "Science Block", "Engineering Hall", "Dining Commons", "Sports Complex", "Lecture Hall A", "Campus Quad", "Other"]

def main():
    st.set_page_config(page_title="CampusFind Portal", page_icon="🎓", layout="wide")
    
    db = DatabaseManager()
    
    st.title("🎓 CampusFind — College Lost & Found Portal")
    st.markdown("Welcome to the official campus hub for reporting, tracking, and reuniting lost belongings.")
    
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard & Feed", "Report New Item", "Smart Matching", "Manage Records"])
    
    stats = db.get_statistics()
    
    if page == "Dashboard & Feed":
        st.header("📊 Campus Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reports", stats["total"])
        col2.metric("Unresolved Cases", stats["unresolved"], delta_color="inverse")
        col3.metric("Resolved / Claimed", stats["resolved"], delta=stats["resolved"])
        
        st.divider()
        
        st.subheader("🔍 Search & Filter Items")
        all_items = db.get_all_items()
        
        search_query = st.text_input("Search by keyword in title or description:", "")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            cat_filter = st.selectbox("Filter by Category", ["All"] + CATEGORIES)
        with col_f2:
            loc_filter = st.selectbox("Filter by Location", ["All"] + LOCATIONS)
        with col_f3:
            status_filter = st.selectbox("Filter by Status", ["All", "Lost", "Found", "Claimed/Resolved"])
            
        filtered_items = []
        for item in all_items:
            if search_query:
                q = search_query.lower()
                if q not in item["title"].lower() and q not in item["description"].lower():
                    continue
            if cat_filter != "All" and item["category"] != cat_filter:
                continue
            if loc_filter != "All" and item["location"] != loc_filter:
                continue
            if status_filter != "All" and item["status"] != status_filter:
                continue
            filtered_items.append(item)
            
        st.markdown(f"### Showing {len(filtered_items)} item(s)")
        
        if not filtered_items:
            st.info("No items found matching your criteria.")
        else:
            cols_per_row = 2
            for i in range(0, len(filtered_items), cols_per_row):
                row_cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(filtered_items):
                        item = filtered_items[i + j]
                        with row_cols[j]:
                            status_color = "🔴" if item["status"] == "Lost" else ("🟢" if item["status"] == "Found" else "🔵")
                            with st.container(border=True):
                                st.markdown(f"#### {status_color} {item['title']}")
                                st.caption(f"**Category:** {item['category']} | **Location:** {item['location']}")
                                st.write(item["description"])
                                st.markdown(f"**Date:** {item['date_reported']} | **Status:** `{item['status']}`")
                                st.markdown(f"📞 **Contact:** {item['contact_info']}")
                                
                                if item["status"] != "Claimed/Resolved":
                                    if st.button(f"Mark Resolved #{item['id']}", key=f"card_res_{item['id']}"):
                                        db.update_status(item["id"], "Claimed/Resolved")
                                        st.success(f"Item #{item['id']} marked as resolved!")
                                        st.rerun()

    elif page == "Report New Item":
        st.header("📝 Report a Lost or Found Item")
        with st.form("report_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Item Title / Name *", placeholder="e.g., Blue Hydro Flask")
                category = st.selectbox("Category", CATEGORIES)
                status = st.selectbox("Status", ["Lost", "Found"])
                date_reported = st.date_input("Date", date.today())
            with col2:
                location = st.selectbox("Campus Location", LOCATIONS)
                contact_info = st.text_input("Contact Info (Email / Phone) *", placeholder="student@campus.edu")
                description = st.text_area("Detailed Description *", placeholder="Include distinguishing marks, brand, color, etc.")
                
            submitted = st.form_submit_button("Submit Report")
            if submitted:
                try:
                    new_id = db.add_item(title, description, category, status, location, str(date_reported), contact_info)
                    st.success(f"Item successfully reported with ID #{new_id}!")
                    st.balloons()
                except ValueError as e:
                    st.error(str(e))

    elif page == "Smart Matching":
        st.header("🤖 Smart Match Suggestions")
        st.markdown("Our algorithm automatically analyzes lost and found reports to suggest potential matches based on category, location proximity, and keyword text overlap.")
        
        all_items = db.get_all_items()
        matches = MatchingEngine.find_potential_matches(all_items)
        
        if not matches:
            st.info("No high-confidence matches found yet. Check back when more items are reported!")
        else:
            st.success(f"Found {len(matches)} potential match pair(s)!")
            for idx, match in enumerate(matches):
                item1 = match["item_1"]
                item2 = match["item_2"]
                score = match["score"]
                
                with st.expander(f"Match #{idx+1}: Confidence Score: {score}% ({item1['title']} ↔ {item2['title']})"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"### 🔴 Item A ({item1['status']})")
                        st.write(f"**Title:** {item1['title']}")
                        st.write(f"**Category:** {item1['category']}")
                        st.write(f"**Location:** {item1['location']}")
                        st.write(f"**Description:** {item1['description']}")
                        st.write(f"**Contact:** {item1['contact_info']}")
                    with col_b:
                        st.markdown(f"### 🟢 Item B ({item2['status']})")
                        st.write(f"**Title:** {item2['title']}")
                        st.write(f"**Category:** {item2['category']}")
                        st.write(f"**Location:** {item2['location']}")
                        st.write(f"**Description:** {item2['description']}")
                        st.write(f"**Contact:** {item2['contact_info']}")
                        
                    if st.button(f"Resolve Both Items (Match #{idx+1})", key=f"match_resolve_{idx}"):
                        db.update_status(item1["id"], "Claimed/Resolved")
                        db.update_status(item2["id"], "Claimed/Resolved")
                        st.success("Both items successfully marked as resolved!")
                        st.rerun()

    elif page == "Manage Records":
        st.header("⚙️ Manage All Records")
        st.markdown("View complete database records, update statuses, delete erroneous entries, or export to CSV.")
        
        all_items = db.get_all_items()
        if not all_items:
            st.info("No records in the database.")
        else:
            df = pd.DataFrame(all_items)
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Records as CSV",
                data=csv_data,
                file_name="campusfind_records.csv",
                mime="text/csv"
            )
            
            st.divider()
            st.subheader("Update Status or Delete Item")
            
            item_options = {f"#{i['id']} - {i['title']} ({i['status']})": i['id'] for i in all_items}
            selected_label = st.selectbox("Select Item", list(item_options.keys()))
            selected_id = item_options[selected_label]
            
            col_upd1, col_upd2 = st.columns(2)
            with col_upd1:
                new_stat = st.selectbox("New Status", ["Lost", "Found", "Claimed/Resolved"])
                if st.button("Update Status"):
                    db.update_status(selected_id, new_stat)
                    st.success(f"Item #{selected_id} status updated to {new_stat}!")
                    st.rerun()
            with col_upd2:
                st.markdown("&nbsp;")
                if st.button("🗑️ Delete Record", type="primary"):
                    db.delete_item(selected_id)
                    st.success(f"Item #{selected_id} deleted successfully!")
                    st.rerun()

if __name__ == '__main__':
    main()