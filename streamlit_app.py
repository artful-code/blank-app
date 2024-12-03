import streamlit as st
import pandas as pd
from groq import Groq
from io import BytesIO
from openai import OpenAI
import json



# Initialize the API clients with secrets
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"]) 

# Define the system prompt
def create_system_prompt():
    return """
    You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. For each transaction, provide a JSON output in the following format:

    {
        "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
        "Category": "<One category   from the strictly defined list>",
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

# Utility function to clean and extract JSON
def extract_json_content(content):
    try:
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            return content[start:end].strip()
        return content.strip()
    except Exception as e:
        st.warning(f"Failed to extract JSON: {e}")
        return ""

# Function to process rows using Groq
def classify_with_groq(row, with_narration):
    try:
        user_prompt = create_user_prompt(
            description=row['Description'],
            cr_dr_indicator=row['Credit/Debit'],
            narration=row['Narration'] if with_narration else None
        )
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": create_system_prompt()},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.13,
            max_tokens=8000
        )
        raw_content = completion.choices[0].message.content
     
        json_content = extract_json_content(raw_content)
        return json.loads(json_content)
    except (KeyError, json.JSONDecodeError, AttributeError) as e:
        st.error(f"Error processing Groq response: {e}")
        return {"Vendor/Customer": "", "Category": "", "Explanation": ""}

# Function to process rows using OpenAI
def classify_with_openai(row, with_narration, model):
    try:
        user_prompt = create_user_prompt(
            description=row['Description'],
            cr_dr_indicator=row['Credit/Debit'],
            narration=row['Narration'] if with_narration else None
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": create_system_prompt()},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.13,
            max_tokens=2000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        raw_content = response.choices[0].message.content
        
        json_content = extract_json_content(raw_content)
        return json.loads(json_content)
    except (KeyError, json.JSONDecodeError, AttributeError) as e:
        st.error(f"Error processing OpenAI response: {e}")
        return {"Vendor/Customer": "", "Category": "", "Explanation": ""}

# Streamlit app
def main():
    st.title("Bank Statement Classifier")

    # Model selection dropdown
    st.subheader("Choose an analysis model")
    model_option = st.selectbox(
        "Select a model to process the transactions:",
        ["LLAMA 70B (Groq)", "GPT4-o (OpenAI)", "GPT4-o-mini (OpenAI)"]
    )

    # File upload
    uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])

    if uploaded_file:
        file_extension = uploaded_file.name.split(".")[-1]
        if file_extension == "csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        with_narration = st.radio("Choose input mode:", ("Without Narration", "With Narration")) == "With Narration"
        required_columns = ["Description", "Credit/Debit"]
        if with_narration:
            required_columns.append("Narration")

        if all(col in df.columns for col in required_columns):
            if st.button("Start Processing"):
                results = []
                progress_bar = st.progress(0)
                for idx, row in df.iterrows():
                    if model_option == "LLAMA 70B (Groq)":
                        result = classify_with_groq(row, with_narration)
                    elif model_option == "GPT4-o (OpenAI)":
                        result = classify_with_openai(row, with_narration, "gpt-4o")
                    elif model_option == "GPT4-o-mini (OpenAI)":
                        result = classify_with_openai(row, with_narration, "gpt-4o-mini")
                    results.append(result)
                    progress_bar.progress((idx + 1) / len(df))
                progress_bar.empty()

                df["Vendor/Customer"] = [res.get("Vendor/Customer", "") for res in results]
                df["Category"] = [res.get("Category", "") for res in results]
                df["Explanation"] = [res.get("Explanation", "") for res in results]

                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                st.download_button(
                    label="Download Excel",
                    data=excel_buffer,
                    file_name="classified_bank_statement.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error(f"Required columns {required_columns} not found in uploaded file.")
    else:
        st.info("Please upload an Excel or CSV file to proceed.")

if __name__ == "__main__":
    main()
