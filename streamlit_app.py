import streamlit as st
import pandas as pd
from groq import Groq
from io import BytesIO
import openai
import json

# Initialize the API clients with secrets
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Define the system prompt
def create_system_prompt():
    return """
    You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. For each transaction, provide a JSON output in the following format:

    {
        "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
        "Category": "<One category from the strictly defined list in user prompt>",
        "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
    }
    """

# Define the user prompt
def create_user_prompt(description, cr_dr_indicator, narration=None):
    prompt = f"""
    You are an expert accountant tasked with categorizing bank transactions into predefined accounting categories. Each transaction includes the following details: transaction ID, value date, posted date, description, Cr/Dr indicator (credit or debit), transaction amount, and available balance.

    ### Instructions:
    1. **Classify the Transaction**:
       - Assign exactly one category to each transaction from this predefined list:
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

    2. **Interpretation Rules**:
       - Use the transaction description and Cr/Dr indicator to determine the most appropriate category.
       - Address typos or slight variations in terms (e.g., "accessorie" for "accessory") by inferring the intended meaning.
       - Broaden interpretations when necessary:
         - **Accessories/Gadgets** → Furniture, Computer, or Cost of Services / Cost of Sales.
         - **Rent/Repair** → Rental & Accommodation Expense or Repairs & Maintenance.
       - Consider "CR" (credit) transactions as income, refunds, or capital infusion.
       - Consider "DR" (debit) transactions as expenses, loan repayments, or outgoing payments.

    3. **Vendor/Customer Extraction**:
       - Extract vendor or customer names from the transaction description only.

    4. **Handling Unclear Entries**:
       - If the transaction details are insufficient for a clear classification, make an educated guess or label it as "Unclassified."

    5. **Provide an Explanation**:
       - Justify the assigned category with a brief explanation based on keywords, patterns, or the overall transaction context.

    ### Transaction Details:
    - **Description**: {description}
    - **Credit/Debit**: {cr_dr_indicator}
    """
    if narration:
        prompt += f"- **Narration**: {narration}"
    return prompt

# Function to process rows using Groq
def classify_with_groq(row, with_narration):
    user_prompt = create_user_prompt(
        description=row['Description'],
        cr_dr_indicator=row['Credit/Debit'],
        narration=row['Narration'] if with_narration else None
    )
    completion = groq_client.chat.completions.create(
        model="llama-3.2-90b-text-preview",
        messages=[
            {"role": "system", "content": create_system_prompt()},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.13,
        max_tokens=256
    )
    st.subheader("Groq Raw Output")
    st.json(completion) 
    return extract_response_groq(completion)

# Function to process rows using OpenAI
def classify_with_openai(row, with_narration, model):
    user_prompt = create_user_prompt(
        description=row['Description'],
        cr_dr_indicator=row['Credit/Debit'],
        narration=row['Narration'] if with_narration else None
    )
    completion = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": create_system_prompt()},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.13,
        max_tokens=256
    )
    
    return extract_response_openai(completion)

# Extract response content specifically for Groq
def extract_response_groq(completion):
    try:
        # Extract the `content` field from the first choice
        raw_content = completion["choices"][0].message.content

        # Parse the content if it contains valid JSON
        if "```json" in raw_content:  # Look for JSON content in the message
            start_index = raw_content.find("```json") + 7  # Start after the ```json
            end_index = raw_content.find("```", start_index)  # End before closing ```
            json_content = raw_content[start_index:end_index]
            response_dict = json.loads(json_content)  # Parse the extracted JSON string
        else:
            st.warning("No valid JSON found in Groq response content.")
            response_dict = {}

        return {
            "Vendor/Customer": response_dict.get("Vendor/Customer", ""),
            "Category": response_dict.get("Category", ""),
            "Explanation": response_dict.get("Explanation", "")
        }
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        st.error(f"Error processing Groq response: {e}")
        return {"Vendor/Customer": "", "Category": "", "Explanation": ""}


# Extract response content specifically for OpenAI
def extract_response_openai(completion):
    try:
        # Extract content from OpenAI's response structure
        response_content = completion.choices[0].message["content"]
        response_dict = json.loads(response_content)  # Parse as JSON
        return {
            "Vendor/Customer": response_dict.get("Vendor/Customer", ""),
            "Category": response_dict.get("Category", ""),
            "Explanation": response_dict.get("Explanation", "")
        }
    except (KeyError, json.JSONDecodeError) as e:
        st.error(f"Error processing OpenAI response: {e}")
        return {"Vendor/Customer": "", "Category": "", "Explanation": ""}

# Streamlit app
def main():
    st.title("Bank Statement Classifier")

    # Model selection dropdown
    st.subheader("Choose an analysis model")
    model_option = st.selectbox(
        "Select a model to process the transactions:",
        ["LLAMA 90B (Groq)", "GPT4-o (OpenAI)", "GPT4-o-mini (OpenAI)"]
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
                    if model_option == "LLAMA 90B (Groq)":
                        result = classify_with_groq(row, with_narration)
                    elif model_option == "GPT4-o (OpenAI)":
                        result = classify_with_openai(row, with_narration, "gpt-4o")
                    elif model_option == "GPT4-o-mini (OpenAI)":
                        result = classify_with_openai(row, with_narration, "gpt-4o-mini")
                    results.append(result)
                    progress_bar.progress((idx + 1) / len(df))
                progress_bar.empty()

                df["Vendor/Customer"] = [res["Vendor/Customer"] for res in results]
                df["Category"] = [res["Category"] for res in results]
                df["Explanation"] = [res["Explanation"] for res in results]

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
