import streamlit as st
import os
import dotenv
from aisql import gen_full_dump, get_schema, get_dataset_descriptions
from google.generativeai import configure, GenerativeModel

# Load environment variables
dotenv.load_dotenv()
configure(api_key=os.environ["GEMINI_API_KEY"])

def main():
    st.title("Data Exploration with Gemini")

    schema = get_schema()
    datasets = get_dataset_descriptions()
    # filter datasets in tables
    datasets = {k: v for k, v in datasets.items() if k in set(t['dataset_id'] for t in schema)}

    st.subheader(f"Loaded {len(schema)} table in {len(datasets)} datasets")

    Q="Write me an sql query that helps me understand the correlation of dead newborns with pollution levels in regions such as municipalities. You can use a proxy for pollution if needed."

    st.text(Q)

    question = st.text_area("Faça seu pedido singelo ao Mago dos Dados", height=101)

    ### CHANGE PROMPT TO USE FULL DUMP AND RETRY!

    if st.button("Vai filhão!"):
        if not question:
            st.warning("Escreva algo ali em cima!")
        else:
            intersting_datasets = select_datasets_of_interest(datasets, question)
            st.write("Filtered on to datasets: ", intersting_datasets)
            response = answer_question(intersting_datasets, schema, question)
            st.write(response.text)

def select_datasets_of_interest(datasets, question):
    model = GenerativeModel("gemini-2.0-flash")
    prompt = f"""Use the provided schema to select all the datasets that could happen to be relevant to the following question:
    Schema:"""
    for dataset_info in datasets.values():
        prompt += f"""
        Dataset: {dataset_info['name']}
        Description: {dataset_info['description']}
        """
    prompt += f"""
    Question:
    {question}
    Answer:
    """
    response = model.generate_content(prompt)
    return response.text

def answer_question(datasets, schema, question):
    model = GenerativeModel("gemini-2.0-flash")
    token_count = model.count_tokens(question).total_tokens
    prompt = f"""Use the provided schema to provide an sql answering the following question:

    Schema:
    {gen_full_dump(datasets, schema)}

    Question:
    {question}
    Answer:
    """

    token_count = model.count_tokens(prompt).total_tokens
    st.write(f"Total token count: {token_count}")
    try:
        response = model.generate_content(prompt) #, generation_config={"max_output_tokens": 150, "temperature": 0.7})
        answer = response.text
        return answer
    except Exception as e:
        st.error(f"An error occurred: {e}")

main()
