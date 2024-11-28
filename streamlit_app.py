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
        "Category": "<One category from the strictly defined list>",
        "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
    }

    Ensure that your response includes only the JSON output without any accompanying text.
    """

# Define the user prompt
def create_user_prompt(description, cr_dr_indicator, narration=None):
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
    1. Choose one category for the transaction:
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
       - Advance (for advance salaries, advance tax, or similar transactions)

    2. Justify the category assignment with a brief explanation.

    3. Extract vendor/customer names only if applicable.

    4. If details are unclear, make an educated guess or mark as "Unclassified."
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
        st.write("Raw Groq Response:", raw_content)
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
        st.write("Raw OpenAI Response:", raw_content)
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
