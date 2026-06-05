import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# Optional PDF support
try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# =====================================================
# Page Config
# =====================================================
st.set_page_config(
    page_title="FIRE Dashboard",
    page_icon="🔥",
    layout="wide"
)


# =====================================================
# Helper Functions
# =====================================================
def money(currency, value):
    try:
        return f"{currency}{float(value):,.2f}"
    except Exception:
        return f"{currency}0.00"


def calculate_fire_number(annual_expenses, withdrawal_rate):
    if withdrawal_rate <= 0:
        return 0
    return annual_expenses / withdrawal_rate


def calculate_years_to_fire(current_net_worth, fire_number, annual_investment, annual_return):
    if fire_number <= 0:
        return np.inf

    if current_net_worth >= fire_number:
        return 0

    if annual_investment <= 0:
        return np.inf

    years = 0
    net_worth = current_net_worth

    while net_worth < fire_number and years < 100:
        net_worth = net_worth * (1 + annual_return) + annual_investment
        years += 1

    return years


def fire_score(savings_rate, years_to_fire, emergency_months, debt_ratio):
    score = 0

    # Savings rate: max 40 points
    if savings_rate >= 50:
        score += 40
    elif savings_rate >= 30:
        score += 30
    elif savings_rate >= 20:
        score += 20
    elif savings_rate >= 10:
        score += 10

    # Years to FIRE: max 30 points
    if years_to_fire <= 5:
        score += 30
    elif years_to_fire <= 10:
        score += 25
    elif years_to_fire <= 15:
        score += 18
    elif years_to_fire <= 20:
        score += 10
    else:
        score += 5

    # Emergency fund: max 20 points
    if emergency_months >= 12:
        score += 20
    elif emergency_months >= 6:
        score += 15
    elif emergency_months >= 3:
        score += 10
    else:
        score += 5

    # Debt ratio: max 10 points
    if debt_ratio <= 10:
        score += 10
    elif debt_ratio <= 30:
        score += 7
    elif debt_ratio <= 50:
        score += 4
    else:
        score += 1

    return min(score, 100)


def fire_level(score):
    if score >= 85:
        return "Excellent 🔥🔥🔥"
    elif score >= 70:
        return "Good 🔥🔥"
    elif score >= 50:
        return "Average 🔥"
    return "Needs Improvement"


def clean_amount(value):
    """
    Converts values like RM1,234.50, (123.45), -123.45 into float.
    """
    if pd.isna(value):
        return 0.0

    text = str(value).strip()
    text = text.replace("RM", "").replace("MYR", "").replace(",", "")

    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]

    text = re.sub(r"[^0-9.\-]", "", text)

    try:
        return float(text)
    except Exception:
        return 0.0


def categorize_expense(description):
    desc = str(description).lower()

    rules = {
        "Food & Drinks": [
            "grab", "foodpanda", "mcd", "mcdonald", "kfc", "starbucks",
            "coffee", "restaurant", "cafe", "kopitiam", "tealive",
            "oldtown", "secret recipe", "sushi", "pizza", "domino",
            "burger", "nasi", "bakery", "chicken", "boost juice"
        ],
        "Transport": [
            "shell", "petronas", "caltex", "bhp", "petrol", "tng",
            "touch n go", "parking", "grabcar", "airasia ride",
            "rapidkl", "mrt", "lrt", "toll", "rfid", "setel"
        ],
        "Subscriptions": [
            "netflix", "spotify", "youtube", "icloud", "google",
            "microsoft", "disney", "subscription", "apple.com",
            "chatgpt", "openai", "canva", "notion"
        ],
        "Shopping": [
            "shopee", "lazada", "zalora", "uniqlo", "h&m", "hm",
            "mr diy", "decathlon", "ikea", "fashion", "nike",
            "adidas", "watsons online", "tiktok shop"
        ],
        "Groceries": [
            "aeon", "tesco", "lotus", "jaya grocer", "village grocer",
            "giant", "mydin", "grocer", "grocery", "supermarket",
            "cold storage", "ns k", "99 speedmart"
        ],
        "Utilities": [
            "tnb", "syabas", "water", "maxis", "celcom", "digi",
            "u mobile", "unifi", "time internet", "astro",
            "telekom", "wifi", "internet"
        ],
        "Medical": [
            "watsons", "guardian", "clinic", "hospital", "pharmacy",
            "dental", "doctor", "medical", "health"
        ],
        "Travel": [
            "airasia", "malaysia airlines", "agoda", "booking.com",
            "hotel", "travel", "klook", "trip.com", "expedia"
        ],
        "Insurance": [
            "insurance", "aia", "prudential", "great eastern",
            "allianz", "etiqa", "zurich", "tokio marine"
        ],
        "Education": [
            "school", "tuition", "book", "education", "course",
            "udemy", "coursera"
        ],
        "Fitness": [
            "gym", "fitness", "sport", "sports", "yoga"
        ]
    }

    for category, keywords in rules.items():
        if any(keyword in desc for keyword in keywords):
            return category

    return "Others"


