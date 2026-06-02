# FIRE Expense Dashboard

A free Streamlit dashboard for tracking income, expenses, FIRE progress, credit card spending categories, and saving opportunities.

## Features

- Income vs expenses dashboard
- FIRE number calculator
- FIRE score
- Savings rate analysis
- Net worth projection
- CSV / Excel / PDF credit card statement upload
- Automatic expense categorization
- Top 10 biggest transactions
- Saving opportunity calculator
- Free built-in financial assistant
- No OpenAI API required
- No AI usage charge

## Files

| File | Purpose |
|---|---|
| `fire_free_app.py` | Main Streamlit app |
| `requirements.txt` | Python packages needed for deployment |
| `.gitignore` | Files GitHub should ignore |
| `sample_credit_card_expenses.csv` | Sample upload file for testing |
| `PRIVACY_NOTICE.md` | Privacy and data handling notice |
| `DEPLOYMENT_STEPS.md` | Step-by-step GitHub and Streamlit deployment guide |

## How to Run Locally

Open Command Prompt and run:

```bash
cd /d C:\Users\chiny\stock_app
pip install -r requirements.txt
streamlit run fire_free_app.py
```

## How to Deploy

1. Create a GitHub repository.
2. Upload `fire_free_app.py`, `requirements.txt`, and the support documents.
3. Go to Streamlit Community Cloud.
4. Create a new app.
5. Select your GitHub repository.
6. Set the main file path as:

```text
fire_free_app.py
```

7. Click Deploy.

## Important Privacy Reminder

This app can process credit card statements. Before uploading or sharing statements, remove sensitive information such as:

- Full card number
- IC / passport number
- Address
- Phone number
- Email address
- Bank account number

This app is a planning tool only and does not provide licensed financial advice.
