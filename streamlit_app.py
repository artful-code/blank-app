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
        json_content = extract_json_content(raw_content)
        result = json.loads(json_content)
        push_to_es(row["Description"], result["Vendor/Customer"], result["Category"])
        return result
    except (KeyError, json.JSONDecodeError, AttributeError) as e:
        st.error(f"Error processing response: {e}")
        return {"Vendor/Customer": "", "Category": "", "Explanation": ""}

def main():
    st.title("Bank Statement Classifier with Elasticsearch Caching")
    model_option = st.selectbox("Select a model to process transactions:", ["LLAMA 70B (Groq)", "GPT4-o (OpenAI)", "GPT4-o-mini (OpenAI)"])
    uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        with_narration = st.radio("Include Narration?", ("No", "Yes")) == "Yes"
        required_columns = ["Description", "Credit/Debit"] + (["Narration"] if with_narration else [])
        if all(col in df.columns for col in required_columns):
            if st.button("Start Processing"):
                results = []
                progress_bar = st.progress(0)
                for idx, row in df.iterrows():
                    results.append(classify_transaction(row, with_narration, model_option))
                    progress_bar.progress((idx + 1) / len(df))
                df["Vendor/Customer"] = [res.get("Vendor/Customer", "") for res in results]
                df["Category"] = [res.get("Category", "") for res in results]
                df["Explanation"] = [res.get("Explanation", "") for res in results]
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                st.download_button("Download Classified Transactions", excel_buffer, "classified_bank_statement.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.error(f"Missing required columns: {required_columns}")
    else:
        st.info("Upload an Excel or CSV file to proceed.")

if __name__ == "__main__":
    main()

