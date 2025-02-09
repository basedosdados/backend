import json
import streamlit as st
import os
import dotenv
from aisql import Datasets, gen_full_dump, get_schema, get_dataset_descriptions
from google.generativeai import configure, GenerativeModel

# Load environment variables
dotenv.load_dotenv()
configure(api_key=os.environ["GEMINI_API_KEY"])

def main():
    st.title("Base dos Dados - Pontapé")

    with st.spinner("Loading schema..."):
        schema = get_schema()
        datasets = get_dataset_descriptions()
    # filter datasets in tables
    datasets = {k: v for k, v in datasets.items() if k in set(t['dataset_id'] for t in schema)}

    st.subheader(f"Loaded {len(schema)} table in {len(datasets)} datasets")

    with st.expander("Sample question:"):
        Q="Write me an sql query that helps me understand the correlation of dead newborns with pollution levels in regions such as municipalities. You can use a proxy for pollution if needed."
        st.write(Q)

    question = st.text_area("Faça seu pedido singelo ao Mago dos Dados", height=101)

    ### CHANGE PROMPT TO USE FULL DUMP AND RETRY!

    if st.button("Vai filhão!"):
        if not question:
            st.warning("Escreva algo ali em cima!")
        else:
            with st.spinner("Filtering datasets..."):
                interesting_datasets = select_datasets_of_interest(datasets, question)
            with st.expander("Filtered on datasets:"):
                st.write("Filtered on to datasets: ", list(interesting_datasets.values()))
            with st.spinner("Answering question..."):
                response = answer_question(interesting_datasets, schema, question)
            st.write(response)

def select_datasets_of_interest(datasets: Datasets, question):
    model = GenerativeModel("gemini-2.0-flash")
    prompt = f"""Use the provided schema to select all the datasets that could happen to be relevant to the following question. If in doubt, select the dataset. 
    It is better to select too many datasets than too few.
    You are not to answer the question. You should only return a json list of relevant dataset names and ids. Output valid json. 
    Schema:"""
    for dataset_info in datasets.values():
        prompt += f"""
        Dataset: {dataset_info['name']}
        id: {dataset_info['id']}
        Description: {dataset_info['description']}
        """
    prompt += f"""
    Question:
    {question}
    Answer:
    """ + """
    ```json
    [
    {"id":"""
    response = model.generate_content(prompt)
    # st.write(response.text)
    interesing = json.loads(response.text.strip('`json'))
    return {id:v for id, v in datasets.items() if id in set(d['id'] for d in interesing)}

def answer_question(datasets, schema, question):
    model = GenerativeModel("gemini-2.0-flash")
    token_count = model.count_tokens(question).total_tokens
    prompt = f"""Use the provided schema to provide an sql answering the following question.
    Your answer must contain some reasoning, and finally the sql query.

    Your answer should look like this:
    "
    # Reasoning:
    [... reasoning markdown ...]

    # SQL:
    ```sql
    ... sql query ...
    ```
    "
    ---

    Schema:
    {gen_full_dump(schema, datasets)}

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
        return ''

main()
