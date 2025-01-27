import streamlit as st
import pandas as pd
from groq import Groq
from io import BytesIO
from openai import OpenAI
import json
from elasticsearch import Elasticsearch

# Initialize the API clients with secrets
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize Elasticsearch
ELASTIC_URL = "https://elastic:NuwRaaWUktq5FM1QJZe6iexV@my-deployment-3eafc9.es.ap-south-1.aws.elastic-cloud.com:9243"
INDEX_NAME = "accounting_classification"
es = Elasticsearch(ELASTIC_URL)

def create_system_prompt():
    return """
    You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. 
    For each transaction, provide a JSON output in the following format:

    {
        "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
        "Category": "<One category from the strictly defined list>",
        "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
    }

    Ensure that your response includes only the JSON output without any accompanying text.
    """

# Define the user prompt
def create_user_prompt(description, cr_dr_indicator, narration=None):
    # Define ledger data directly in the function
    # Define ledger data separately
    ledger_data = {
    "Credit": {
        "Land & Building": "Purchased Land & Building",
        "Furniture": "Purchase of furniture made during the year",
        "Computer": "Purchase of computer made during the year",
        "Loan to Director": "Loan amount transferred to director",
        "Sale of Goods/Services": "Revenue from sale of goods or services",
        "Interest Income": "If any interest income is received",
        "Other Income (including Dividend Income)": "Income other than revenue from operations",
        "Cost of Services / Cost of Sales": "Expenses incurred for services or sales",
        "Salaries and Wages": "Salary payment to employees",
        "Bank Charges": "Bank charges debited from the bank statement",
        "Interest Expenses": "Loan interest expenses",
        "Director Remuneration": "Directors' salary payments made during the year",
        "Professional Charges": "Fee paid to professionals",
        "Rental & Accommodation Expense": "Rental payments to landlord",
        "Repairs & Maintenance": "Expenses in nature of repairs and maintenance",
        "Travelling Expenses": "Expenses related to travel",
        "Telephone Expense": "Expenses for telephone, mobile recharge, internet",
        "Capital Infusion": "Capital contribution made by the director",
        "Loan from Bank": "Loan proceeds received from the bank",
        "Loan from Director": "Loan proceeds received from the director",
        "GST Payment": "GST tax payment made",
        "TDS Payment": "TDS tax payment made",
        "Advance": "For advance salaries, advance tax, or similar transactions",
        "-- Electricity deposit (TNEB)": "Deposit made with Tamil Nadu Electricity Board",
        "-- Opening balance DTA": "Opening balance of deferred tax asset",
        "-- Rental deposit": "Deposit made with landlord",
        "-- To Directors (LT)": "Loans given to directors where receipt is expected after 12 months",
        "-- To Directors (ST)": "Loans given to directors where receipt is expected within 12 months",
        "-- To Others (LT)": "Loans given to other related parties expected after 12 months",
        "-- To Others (ST)": "Loans given to other related parties expected within 12 months",
        "Advance income tax": "Income tax advance payment",
        "Balances with bank": "Closing balance of bank as at 31-03",
        "Building": "Purchase of building made during the year",
        "Cash on hand": "Closing balance of cash as at 31-03",
        "Copyright": "Amount spent towards copyright development & registration",
        "Doubtful": "Trade receivables where receipt is doubtful",
        "Finished goods": "Closing stock of finished goods",
        "Fixed deposits maturing more than 12 months": "Fixed deposits maturing after 12 months",
        "Fixed deposits maturing within 12 months": "Fixed deposits maturing within 12 months",
        "GST Input tax credit": "Closing balance of GST credit ledger balance",
        "Investment in equity instruments (Subsidiary/ Associate/ JV)": "Investment in equity shares held for more than 12 months",
        "Investment in equity instruments (Subsidiary/ Associate/ JV) - (CI)": "Investment in equity shares held for less than 12 months",
        "Less: Provision for dimunition in value of investments": "Provision for diminishing value of investments",
        "Loans and advances to others (Unsecured, Considered Good)": "Loans given to others expected after 12 months",
        "Loans and advances to others (Unsecured, Considered Good) (ST)": "Loans given to others expected within 12 months",
        "Office Equipment": "Purchase of office equipment like A/C, water dispenser, etc.",
        "Other Current investments": "Investment in equity shares held for less than 12 months",
        "Other Income (incl. Dividend Income)": "Income other than revenue from operations",
        "Other Non-current investments": "Investment in equity shares held for more than 12 months",
        "Other assets": "Any assets expected to realize within 12 months",
        "Other income": "Other income received",
        "Other non current assets": "Any other assets realized after 12 months",
        "Others (specify nature)": "Other stock or materials",
        "Patents": "Amount spent towards patent development & registration",
        "Plant & Machinery": "Purchase of plant & machinery made during the year",
        "Prepaid insurance": "Insurance paid in advance for future coverage",
        "Raw materials": "Closing stock of raw materials",
        "Sale of goods": "Revenue from sale of goods",
        "Sale of services": "Revenue from services rendered",
        "Scrap sales": "Income from scrap sales",
        "Secured and considered good": "Trade receivables secured and receivable",
        "Stores and spares": "Closing stock of stores and spares",
        "TDS/TCS receivables": "Closing balance of TDS/TCS receivable",
        "Unsecured and considered good": "Trade receivables unsecured and receivable",
        "Website owned": "Amount spent towards website development & registration"
    },
    "Debit": {
        "Closing balance SP (A)": "Closing balance of securities premium account",
        "Closing balance PL (B)": "Closing balance of profit & loss account/retained earnings",
        "From Bank (LT)": "Secured long-term bank loan received",
        "From Directors (LT)": "Unsecured long-term loan received from Directors",
        "From Others (LT)": "Unsecured long-term loan received from Others",
        "Opening balance DTL": "Opening balance of deferred tax liabilities",
        "Other non-current liabilities": "Any other liability to be repaid after 12 months",
        "Gratuity": "Gratuity payable to employees",
        "From Bank (ST)": "Secured short-term bank loan received repayable within 12 months",
        "From Directors (ST)": "Unsecured short-term loan received from Directors repayable within 12 months",
        "Provision for expenses": "Provision made to meet upcoming expenses",
        "Provision for employee benefits": "Provision made for employee benefits like salaries",
        "Cost of goods sold": "Cost of goods sold during the period",
        "Cost of services": "Cost of services rendered during the period",
        "Salaries and wages": "Salary payment to employees",
        "Bank charges": "Bank charges debited from bank statement",
        "Interest on borrowings": "Interest payment on loans borrowed",
        "Administrative expense": "Expenses spent for administering the office",
        "Advertisement": "Advertisement expenses incurred during the year",
        "Business promotion expense": "Business promotion expenses incurred during the year",
        "Professional charges": "Fee paid to professionals",
        "Rental expense": "Rental payments made during the year",
        "Travelling expenses": "Expenses related to travel",
        "Telephone expense": "Expenses for telephone, mobile recharge, internet",
        "Miscellaneous expense": "Any expenses other than above which were miscellaneous",
        "GST Payment": "GST tax payment made",
        "TDS Payment": "TDS tax payment made",
        "(i) total outstanding dues of micro enterprises and small enterprises; and": "Trade payables outstanding to micro enterprises",
        "(ii) total outstanding dues of creditors other than micro enterprises and small enterprises": "Trade payables outstanding to other creditors",
        "-- Building maintenance": "Expenses for building repairs and maintenance",
        "-- Employee state insurance": "Employee State Insurance payable as on 31-03",
        "-- Employee/er provident fund": "Employer/employee provident fund payable as on 31-03",
        "-- Foreign travelling": "Foreign travel expenses incurred",
        "-- Goods and service tax payable (Net off of Input Tax Credit)": "GST payable as on 31-03",
        "-- Machinery maintenance": "Expenses for machinery repairs and maintenance",
        "-- Professional tax payable": "Professional tax payable as on 31-03",
        "-- Property tax payable": "Property tax payable as on 31-03",
        "-- Statutory audit fee": "Audit fee payments made",
        "-- Tax deducted at source": "Tax deducted at source payable as on 31-03",
        "-- Value added tax": "Value added tax payable as on 31-03",
        "-- Vehicle maintenance": "Expenses for vehicle repairs and maintenance",
        "Advance received from customers": "Advance received from customers outstanding as on 31-03",
        "Capital Contribution": "Capital contribution made by the director",
        "Closing balance of stock-in-trade": "Closing balance of stock-in-trade",
        "Contribution to provident and other funds": "Provident fund, Employee state insurance payments, etc.",
        "Credit card commission": "Credit card fee",
        "Credit card due payable": "Credit card due as on 31-03",
        "Current Tax": "Self-assessment tax payment"}
    }


    # Fetch ledger categories and definitions based on cr_dr_indicator
    if cr_dr_indicator not in ledger_data:
        return "Invalid value for Credit/Debit indicator. Must be 'Credit' or 'Debit'."

    categories = ledger_data[cr_dr_indicator]

    # Generate the prompt
    prompt = f"""
    ### Task: Categorize Bank Transactions into Predefined Accounting Categories.

    #### **Transaction Details**:
    - **Description**: {description}
    - **Credit/Debit**: {cr_dr_indicator}
    """
    if narration:
        prompt += f"- **Narration**: {narration}\n"

    prompt += """
    #### **Instructions**:
    1. Choose one category for the transaction from the following:
    """

    for category, definition in categories.items():
        prompt += f"       - {category}: {definition}\n"

    prompt += """
    2. Justify the category assignment with a brief explanation.

    3. Extract vendor/customer names only if applicable.

    4. If details are unclear, make an educated guess or mark as \"Unclassified.\"
    """

    return prompt