def read_pdf_to_dataframe(pdf_file):
    """
    Reads selectable-table PDF statements.
    Scanned/image PDF may not work.
    """
    if pdfplumber is None:
        st.error("pdfplumber is not installed. Run: pip install pdfplumber")
        return pd.DataFrame()

    all_rows = []

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        all_rows.append(row)

        if not all_rows:
            return pd.DataFrame()

        return pd.DataFrame(all_rows)

    except Exception as e:
        st.error(f"PDF reading error: {e}")
        return pd.DataFrame()


def standardize_uploaded_data(df):
    """
    Converts many bank formats into:
    Date, Description, Amount
    """
    df = df.copy()
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    df.columns = [str(col).strip() for col in df.columns]

    # PDF tables often have numeric column headers. Try first row as header.
    if all(str(col).isdigit() for col in df.columns):
        if len(df) > 1:
            df.columns = df.iloc[0].astype(str).str.strip()
            df = df.iloc[1:].reset_index(drop=True)

    lower_cols = {str(col).lower().strip(): col for col in df.columns}

    date_candidates = [
        "date", "transaction date", "posting date", "posted date",
        "txn date", "trans date"
    ]

    description_candidates = [
        "description", "merchant", "merchant name", "transaction description",
        "details", "particulars", "narrative", "transaction details"
    ]

    amount_candidates = [
        "amount", "transaction amount", "debit", "charge", "charges",
        "billing amount", "myr amount", "withdrawal", "spent"
    ]

    date_col = next((lower_cols[c] for c in date_candidates if c in lower_cols), None)
    desc_col = next((lower_cols[c] for c in description_candidates if c in lower_cols), None)
    amount_col = next((lower_cols[c] for c in amount_candidates if c in lower_cols), None)

    with st.expander("Column detection"):
        st.write({
            "Date": date_col,
            "Description": desc_col,
            "Amount": amount_col
        })

    if date_col is None or desc_col is None or amount_col is None:
        st.warning("Please map your statement columns manually.")

        columns = list(df.columns)

        date_col = st.selectbox("Select Date column", columns)
        desc_col = st.selectbox("Select Description column", columns)
        amount_col = st.selectbox("Select Amount column", columns)

    clean_df = pd.DataFrame()
    clean_df["Date"] = df[date_col]
    clean_df["Description"] = df[desc_col].astype(str)
    clean_df["Amount"] = df[amount_col].apply(clean_amount)

    clean_df = clean_df[clean_df["Amount"] != 0]
    clean_df["Amount"] = clean_df["Amount"].abs()
    clean_df["Date"] = pd.to_datetime(clean_df["Date"], errors="coerce")

    return clean_df


