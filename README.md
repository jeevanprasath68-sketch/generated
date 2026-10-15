# Generated Application

**Requirement:** Build a complete, functional web application called **SpendWise — Student Expense & Budget Manager** using Python and Streamlit.

### Core Features
1. Allow users to add, edit, and delete expenses.
2. Each expense must include amount, category, date, payment method, and description.
3. Support categories such as Food, Transport, Education, Shopping, Entertainment, and Other.
4. Allow users to set a monthly spending budget.
5. Calculate total spending, remaining budget, and category-wise expenses automatically.
6. Display interactive charts for spending by category and monthly spending trends.
7. Include search, filtering by date and category, and sorting by amount.
8. Store data persistently in SQLite so expenses remain available after restarting the application.
9. Provide CSV export functionality.
10. Build a polished, responsive interface with a modern dark theme, sidebar navigation, summary cards, and clear visualisations.

### Technical Requirements
- Use Python, Streamlit, SQLite, Pandas, and Plotly.
- Organise the code into logical modules.
- Validate all user inputs, including positive amounts and valid dates.
- Handle empty datasets and database errors gracefully.
- Never use hardcoded sample results to represent actual user data.

**Status:** VERIFIED

## Run Locally
```bash
streamlit run app.py
```
