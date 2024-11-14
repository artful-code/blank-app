import streamlit as st
import pandas as pd
from groq import Groq
from io import BytesIO
import json

# Initialize the Groq client with the API key from Streamlit secrets
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Define the system prompt to expect JSON output with strict categories
def create_system_prompt():
    return """
    You are an expert accountant responsible for accurately categorizing bank transactions and extracting vendor/customer names according to strict criteria. For each transaction, provide a JSON output in the following format:

{
    "Vendor/Customer": "<Extracted name or entity involved in the transaction>",
    "Category": "<One category from the strictly defined list in user prompt>",
    "Explanation": "<Brief reasoning for the chosen category based on the description, Cr/Dr indicator, and narration if provided>"
}
    """

# Define the user prompt with strict categorization guidelines
# Define the user prompt with strict categorization guidelines
def create_user_prompt(description, cr_dr_indicator, narration=None):
    prompt = f"""
You are an expert accountant. I need your help categorizing bank transactions from a bank statement into predefined accounting categories. Each transaction contains the following details: transaction ID, value date, transaction posted date, description, Cr/Dr indicator (credit or debit), transaction amount, and available balance. Here’s what I need you to do:

Classify Each Transaction: Based on the available information, classify each transaction into one of the following categories. Use only these categories without modification:

Land & Building
Furniture
Computer
Loan to Director
Sale of Goods/Services
Interest Income
Other Income (including Dividend Income)
Cost of Services / Cost of Sales
Salaries and Wages
Bank Charges
Interest Expenses
Director Remuneration
Professional Charges
Rental & Accommodation Expense
Repairs & Maintenance
Travelling Expenses
Telephone Expense
Capital Infusion
Loan from Bank
Loan from Director
GST Payment
TDS Payment
Only one category should be assigned per transaction.

Understand Description and/or Narration: Use your understanding of the description and/or narration (whichever is provided) to accurately determine the transaction's category. While keywords can be helpful, it is not necessary to rely solely on them. Focus on the overall context and meaning to ensure accurate classification.

Handle Typos and Variations: Be flexible with common misspellings or slight variations in terms (e.g., "accessorie" may refer to "accessory"). If a term appears to be a minor typo or spelling variation of a common business item, interpret it accordingly.

Interpret Common Terms for Accessories and Equipment: If the description or narration includes terms like "accessory," "gadget," or other generic terms related to business equipment, consider categories such as:

Furniture: If it’s related to office furnishings.
Computer: If it relates to electronic equipment or gadgets.
Cost of Services / Cost of Sales: If it pertains to items used in delivering services or goods sold.
Extract Vendor/Customer Name from Description Only: If the description contains an indication of a vendor or customer name, extract and display it. Do not infer the vendor/customer name from any other field.

Use Credit/Debit Indicator: Use the Cr/Dr indicator to aid in classification:

"CR" (credit) transactions may indicate income, refunds, or capital infusion.
"DR" (debit) transactions may suggest expenses, loan repayments, or outgoing payments.
Infer Category Based on Overall Context:

Assets: Keywords like "purchase" or asset references suggest categories like "Land & Building," "Furniture," or "Computer."
Loans and Infusions: Terms like "loan" and mentions of directors or banks indicate "Loan to Director," "Loan from Bank," or "Loan from Director."
Sales and Income: Credits labeled "interest" or "sales" imply "Interest Income" or "Sale of Goods/Services."
Operational Costs: Debits related to services or costs imply "Cost of Services / Cost of Sales."
Employee-Related: "Salary" or "wage" suggests "Salaries and Wages"; "bonus" implies "Director Remuneration."
Professional Services: "Consulting" or "professional" expenses indicate "Professional Charges."
Recurring Expenses: Words like "rent," "repair," or "travel" map to categories such as "Rental & Accommodation Expense" or "Repairs & Maintenance."
Tax Payments: Explicit labels like "GST" or "TDS" should be classified as "GST Payment" or "TDS Payment."
Handle Unclear Entries: If the information in the row is insufficient for a clear categorization, make the best possible guess or label it as "Unclassified."

Provide Explanations: For each classified transaction, give a brief explanation justifying the categorization based on the description, Cr/Dr indicator, and any keywords, patterns, or contextual understanding used.

Summary of Updates
Included Flexibility for Typos: The prompt now instructs the model to interpret common misspellings or slight variations, such as "accessorie" for "accessory."
Guidance for Generic Terms: Added instructions to interpret terms like "accessory" or "gadget" based on the context of business items.
More Contextual Classification: Reinforced the instruction to understand the overall context, with examples for interpreting general business equipment.
These updates should help the LLM better categorize transactions that contain minor spelling errors or generic descriptions.






You said:
### Learnings from the Unidentified Transactions 1. **Spelling Variations and Minor Typos**: * The term "accessorie" is a misspelling of "accessory," which caused the LLM to fail in categorizing it. * The model struggled to map "accessorie" and "accessorie and gadget" to any specific category because it didn’t recognize the intended meaning due to this typo. 2. **Ambiguity in Description**: * The descriptions and narration provided lacked enough context to clearly indicate the nature of the transactions. This is particularly true when the terms are generic or ambiguous, such as "accessorie," which could apply to various items. 3. **Additional Guidance for Context Understanding**: * The LLM needs to be instructed to interpret terms more flexibly, especially for common business items like accessories or gadgets, even if they're not explicitly listed in the predefined categories.

the prompt should instruct the model to do a hard keyword search

look for broader ideas or topics or simialr types of servies or productsb 
ChatGPT said:
ChatGPT
To ensure that the model performs a hard keyword search while also looking for broader topics or similar types of services or products, here’s an updated prompt. This prompt emphasizes exact keyword matching and encourages the model to consider broader or related terms in categorization.

You are an expert accountant. I need your help categorizing bank transactions from a bank statement into predefined accounting categories. Each transaction contains the following details: transaction ID, value date, transaction posted date, description, Cr/Dr indicator (credit or debit), transaction amount, and available balance. Here’s what I need you to do:

Classify Each Transaction Using Hard Keyword Matching: Rely on exact keywords in the description or narration to classify each transaction into one of the following categories. Use only these categories without modification:

Land & Building
Furniture
Computer
Loan to Director
Sale of Goods/Services
Interest Income
Other Income (including Dividend Income)
Cost of Services / Cost of Sales
Salaries and Wages
Bank Charges
Interest Expenses
Director Remuneration
Professional Charges
Rental & Accommodation Expense
Repairs & Maintenance
Travelling Expenses
Telephone Expense
Capital Infusion
Loan from Bank
Loan from Director
GST Payment
TDS Payment
Only one category should be assigned per transaction. Focus on exact matches to the keywords in the description/narration and align them directly with the listed categories.

Consider Broader Topics and Similar Products or Services: In addition to hard keyword matching, consider broader ideas or related products/services if a keyword strongly implies a similar category. For example:

Accessories may broadly imply items used in the office or business environment and can fall under categories like Furniture or Computer.
Gadgets or Devices can imply Computer or Electronics equipment.
Terms like Rent, Repair, or Maintenance suggest Rental & Accommodation Expense or Repairs & Maintenance.
Extract Vendor/Customer Name from Description Only: If the description contains an indication of a vendor or customer name, extract and display it. Do not infer the vendor/customer name from any other field.

Use Credit/Debit Indicator: Use the Cr/Dr indicator to aid in classification:

"CR" (credit) transactions may indicate income, refunds, or capital infusion.
"DR" (debit) transactions may suggest expenses, loan repayments, or outgoing payments.
Apply Specific Rules Based on Keywords:

Assets: Keywords like "purchase" or asset references suggest categories like "Land & Building," "Furniture," or "Computer."
Loans and Infusions: Terms like "loan" and mentions of directors or banks indicate "Loan to Director," "Loan from Bank," or "Loan from Director."
Sales and Income: Credits labeled "interest" or "sales" imply "Interest Income" or "Sale of Goods/Services."
Operational Costs: Debits related to services or costs imply "Cost of Services / Cost of Sales."
Employee-Related: "Salary" or "wage" suggests "Salaries and Wages"; "bonus" implies "Director Remuneration."
Professional Services: "Consulting" or "professional" expenses indicate "Professional Charges."
Recurring Expenses: Words like "rent," "repair," or "travel" map to categories such as "Rental & Accommodation Expense" or "Repairs & Maintenance."
Tax Payments: Explicit labels like "GST" or "TDS" should be classified as "GST Payment" or "TDS Payment."
Handle Minor Typos and Variations in Keywords: If a keyword is misspelled or has minor variations (e.g., "accessorie" instead of "accessory"), treat it as the closest possible match. Focus on identifying and correcting minor typos that may affect categorization.

Handle Unclear Entries: If the information in the row is insufficient for a clear categorization, make the best possible guess or label it as "Unclassified."

Provide Explanations: For each classified transaction, give a brief explanation justifying the categorization based on the description, Cr/Dr indicator, and any keywords or patterns used.


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
    response_content = completion.choices[0].message.content  # Extract content from response
    try:
        # The content is a JSON string, so we need to parse it
        response_dict = json.loads(response_content)
        
        # Extract fields from the parsed JSON
        return {
            "Vendor/Customer": response_dict.get("Vendor/Customer", ""),
            "Category": response_dict.get("Category", ""),
            "Explanation": response_dict.get("Explanation", "")
        }
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON content: {e}")
        return {
            "Vendor/Customer": "",
            "Category": "",
            "Explanation": ""
        }


# Streamlit app
def main():
    st.title("Bank Statement Classifier")

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
            # Add a Start Processing button
            if st.button("Start Processing"):
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