def rule_based_assistant(
    currency,
    monthly_income,
    monthly_expenses,
    monthly_savings,
    savings_rate,
    current_net_worth,
    fire_number,
    years_to_fire,
    emergency_fund,
    emergency_months,
    monthly_debt_payment,
    debt_ratio,
    score,
    level,
    category_summary,
    top_transactions
):
    """
    Free built-in assistant. No API. No AI cost.
    Generates practical suggestions from rules and calculations.
    """
    observations = []
    actions = []
    warnings = []
    strengths = []

    # Savings rate
    if savings_rate >= 50:
        strengths.append(f"Your savings rate is very strong at {savings_rate:.1f}%. This is excellent for FIRE progress.")
    elif savings_rate >= 30:
        strengths.append(f"Your savings rate is good at {savings_rate:.1f}%. You are building a strong FIRE base.")
    elif savings_rate >= 20:
        observations.append(f"Your savings rate is {savings_rate:.1f}%. This is decent, but improving it can reduce your FIRE timeline.")
        actions.append("Try to increase savings rate toward 30% by reducing flexible spending.")
    else:
        warnings.append(f"Your savings rate is only {savings_rate:.1f}%. FIRE progress may be slow.")
        actions.append("Focus first on raising savings rate to at least 20%.")

    # Emergency fund
    if emergency_months >= 6:
        strengths.append(f"Your emergency fund covers about {emergency_months:.1f} months, which is healthy.")
    elif emergency_months >= 3:
        observations.append(f"Your emergency fund covers about {emergency_months:.1f} months. It is acceptable but can be stronger.")
        actions.append("Build emergency fund toward 6 months of expenses before taking more investment risk.")
    else:
        warnings.append(f"Your emergency fund covers only {emergency_months:.1f} months.")
        actions.append("Build emergency fund to at least 3 months first, then 6 months.")

    # Debt ratio
    if debt_ratio <= 10:
        strengths.append(f"Your debt payment ratio is low at {debt_ratio:.1f}%.")
    elif debt_ratio <= 30:
        observations.append(f"Your debt payment ratio is {debt_ratio:.1f}%. It is manageable, but should be monitored.")
        actions.append("Avoid adding new lifestyle debt while improving savings.")
    else:
        warnings.append(f"Your debt payment ratio is high at {debt_ratio:.1f}%.")
        actions.append("Prioritize reducing high-interest debt before increasing discretionary spending.")

    # FIRE timeline
    if years_to_fire == np.inf:
        warnings.append("Based on current savings, FIRE is not reachable in the projection because annual savings is not positive.")
        actions.append("Increase income, reduce expenses, or both, until monthly savings becomes positive.")
    elif years_to_fire <= 10:
        strengths.append(f"Your estimated FIRE timeline is around {years_to_fire} years, which is strong.")
    elif years_to_fire <= 20:
        observations.append(f"Your estimated FIRE timeline is around {years_to_fire} years.")
        actions.append("Every extra monthly saving can shorten your FIRE timeline.")
    else:
        observations.append(f"Your FIRE timeline is quite long at around {years_to_fire} years.")
        actions.append("Target higher monthly savings and review your largest expenses.")

    # Category analysis
    possible_saving = 0
    saving_details = []

    if category_summary is not None and not category_summary.empty:
        total_card_spending = category_summary["Amount"].sum()
        top_category = category_summary.iloc[0]["Category"]
        top_amount = category_summary.iloc[0]["Amount"]
        top_pct = top_amount / total_card_spending * 100 if total_card_spending > 0 else 0

        observations.append(
            f"Your highest credit card category is {top_category}, at {money(currency, top_amount)} "
            f"or about {top_pct:.1f}% of uploaded card spending."
        )

        flexible_categories = ["Food & Drinks", "Shopping", "Travel", "Subscriptions", "Others"]
        flexible_df = category_summary[category_summary["Category"].isin(flexible_categories)]

        if not flexible_df.empty:
            flexible_spending = flexible_df["Amount"].sum()
            possible_saving = flexible_spending * 0.15

            actions.append(
                f"If you reduce flexible categories by 15%, you may save about {money(currency, possible_saving)} per month."
            )

            for _, row in flexible_df.iterrows():
                category = row["Category"]
                amount = row["Amount"]
                saving = amount * 0.15
                saving_details.append(
                    f"- Reduce {category} by 15%: possible saving {money(currency, saving)}"
                )

        if top_category in ["Food & Drinks", "Shopping", "Travel", "Subscriptions", "Others"]:
            actions.append(f"Start with {top_category}, because it is your biggest flexible spending category.")

    # Top transactions
    if top_transactions is not None and not top_transactions.empty:
        biggest = top_transactions.iloc[0]
        observations.append(
            f"Your largest single transaction is {money(currency, biggest['Amount'])}: {biggest['Description']}."
        )

    # FIRE score comment
    if score >= 85:
        final_view = "You are in a very strong FIRE position. The focus should be consistency and risk control."
    elif score >= 70:
        final_view = "You are in a good FIRE position. A few improvements can make the plan stronger."
    elif score >= 50:
        final_view = "You are in an average FIRE position. The biggest improvement should come from savings rate and expense control."
    else:
        final_view = "Your FIRE position needs improvement. Focus on cash flow, emergency fund, and debt control first."

    result = {
        "final_view": final_view,
        "strengths": strengths,
        "observations": observations,
        "warnings": warnings,
        "actions": actions,
        "saving_details": saving_details,
        "possible_saving": possible_saving
    }

    return result