def push_to_es(unique_id, vendor, category):
    payload = {
        "unique_id": unique_id,
        "Vendor/Customer": vendor,
        "Category": category
    }
    try:
        response = es.index(index=INDEX_NAME, document=payload)
        return response
    except Exception as e:
        return {"error": str(e)}

def search_in_es(vendor):
    query = {
        "query": {
            "match": {"Vendor/Customer": vendor}
        }
    }
    try:
        response = es.search(index=INDEX_NAME, body=query)
        if response["hits"]["hits"]:
            return response["hits"]["hits"][0]["_source"]["Category"]
    except Exception as e:
        return None
    return None

def classify_transaction(row, with_narration, model):
    vendor = row['Description']  # Using Description as Vendor reference
    existing_category = search_in_es(vendor)
    if existing_category:
        return {"Vendor/Customer": vendor, "Category": existing_category, "Explanation": "Retrieved from database"}
    
    if model == "LLAMA 70B (Groq)":
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": create_system_prompt()},
                {"role": "user", "content": create_user_prompt(row['Description'], row['Credit/Debit'], row.get('Narration') if with_narration else None)}
            ],
            temperature=0.13,
            max_tokens=8000
        )
        raw_content = completion.choices[0].message.content
    else:
        response = client.chat.completions.create(
            model="gpt-4o" if model == "GPT4-o (OpenAI)" else "gpt-4o-mini",
            messages=[
                {"role": "system", "content": create_system_prompt()},
                {"role": "user", "content": create_user_prompt(row['Description'], row['Credit/Debit'], row.get('Narration') if with_narration else None)}
            ],
            temperature=0.13,
            max_tokens=2000
        )
        raw_content = response.choices[0].message.content
    
    try:
        json_content = json.loads(raw_content)
        push_to_es(row["Description"], json_content["Vendor/Customer"], json_content["Category"])
        return json_content
    except Exception as e:
        st.error(f"Error processing response: {e}")
        return {"Vendor/Customer": "", "Category": "", "Explanation": ""}

def main():
    st.title("Bank Statement Classifier with Elasticsearch Caching")
    uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        if st.button("Start Processing"):
            results = [classify_transaction(row, False, "GPT4-o (OpenAI)") for _, row in df.iterrows()]
            df["Vendor/Customer"] = [res.get("Vendor/Customer", "") for res in results]
            df["Category"] = [res.get("Category", "") for res in results]
            st.write(df)

if __name__ == "__main__":
    main()
