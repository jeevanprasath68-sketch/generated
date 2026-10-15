# Generated Application

**Requirement:** Build a functional web application called **CampusFind — College Lost & Found Portal** using Python and Streamlit.

Features:
- Register lost and found items with name, description, category, location, date, and contact information.
- Display items as searchable cards.
- Filter by item category, campus location, date, and lost/found status.
- Allow users to report an item as claimed or resolved.
- Store records in SQLite with persistent storage.
- Provide a dashboard showing total reports, unresolved cases, and successful matches.
- Implement a basic matching algorithm that suggests potentially matching lost and found reports using item category, keywords, and location.
- Include input validation, duplicate prevention, and CSV export.
- Create a polished interface with a modern design and responsive layout.

Testing requirements:
- Test item creation, editing, deletion, and status changes.
- Test search, filtering, and matching behaviour.
- Test invalid inputs and empty results.
- Verify database persistence.

Generate the complete application, run actual automated tests, diagnose failures, attempt up to two repairs, and rerun tests. Report genuine results without fabricating successful tests. Clearly document any unimplemented functionality.

Do not build only a static interface. The application must work end to end.

**Format:** Streamlit Web App

**Status:** VERIFIED

## How to Run Locally
```bash
streamlit run app.py
```