def display_rule_based_reply(reply):
    st.subheader("Financial Assistant Reply")

    st.write(f"**Overall view:** {reply['final_view']}")

    if reply["strengths"]:
        st.success("Strengths")
        for item in reply["strengths"]:
            st.write(f"- {item}")

    if reply["observations"]:
        st.info("Key observations")
        for item in reply["observations"]:
            st.write(f"- {item}")

    if reply["warnings"]:
        st.warning("Things to improve")
        for item in reply["warnings"]:
            st.write(f"- {item}")

    if reply["actions"]:
        st.subheader("Suggested actions")
        for item in reply["actions"]:
            st.write(f"- {item}")

    if reply["saving_details"]:
        st.subheader("Possible saving breakdown")
        for item in reply["saving_details"]:
            st.write(item)


# =====================================================
# Sidebar Inputs
# =====================================================
st.sidebar.title("🔥 FIRE Inputs")

st.sidebar.caption(
    "Demo values use general Malaysia-style example numbers. Replace them with your own figures."
)

currency = st.sidebar.selectbox(
    "Currency",
    ["RM", "$", "SGD"],
    index=0
)

monthly_income = st.sidebar.number_input(
    "Monthly income",
    min_value=3200.0,
    value=3200.0,
    step=100.0
)

monthly_expenses = st.sidebar.number_input(
    "Monthly expenses",
    min_value=2400.0,
    value=2400.0,
    step=100.0
)

current_net_worth = st.sidebar.number_input(
    "Current net worth / investment portfolio",
    min_value=20000.0,
    value=20000.0,
    step=1000.0
)

emergency_fund = st.sidebar.number_input(
    "Emergency fund amount",
    min_value=6000.0,
    value=6000.0,
    step=500.0
)

monthly_debt_payment = st.sidebar.number_input(
    "Monthly debt payment",
    min_value=500.0,
    value=500.0,
    step=100.0
)

annual_return_percent = st.sidebar.slider(
    "Expected annual investment return (%)",
    min_value=0.0,
    max_value=15.0,
    value=6.0,
    step=0.5
)

withdrawal_rate_percent = st.sidebar.slider(
    "Safe withdrawal rate (%)",
    min_value=2.0,
    max_value=6.0,
    value=4.0,
    step=0.1
)


# =====================================================
# FIRE Calculations
# =====================================================
annual_income = monthly_income * 12
annual_expenses = monthly_expenses * 12
monthly_savings = monthly_income - monthly_expenses
annual_savings = monthly_savings * 12

savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0
debt_ratio = (monthly_debt_payment / monthly_income * 100) if monthly_income > 0 else 0
emergency_months = emergency_fund / monthly_expenses if monthly_expenses > 0 else 0

annual_return = annual_return_percent / 100
withdrawal_rate = withdrawal_rate_percent / 100

fire_number = calculate_fire_number(annual_expenses, withdrawal_rate)

years_to_fire = calculate_years_to_fire(
    current_net_worth,
    fire_number,
    annual_savings,
    annual_return
)

score = fire_score(
    savings_rate,
    years_to_fire if years_to_fire != np.inf else 999,
    emergency_months,
    debt_ratio
)

level = fire_level(score)


# =====================================================
# Main Dashboard
# =====================================================
st.title("🔥 FIRE Dashboard")

st.caption(
    "Example values are based on general Malaysia salary ranges. Replace them with your own numbers for personal planning."
)

