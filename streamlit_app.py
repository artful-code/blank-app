import streamlit as st
import pandas as pd
from io import BytesIO
from openai import OpenAI
import json
from elasticsearch import Elasticsearch

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize Elasticsearch
ELASTIC_URL = "https://elastic:NuwRaaWUktq5FM1QJZe6iexV@my-deployment-3eafc9.es.ap-south-1.aws.elastic-cloud.com:9243"
INDEX_NAME = "accounting_classification"
es = Elasticsearch(ELASTIC_URL)

def create_system_prompt():
    return """You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. 
    For each transaction, provide a JSON output in the following format:
    {
        "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
        "Category": "<One category from the strictly defined list>",
        "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
    }
    Ensure that your response includes only the JSON output without any accompanying text."""

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


def is_valid_vendor(vendor):
    """Check if vendor name is valid (not empty, not Unclassified, etc.)"""
    if not vendor:
        return False
    invalid_names = {"unclassified", "n/a", "unknown", "none", "", "error"}
    return str(vendor).lower().strip() not in invalid_names

def push_to_es(unique_id, vendor, category):
    try:
        # Validate vendor name before pushing
        if not is_valid_vendor(vendor):
            st.warning(f"Skipping Elasticsearch push: Invalid vendor name '{vendor}'")
            return None
            
        # Validate category
        if not category or category.lower() in {"unclassified", "error in classification"}:
            st.warning(f"Skipping Elasticsearch push: Invalid category '{category}'")
            return None

        payload = {
            "unique_id": unique_id,
            "Vendor/Customer": vendor,
            "Category": category
        }
        response = es.index(index=INDEX_NAME, document=payload)
        return response
    except Exception as e:
        st.error(f"Elasticsearch error: {str(e)}")
        return None

def search_in_es(vendor):
    try:
        # Skip search if vendor name is invalid
        if not is_valid_vendor(vendor):
            return None
            
        query = {
            "query": {
                "match": {
                    "Vendor/Customer": vendor
                }
            }
        }
        response = es.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["hits"]:
            category = response["hits"]["hits"][0]["_source"]["Category"]
            # Double check the category is valid
            if category and category.lower() not in {"unclassified", "error in classification"}:
                return category
                
    except Exception as e:
        st.error(f"Elasticsearch search error: {str(e)}")
    return None
def classify_transaction(row, with_narration=False):
    try:
        system_prompt = create_system_prompt()
        vendor = row['Description']
        
        # Check existing classification
        existing_category = search_in_es(vendor)
        if existing_category:
            return {
                "Vendor/Customer": vendor,
                "Category": existing_category,
                "Explanation": "Retrieved from database"
            }
        
        user_prompt = create_user_prompt(
            row['Description'],
            row['Credit/Debit'],
            row.get('Narration') if with_narration else None
        )
        
        # Make API call to GPT-4-mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        raw_content = response.choices[0].message.content
        
        # Debug: Print raw response
        st.write(f"Raw response for {vendor}:", raw_content)
        
        # Clean and parse JSON
        raw_content = raw_content.strip()
        if not raw_content.startswith('{'):
            start_idx = raw_content.find('{')
            end_idx = raw_content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                raw_content = raw_content[start_idx:end_idx + 1]
        
        json_content = json.loads(raw_content)
        
        # Store in Elasticsearch
        if json_content.get("Category"):
            push_to_es(row["Description"], json_content["Vendor/Customer"], json_content["Category"])
        
        return json_content
    
    except Exception as e:
        st.error(f"Error processing transaction: {str(e)}")
        return {
            "Vendor/Customer": vendor if 'vendor' in locals() else "Error",
            "Category": "Processing Error",
            "Explanation": f"Error: {str(e)}"
        }

def main():
    st.title("Bank Statement Classifier")
    
    uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            # Read and display file preview
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
            st.write("File Preview:")
            st.write(df.head())
            
            # Verify required columns
            required_cols = ['Description', 'Credit/Debit']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
                return
            
            if st.button("Process Transactions"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = []
                for idx, row in df.iterrows():
                    status_text.text(f"Processing transaction {idx + 1}/{len(df)}")
                    result = classify_transaction(row)
                    results.append(result)
                    progress_bar.progress((idx + 1) / len(df))
                
                # Update DataFrame
                df["Vendor/Customer"] = [res.get("Vendor/Customer", "") for res in results]
                df["Category"] = [res.get("Category", "") for res in results]
                df["Explanation"] = [res.get("Explanation", "") for res in results]
                
                status_text.text("Processing complete!")
                st.write("Results:")
                st.write(df)
                
                # Add download button
                output = BytesIO()
                df.to_excel(output, index=False)
                output.seek(0)
                st.download_button(
                    label="Download Processed File",
                    data=output,
                    file_name="classified_transactions.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()