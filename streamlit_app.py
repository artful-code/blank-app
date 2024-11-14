import streamlit as st
import pandas as pd
from groq import Groq
from io import BytesIO

# Initialize the Groq client with the API key directly
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Define the system prompt to expect JSON output with strict categories
def create_system_prompt():
    return """
You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. For each transaction, provide a JSON output in the following format:

{
    "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
    "Category": "<One category from the strictly defined list below>",
    "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
}

Categories:
- Land & Building
- Furniture
- Computer
- Loan to Director
- Sale of Goods/Services
- Interest Income
- Other Income (including Dividend Income)
- Cost of Services / Cost of Sales
- Salaries and Wages
- Bank Charges
- Interest Expenses
- Director Remuneration
- Professional Charges
- Rental & Accommodation Expense
- Repairs & Maintenance
- Travelling Expenses
- Telephone Expense
- Capital Infusion
- Loan from Bank
- Loan from Director
- GST Payment
- TDS Payment

Do not use any other category names or modify these categories in any way.
"""

# Define the user prompt with strict categorization guidelines
def create_user_prompt(description, cr_dr_indicator, narration=None):
    prompt = f"""
Task: You are an expert accountant. I need your help categorizing bank transactions from a bank statement into predefined accounting categories. Each transaction contains the following details: transaction ID, value date, transaction posted date, description, Cr/Dr indicator (credit or debit), transaction amount, and available balance. Here’s what I need you to do:

1. **Classify Each Transaction**: Based on the available information, classify each transaction into one of the following categories. Use only these categories without modification:
   - Land & Building
   - Furniture
   - Computer
   - Loan to Director
   - Sale of Goods/Services
   - Interest Income
   - Other Income (including Dividend Income)
   - Cost of Services / Cost of Sales
   - Salaries and Wages
   - Bank Charges
   - Interest Expenses
   - Director Remuneration
   - Professional Charges
   - Rental & Accommodation Expense
   - Repairs & Maintenance
   - Travelling Expenses
   - Telephone Expense
   - Capital Infusion
   - Loan from Bank
   - Loan from Director
   - GST Payment
   - TDS Payment

   **Only one category should be assigned per transaction.**

2. **Extract Vendor/Customer Name**: If the description contains an indication of a vendor or customer name, extract and display it. Common patterns include "ReqPay," "IMPS," or explicit names.

3. **Use Credit/Debit Indicator**: Use the Cr/Dr indicator to aid in classification:
   - "CR" (credit) transactions may indicate income, refunds, or capital infusion.
   - "DR" (debit) transactions may suggest expenses, loan repayments, or outgoing payments.

4. **Infer Category Based on Keywords**:
   - **Assets**: Keywords like "purchase" or asset references suggest categories like "Land & Building," "Furniture," or "Computer."
   - **Loans and Infusions**: Terms like "loan" and mentions of directors or banks indicate "Loan to Director," "Loan from Bank," or "Loan from Director."
   - **Sales and Income**: Credits labeled "interest" or "sales" imply "Interest Income" or "Sale of Goods/Services."
   - **Operational Costs**: Debits related to services or costs imply "Cost of Services / Cost of Sales."
   - **Employee-Related**: "Salary" or "wage" suggests "Salaries and Wages"; "bonus" implies "Director Remuneration."
   - **Professional Services**: "Consulting" or "professional" expenses indicate "Professional Charges."
   - **Recurring Expenses**: Words like "rent," "repair," or "travel" map to categories such as "Rental & Accommodation Expense" or "Repairs & Maintenance."
   - **Tax Payments**: Explicit labels like "GST" or "TDS" should be classified as "GST Payment" or "TDS Payment."

5. **Handle Unclear Entries**: If the information in the row is insufficient for a clear categorization, make the best possible guess or label it as "Unclassified."

6. **Provide Explanations**: For each classified transaction, give a brief explanation justifying the categorization based on the description, Cr/Dr indicator, and any keywords or patterns used.

**Transaction Details**:
- **Description**: {description}
- **Credit/Debit**: {cr_dr_indicator}
"""
    if narration:
        prompt += f"- **Narration**: {narration}"
    return prompt

# Function to process each row through the LLM
def classify_transaction_llm(row, with_narration):
    # Construct the user prompt
    user_prompt = create_user_prompt(
        description=row['Description'],
        cr_dr_indicator=row['Credit/Debit'],
        narration=row['Narration'] if with_narration else None
    )

    # Call the Groq API with the prompts and model parameters
    completion = client.chat.completions.create(
        model="llama-3.2-90b-text-preview",
        messages=[
            {"role": "system", "content": create_system_prompt()},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.13,
        max_tokens=256,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
    )

    # Parse the JSON response
    response = completion.choices[0].message.content
    try:
        response_dict = response  # Assuming response is already a dict
        if isinstance(response_dict, dict):
            return {
                "Vendor/Customer": response_dict.get("Vendor/Customer", ""),
                "Category": response_dict.get("Category", ""),
                "Explanation": response_dict.get("Explanation", "")
            }
        else:
            return {
                "Vendor/Customer": "",
                "Category": "",
                "Explanation": ""
            }
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        return {
            "Vendor/Customer": "",
            "Category": "",
            "Explanation": ""
        }

# Streamlit app
def main():
    st.title("Bank Statement Classifier with LLM Integration")

    # File upload
    uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])

    if uploaded_file:
        # Load the file
        file_extension = uploaded_file.name.split(".")[-1]
        if file_extension == "csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Option to choose with or without narration
        with_narration = st.radio("Choose input mode:", ("Without Narration", "With Narration")) == "With Narration"

        # Check for required columns based on narration selection
        required_columns = ["Description", "Credit/Debit"]
        if with_narration:
            required_columns.append("Narration")

        # Verify that the required columns are present
        if all(col in df.columns for col in required_columns):
            # Apply the LLM on each row and store results
            results = []
            progress_bar = st.progress(0)
            for idx, row in df.iterrows():
                result = classify_transaction_llm(row, with_narration)
                results.append(result)
                progress_bar.progress((idx + 1) / len(df))
            progress_bar.empty()

            # Convert results into separate columns in the DataFrame
            df["Vendor/Customer"] = [res["Vendor/Customer"] for res in results]
            df["Category"] = [res["Category"] for res in results]
            df["Explanation"] = [res["Explanation"] for res in results]

            # Download link for the updated sheet
            st.write("## Download the updated sheet with classifications")
            # Create a BytesIO buffer and write the Excel file into it
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
            st.error(f"Required columns {required_columns} not found in the uploaded file.")
    else:
        st.info("Please upload an Excel or CSV file to proceed.")

if __name__ == "__main__":
    main()