st.write(
    "Track your income, expenses, FIRE progress, credit card spending, and saving opportunities."
)

with st.expander("Privacy reminder before uploading statements"):
    st.write(
        "Before uploading a credit card or bank statement, remove sensitive information such as full card number, "
        "IC/passport number, address, phone number, email, bank account number, passwords, and security codes. "
        "This app processes uploads for analysis and does not intentionally save uploaded statements."
    )

col1, col2, col3, col4 = st.columns(4)

col1.metric("Monthly Income", money(currency, monthly_income))
col2.metric("Monthly Expenses", money(currency, monthly_expenses))
col3.metric("Monthly Savings", money(currency, monthly_savings))
col4.metric("Savings Rate", f"{savings_rate:.1f}%")

col5, col6, col7, col8 = st.columns(4)

col5.metric("FIRE Number", money(currency, fire_number))
col6.metric("Current Net Worth", money(currency, current_net_worth))

if years_to_fire == np.inf:
    col7.metric("Years to FIRE", "Not reachable")
else:
    col7.metric("Years to FIRE", f"{years_to_fire} years")

col8.metric("FIRE Score", f"{score}/100", level)


# =====================================================
# FIRE Progress
# =====================================================
st.subheader("🔥 FIRE Progress")

progress = min(current_net_worth / fire_number, 1) if fire_number > 0 else 0
st.progress(progress)
st.write(f"You are currently at **{progress * 100:.1f}%** of your FIRE target.")


# =====================================================
# Income vs Expense Chart
# =====================================================
st.subheader("Income vs Expenses")

income_expense_df = pd.DataFrame({
    "Type": ["Income", "Expenses", "Savings"],
    "Amount": [monthly_income, monthly_expenses, monthly_savings]
})

fig = px.bar(
    income_expense_df,
    x="Type",
    y="Amount",
    text="Amount",
    title="Monthly Income vs Expenses vs Savings"
)

fig.update_traces(
    texttemplate=f"{currency}%{{text:,.0f}}",
    textposition="outside"
)

st.plotly_chart(fig, use_container_width=True)


# =====================================================
# Manual Expense Breakdown
# =====================================================
st.subheader("Manual Monthly Expense Breakdown")

manual_col1, manual_col2 = st.columns(2)

with manual_col1:
    housing = st.number_input("Housing / Rent", min_value=800.0, value=800.0, step=50.0)
    food = st.number_input("Food & Groceries", min_value=700.0, value=700.0, step=50.0)
    transport = st.number_input("Transport / Petrol", min_value=300.0, value=300.0, step=50.0)
    insurance = st.number_input("Insurance", min_value=0.0, value=800.0, step=100.0)

with manual_col2:
    family = st.number_input("Family Support", min_value=200.0, value=200.0, step=50.0)
    lifestyle = st.number_input("Lifestyle / Shopping", min_value=150.0, value=150.0, step=50.0)
    medical = st.number_input("Medical", min_value=0.0, value=500.0, step=100.0)
    others = st.number_input("Others", min_value=0.0, value=500.0, step=100.0)

expense_df = pd.DataFrame({
    "Category": [
        "Housing",
        "Food & Groceries",
        "Transport",
        "Insurance",
        "Family",
        "Lifestyle",
        "Medical",
        "Others"
    ],
    "Amount": [
        housing,
        food,
        transport,
        insurance,
        family,
        lifestyle,
        medical,
        others
    ]
})

fig2 = px.pie(
    expense_df,
    names="Category",
    values="Amount",
    title="Manual Expense Breakdown"
)

st.plotly_chart(fig2, use_container_width=True)

st.write(f"Total manual category expenses: **{money(currency, expense_df['Amount'].sum())}**")


# =====================================================
# FIRE Projection
# =====================================================
st.subheader("Net Worth Projection")

projection_years = st.slider("Projection years", min_value=5, max_value=40, value=20)

projection = []
net_worth = current_net_worth

for year in range(1, projection_years + 1):
    net_worth = net_worth * (1 + annual_return) + annual_savings
    projection.append({
        "Year": year,
        "Projected Net Worth": net_worth,
        "FIRE Target": fire_number
    })

