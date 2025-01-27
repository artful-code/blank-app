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

# Initialize session state
if 'ai_results' not in st.session_state:
    st.session_state.ai_results = []
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
if 'unique_vendors' not in st.session_state:
    st.session_state.unique_vendors = set()
if 'rules' not in st.session_state:
    st.session_state.rules = []

def is_valid_vendor(vendor):
    """Check if vendor name is valid"""
    if not vendor:
        return False
    invalid_names = {"unclassified", "n/a", "unknown", "none", "", "error"}
    return str(vendor).lower().strip() not in invalid_names

def push_to_es(unique_id, vendor, category):
    """Push to Elasticsearch with validation"""
    try:
        # Check if combination already exists
        existing = search_in_es(vendor)
        if existing == category:
            return None
            
        if not is_valid_vendor(vendor) or not category:
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
    """Search in Elasticsearch"""
    try:
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
            return response["hits"]["hits"][0]["_source"]["Category"]
    except Exception as e:
        st.error(f"Elasticsearch search error: {str(e)}")
    return None

def create_system_prompt():
    return """You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. 
    For each transaction, provide a JSON output in the following format:
    {
        "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
        "Category": "<One category from the strictly defined list>",
        "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
    }
    
    For Vendor/Customer extraction:
    1. Extract the actual business or individual name from the transaction description
    2. Remove any transaction-related text, dates, or reference numbers
    3. If no clear vendor/customer name can be found, use the most relevant entity name from the description
    4. Do not use 'Unknown' or 'Not specified' - extract the best possible name
    
    For Category selection:
    1. Choose only from the provided category list
    2. Match the category based on transaction nature and Credit/Debit indicator
    3. Consider both the description and the transaction type for categorization
    4. If uncertain, choose the most appropriate category based on available information
    
    For Explanation:
    1. Provide a brief, clear reason for the category selection
    2. Reference specific parts of the description that led to the categorization
    3. Include any key indicators that helped determine the category
    
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


def process_with_ai(row):
    try:
        system_prompt = create_system_prompt()
        user_prompt = create_user_prompt(
            description=row['Description'],
            cr_dr_indicator=row['Credit/Debit'],
            narration=row.get('Narration') if 'Narration' in row else None
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        # Clean the JSON string
        content = content.replace('\n', ' ').strip()
        if not content.startswith('{'):
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                content = content[start_idx:end_idx]
        
        return json.loads(content)
        
    except Exception as e:
        raise Exception(f"AI Processing error: {str(e)}")
def create_rule_ui():
    """Create UI for rule-based classification"""
    st.subheader("Create Classification Rule")
    
    col1, col2 = st.columns(2)
    
    with col1:
        vendor_condition = st.selectbox("Vendor Name Condition", ["equals", "contains"])
        vendor_value = st.selectbox("Select Vendor", sorted(list(st.session_state.unique_vendors)))
        transaction_type = st.selectbox("Transaction Type", ["Credit", "Debit"])
    
    with col2:
        amount_operator = st.selectbox("Amount Condition", ["greater than", "less than", "equals"])
        amount_value = st.number_input("Amount Value", min_value=0.0)
        category = st.selectbox("Category", ["Category 1", "Category 2"])  # Will be populated from your categories
    
    if st.button("Add Rule"):
        new_rule = {
            "vendor_condition": vendor_condition,
            "vendor_value": vendor_value,
            "amount_operator": amount_operator,
            "amount_value": amount_value,
            "transaction_type": transaction_type,
            "category": category
        }
        st.session_state.rules.append(new_rule)
        st.success("Rule added!")

def apply_rules(df):
    df = df.copy()
    
    # Convert Amount column to numeric if it exists
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"].str.replace(',', ''), errors='coerce')
    
    # Initialize Category column if it doesn't exist
    if "Category" not in df.columns:
        df["Category"] = None
    
    for rule in st.session_state.rules:
        mask = pd.Series(True, index=df.index)
        
        # Apply vendor condition
        if rule["vendor_condition"] == "equals":
            mask &= df["Extracted_Vendor"] == rule["vendor_value"]
        else:
            mask &= df["Extracted_Vendor"].str.contains(rule["vendor_value"], case=False, na=False)
        
        # Apply amount condition
        amount_value = float(rule["amount_value"])
        if rule["amount_condition"] == "greater than":
            mask &= df["Amount"].fillna(0) > amount_value
        elif rule["amount_condition"] == "less than":
            mask &= df["Amount"].fillna(0) < amount_value
        else:  # equals
            mask &= df["Amount"].fillna(0) == amount_value
        
        # Apply transaction type
        mask &= df["Credit/Debit"] == rule["transaction_type"]
        
        # Update matching rows
        df.loc[mask, "Category"] = rule["category"]
    
    return df
def main():
    st.title("Bank Statement Classifier")
    
    # Initialize session state
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'ai_results' not in st.session_state:
        st.session_state.ai_results = {}
    if 'rules' not in st.session_state:
        st.session_state.rules = []
    if 'es_matched' not in st.session_state:
        st.session_state.es_matched = 0
    if 'rules_applied' not in st.session_state:
        st.session_state.rules_applied = False
    if 'remaining_df' not in st.session_state:
        st.session_state.remaining_df = None
    if 'unique_vendors' not in st.session_state:
        st.session_state.unique_vendors = set()

    uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    
    if uploaded_file:
        # Initial file processing
        if st.session_state.df is None:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.session_state.df = df.copy()
            
            # Process with AI and check Elasticsearch
            st.write("Processing transactions...")
            progress = st.progress(0)
            total_transactions = len(df)
            es_matched = 0
            ai_results = {}
            
            for idx, row in df.iterrows():
                # Check Elasticsearch first
                existing_category = search_in_es(row['Description'])
                if existing_category:
                    es_matched += 1
                else:
                    # Process with AI if not in ES
                    result = process_with_ai(row)
                    ai_results[idx] = result
                    if is_valid_vendor(result.get("Vendor/Customer")):
                        st.session_state.unique_vendors.add(result["Vendor/Customer"])
                
                progress.progress((idx + 1) / total_transactions)
            
            st.session_state.es_matched = es_matched
            st.session_state.ai_results = ai_results
            
            # Create remaining_df excluding ES matches
            remaining_mask = ~df.index.isin([idx for idx, row in df.iterrows() 
                                           if search_in_es(row['Description'])])
            st.session_state.remaining_df = df[remaining_mask].copy()
            
            st.success(f"{es_matched} out of {total_transactions} transactions found in database")
            
        # Display remaining transactions
        if len(st.session_state.remaining_df) > 0:
            st.subheader("Remaining Transactions")
            st.write(st.session_state.remaining_df)
            
            # Rules Processing Section
            st.subheader("Create Classification Rules")
            col1, col2 = st.columns(2)
            
            with col1:
                vendor_condition = st.selectbox(
                    "Vendor Name Condition",
                    ["equals", "contains"],
                    key="vendor_condition"
                )
                vendor_value = st.selectbox(
                    "Select Vendor",
                    sorted(list(st.session_state.unique_vendors)),
                    key="vendor_value"
                )
            
            with col2:
                amount_condition = st.selectbox(
                    "Amount Condition",
                    ["greater than", "less than", "equals"],
                    key="amount_condition"
                )
                amount_value = st.number_input(
                    "Amount Value",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="amount_value"
                )
                transaction_type = st.selectbox(
                    "Transaction Type",
                    ["Credit", "Debit"],
                    key="transaction_type"
                )
            
            categories = get_categories_for_type(transaction_type)
            category = st.selectbox("Select Category", categories, key="category")
            
            if st.button("Add Rule"):
                new_rule = {
                    "vendor_condition": vendor_condition,
                    "vendor_value": vendor_value,
                    "amount_condition": amount_condition,
                    "amount_value": amount_value,
                    "transaction_type": transaction_type,
                    "category": category
                }
                st.session_state.rules.append(new_rule)
                st.success("Rule added!")
            
            # Display and apply rules
            if st.session_state.rules:
                st.subheader("Current Rules")
                for i, rule in enumerate(st.session_state.rules):
                    st.write(f"Rule {i+1}:", rule)
                
                if st.button("Apply Rules"):
                    with st.spinner("Applying rules..."):
                        classified_df = apply_rules(st.session_state.remaining_df)
                        st.session_state.rules_applied = True
                        st.session_state.remaining_df = classified_df
                        st.success("Rules applied successfully!")
                        
                        # Show approval button for rules
                        if st.button("Approve Rule Classifications"):
                            rules_mask = classified_df["Category"].notna()
                            rules_df = classified_df[rules_mask]
                            for _, row in rules_df.iterrows():
                                push_to_es(row["Description"], row["Extracted_Vendor"], row["Category"])
                            st.success("Rule classifications saved to database!")
                            
                            # Update remaining_df
                            st.session_state.remaining_df = classified_df[~rules_mask]
            
            # AI Processing for remaining transactions
            if len(st.session_state.remaining_df) > 0:
                st.subheader(f"Process {len(st.session_state.remaining_df)} Remaining Transactions with AI")
                if st.button("Process with AI"):
                    # Use stored AI results
                    remaining_indices = st.session_state.remaining_df.index
                    for idx in remaining_indices:
                        if idx in st.session_state.ai_results:
                            result = st.session_state.ai_results[idx]
                            st.session_state.remaining_df.loc[idx, "Category"] = result["Category"]
                            st.session_state.remaining_df.loc[idx, "Extracted_Vendor"] = result["Vendor/Customer"]
                    
                    st.write("AI Classifications:", st.session_state.remaining_df)
                    
                    if st.button("Approve AI Classifications"):
                        for _, row in st.session_state.remaining_df.iterrows():
                            push_to_es(row["Description"], row["Extracted_Vendor"], row["Category"])
                        st.success("AI classifications saved to database!")
                        st.session_state.remaining_df = pd.DataFrame()  # Clear remaining transactions

        # Download button for final results
        if st.session_state.df is not None:
            output = BytesIO()
            st.session_state.df.to_excel(output, index=False)
            output.seek(0)
            st.download_button(
                label="Download Processed File",
                data=output,
                file_name="classified_transactions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()