projection_df = pd.DataFrame(projection)

fig3 = px.line(
    projection_df,
    x="Year",
    y=["Projected Net Worth", "FIRE Target"],
    title="Projected Net Worth vs FIRE Target"
)

st.plotly_chart(fig3, use_container_width=True)

st.dataframe(projection_df, use_container_width=True)


# =====================================================
# Credit Card Expense Analyzer
# =====================================================
st.subheader("💳 Credit Card Expense Analyzer")

st.write("Upload your monthly credit card statement. Supported formats: CSV, Excel, PDF.")

uploaded_file = st.file_uploader(
    "Upload credit card statement",
    type=["csv", "xlsx", "xls", "pdf"]
)

category_summary = pd.DataFrame()
top_transactions = pd.DataFrame()
cc_df = pd.DataFrame()

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    raw_df = pd.DataFrame()

    try:
        if file_name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            raw_df = pd.read_excel(uploaded_file)
        elif file_name.endswith(".pdf"):
            raw_df = read_pdf_to_dataframe(uploaded_file)
        else:
            st.error("Unsupported file type.")
    except Exception as e:
        st.error(f"File reading error: {e}")

    if raw_df.empty:
        st.warning("No data found. If this is a scanned PDF, the app may not be able to read it.")
    else:
        st.subheader("Raw Uploaded Data Preview")
        st.dataframe(raw_df.head(50), use_container_width=True)

        try:
            cc_df = standardize_uploaded_data(raw_df)

            if cc_df.empty:
                st.warning("No usable transaction data found.")
            else:
                cc_df["Category"] = cc_df["Description"].apply(categorize_expense)

                st.subheader("Cleaned Transaction Data")
                st.dataframe(cc_df, use_container_width=True)

                category_summary = (
                    cc_df.groupby("Category")["Amount"]
                    .sum()
                    .reset_index()
                    .sort_values("Amount", ascending=False)
                )

                total_spending = cc_df["Amount"].sum()

                st.subheader("Credit Card Summary")

                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Total Card Spending", money(currency, total_spending))

                if len(category_summary) > 0:
                    top_category = category_summary.iloc[0]["Category"]
                    top_category_amount = category_summary.iloc[0]["Amount"]
                    cc2.metric("Highest Category", top_category)
                    cc3.metric("Highest Category Amount", money(currency, top_category_amount))

                fig_cc = px.bar(
                    category_summary,
                    x="Category",
                    y="Amount",
                    text="Amount",
                    title="Credit Card Spending by Category"
                )

                fig_cc.update_traces(
                    texttemplate=f"{currency}%{{text:,.0f}}",
                    textposition="outside"
                )

                st.plotly_chart(fig_cc, use_container_width=True)

                fig_pie_cc = px.pie(
                    category_summary,
                    names="Category",
                    values="Amount",
                    title="Credit Card Spending Share"
                )

                st.plotly_chart(fig_pie_cc, use_container_width=True)

                st.subheader("Category Summary")
                st.dataframe(category_summary, use_container_width=True)

                st.subheader("Top 10 Biggest Transactions")
                top_transactions = cc_df.sort_values("Amount", ascending=False).head(10)
                st.dataframe(top_transactions, use_container_width=True)

                st.subheader("Saving Opportunity Calculator")

                flexible_categories = [
                    "Food & Drinks",
                    "Shopping",
                    "Travel",
                    "Subscriptions",
                    "Others"
                ]

                selected_flexible_categories = st.multiselect(
                    "Select categories you want to reduce",
                    options=list(category_summary["Category"]),
                    default=[
                        c for c in flexible_categories
                        if c in list(category_summary["Category"])
                    ]
                )

                saving_rate = st.slider(
                    "Assume you can reduce selected spending by (%)",
                    min_value=5,
                    max_value=50,
                    value=15,
                    step=5
                )

                flexible_spending = category_summary[
                    category_summary["Category"].isin(selected_flexible_categories)
                ]["Amount"].sum()

                possible_saving = flexible_spending * saving_rate / 100
                annual_extra_saving = possible_saving * 12

                st.success(
                    f"If you reduce selected spending by {saving_rate}%, "
                    f"you may save around {money(currency, possible_saving)} this month."
                )

                st.info(
                    f"If you keep this saving every month, your yearly extra saving is around "
                    f"{money(currency, annual_extra_saving)}."
                )

                csv_export = cc_df.to_csv(index=False).encode("utf-8")

                st.download_button(
                    label="Download cleaned categorized transactions as CSV",
                    data=csv_export,
                    file_name="categorized_credit_card_expenses.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Analysis error: {e}")


# =====================================================
# Free Built-in Assistant
# =====================================================
st.subheader("🤖 Financial Assistant")

st.write(
    "Get quick insights based on your FIRE numbers and uploaded spending categories."
)

if st.button("Generate Financial Analysis"):
    reply = rule_based_assistant(
        currency=currency,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_savings=monthly_savings,
        savings_rate=savings_rate,
        current_net_worth=current_net_worth,
        fire_number=fire_number,
        years_to_fire=years_to_fire,
        emergency_fund=emergency_fund,
        emergency_months=emergency_months,
        monthly_debt_payment=monthly_debt_payment,
        debt_ratio=debt_ratio,
        score=score,
        level=level,
        category_summary=category_summary,
        top_transactions=top_transactions
    )

    display_rule_based_reply(reply)


# =====================================================
# Simple Question-Based Assistant
# =====================================================
st.subheader("Ask a Simple Question")

question = st.selectbox(
    "Choose a question",
    [
        "",
        "How can I improve my FIRE score?",
        "Where should I reduce spending?",
        "Is my emergency fund enough?",
        "Is my debt level okay?",
        "How can I reach FIRE faster?"
    ]
)

if question:
    reply = rule_based_assistant(
        currency=currency,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_savings=monthly_savings,
        savings_rate=savings_rate,
        current_net_worth=current_net_worth,
        fire_number=fire_number,
        years_to_fire=years_to_fire,
        emergency_fund=emergency_fund,
        emergency_months=emergency_months,
        monthly_debt_payment=monthly_debt_payment,
        debt_ratio=debt_ratio,
        score=score,
        level=level,
        category_summary=category_summary,
        top_transactions=top_transactions
    )

    if question == "How can I improve my FIRE score?":
        st.write("To improve your FIRE score:")
        for action in reply["actions"]:
            st.write(f"- {action}")

    elif question == "Where should I reduce spending?":
        if reply["saving_details"]:
            st.write("Start with these categories:")
            for item in reply["saving_details"]:
                st.write(item)
        else:
            st.write("Upload your credit card statement first so I can identify your biggest flexible spending categories.")

    elif question == "Is my emergency fund enough?":
        if emergency_months >= 6:
            st.success(f"Yes. Your emergency fund covers about {emergency_months:.1f} months, which is healthy.")
        elif emergency_months >= 3:
            st.warning(f"It is acceptable, but not strong yet. You have about {emergency_months:.1f} months.")
        else:
            st.error(f"Not yet. You only have about {emergency_months:.1f} months. Aim for at least 3 to 6 months.")

    elif question == "Is my debt level okay?":
        if debt_ratio <= 10:
            st.success(f"Your debt ratio is low at {debt_ratio:.1f}%.")
        elif debt_ratio <= 30:
            st.warning(f"Your debt ratio is manageable at {debt_ratio:.1f}%, but monitor it.")
        else:
            st.error(f"Your debt ratio is high at {debt_ratio:.1f}%. Focus on reducing debt.")

    elif question == "How can I reach FIRE faster?":
        st.write("The main ways to reach FIRE faster:")
        st.write("- Increase monthly savings.")
        st.write("- Reduce your largest flexible expenses.")
        st.write("- Avoid new high-interest debt.")
        st.write("- Keep investing consistently based on your risk tolerance.")
        st.write("- Review your FIRE number if lifestyle expenses change.")


# =====================================================
# Notes
# =====================================================
st.info(
    "This is a planning tool only. It does not provide licensed financial advice. "
    "PDF reading works best with selectable text/table PDFs. Scanned PDFs may need OCR. "
    "The assistant uses built-in calculations and category rules."
)
