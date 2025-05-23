#!/usr/bin/env python3
"""
AI Database Translation Script

This script uses an LLM API to translate database content from Portuguese to English and Spanish.

Usage:
1. Create a .env file in the same directory with the following content:
   ```
   BETTER_EXCEPTIONS=1
   API_KEY=your_api_key_here
   DB_PASSWORD=your_db_password
   DB_HOST=your_db_host
   DB_PORT=5432
   DB_USER=api
   DB_NAME=api
   ```
2. Run the script.
3. Tweak the prompt or other code if necessary.

The script processes multiple tables and fields, translating content and updating the database.
"""

from pprint import pprint
from random import random

import dotenv

dotenv.load_dotenv()

import json

import better_exceptions

better_exceptions.hook()
import csv as _csv
import os
import time
from collections import deque
from functools import wraps
from io import StringIO

import google.generativeai as genai
import psycopg2
from tqdm import tqdm

genai.configure(api_key=os.getenv("API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest")
# model = genai.GenerativeModel('gemini-1.0-pro-latest')


def main():
    """
    Main function to execute the translation process for all specified tables and fields.
    """
    for table, fields in FIELDS_TO_TRANSLATE:
        print(
            f"{table:<20}: {str(fields):<30} - Entries to process: {get_data(table, fields, count_only=True)}"
        )
    print("Press Enter to continue...")
    input()
    for table, fields in FIELDS_TO_TRANSLATE:
        treat_table(table, fields)


def get_new_fields(fields):
    """
    Generate new field names for English and Spanish translations.

    Args:
        fields (list): Original field names.

    Returns:
        list: New field names with '_en' and '_es' suffixes.
    """
    return [f"{f}_en" for f in fields] + [f"{f}_es" for f in fields]


def treat_table(table, fields):
    """
    Process and translate data for a specific table and set of fields.

    Args:
        table (str): Name of the table to process.
        fields (list): List of fields to translate.
    """
    data = get_data(table, fields)
    data = dictify(sorted(data, key=lambda x: random()))
    data = [d | {f: None for f in get_new_fields(fields)} for d in data]

    print(f"Processing {len(data)} entries!")
    new_fields_description_for_prompt = [f"{f}_en (english)" for f in fields] + [
        f"{f}_es (spanish)" for f in fields
    ]

    pbar = tqdm(total=len(data), smoothing=0)
    # for batch in batchify(3, data):
    errors = []
    for d in batch_by_token_size(100, 1, data):
        print(f"Processing a batch of size: {len(d)} in table {table!r}")
        response = None
        try:
            pprint(d)
            response = gen_content(
                f"""
We are an NGO translating metadata for a open public database. We have json with data in portuguese.
Would you please translate the following json, filling up the missing keys: {new_fields_description_for_prompt} . Just write the output json and nothing else.

```
    {json.dumps(d, indent=4)}
```


"""
            )
            print(response.text)
            res = json.loads(response.text.strip("\n`json"))
            for res_line, original_line in zip(res, d):
                try:
                    for field in get_new_fields(fields):
                        assert field in res_line, f"Missing {field!r} column"
                    assert res_line["id"] == original_line["id"], "Id not matching"
                    write_response_to_db(res_line, table, fields)
                    print("Written!")
                except Exception as e:
                    print(e)
                    errors.append((e, response))
                finally:
                    pbar.update(1)
        except KeyboardInterrupt:
            print("Stopping...")
            breakpoint()
            break
        except Exception as e:
            print(e)
            errors.append((e, response))
            pbar.update(len(d))
    pbar.close()
    print("ALL DONE!")
    print(f"Number of errors: {len(errors)}")
    if errors:
        pass
        # breakpoint()
    db.commit()
    print(f"{len(errors)} ERRORS")
    pprint(errors)
    # breakpoint()


def connect_db():
    """
    Establish a connection to the PostgreSQL database.

    Returns:
        psycopg2.connection: Database connection object.
    """
    db = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    db.autocommit = True
    return db


db = connect_db()
cursor = db.cursor()


def sql(q):
    """
    Execute an SQL query and return the results.

    Args:
        q (str): SQL query to execute.

    Returns:
        list: Query results.
    """
    cursor.execute(q)
    result = cursor.fetchall()
    return result


def csv(data):
    output = StringIO()
    csv_writer = _csv.writer(output)
    if cursor.description:
        headers = [col[0] for col in cursor.description]
        csv_writer.writerow(headers)
    csv_writer.writerows(data)
    return output.getvalue()


def dictify(data):
    """
    Convert query results to a list of dictionaries.

    Args:
        data: Query results to convert.

    Returns:
        list: List of dictionaries representing the data.
    """
    if not isinstance(data, list):
        out = [data]
    else:
        out = data
    field_names = [desc[0] for desc in cursor.description]
    out = [dict(zip(field_names, d)) for d in out]
    if not isinstance(data, list):
        out = out[0]
    return out


def batchify(size, data):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), size):
        yield data[i : i + size]


def batch_by_token_size(max_tokens, max_batch, data):
    """
    Yield chunks from data where the total token count of each chunk does not exceed max_tokens.

    Args:
        max_tokens (int): Maximum number of tokens per batch.
        max_batch (int): Maximum number of items per batch.
        data (list): Data to be batched.

    Yields:
        list: Batch of data items.
    """

    def token_counter(item):
        return len(str(item).split())

    batch = []
    token_count = 0
    for item in data:
        item_tokens = token_counter(item)
        if batch and (token_count + item_tokens > max_tokens or len(batch) >= max_batch):
            yield batch
            batch = []
            token_count = 0
        batch.append(item)
        token_count += item_tokens
    if batch:
        yield batch


def write_response_to_db(res, table, fields):
    """
    Write translated content back to the database.

    Args:
        res (dict): Translated data.
        table (str): Name of the table to update.
        fields (list): List of fields that were translated.
    """
    new_fields = get_new_fields(fields)
    set_clause = ", ".join([f"{field} = %s" for field in new_fields])
    values = [res[field] for field in new_fields]
    # values = [field + ' ' if field else None for field in values]
    cursor.execute(f'UPDATE "{table}" SET {set_clause} WHERE id = %s', values + [res["id"]])


def get_data(table, fields, count_only=False):
    """
    Retrieve data from the database for translation.

    Args:
        table (str): Name of the table to query.
        fields (list): List of fields to retrieve.
        count_only (bool): If True, return only the count of rows to process.

    Returns:
        int or list: Count of rows or list of data to process.
    """
    pt_fields = ", ".join(f + "_pt" for f in fields)
    if len(fields) == 1:
        # skip single fields if they are null at the source. Doing this properly for multi fields is hard so we don't do it
        restriction = " AND ".join(
            f"{f}_en IS NULL AND {f}_es IS NULL AND {f}_pt IS NOT NULL" for f in fields
        )
    else:
        restriction = " AND ".join(f"{f}_en IS NULL AND {f}_es IS NULL" for f in fields)
    predicate = "count(*)" if count_only else f"id, {pt_fields}"
    out = sql(f'SELECT {predicate} FROM "{table}" WHERE {restriction}')
    return out[0][0] if count_only else out


# def get_data():
# out = sql('SELECT id, name_pt, description_pt FROM dataset WHERE id NOT IN (SELECT id FROM translated_dataset)')
# return out


def rate_limiter(max_calls_per_minute):
    interval = 60.0 / max_calls_per_minute
    call_times = deque()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal call_times
            now = time.time()
            while call_times and call_times[0] <= now - 60:
                call_times.popleft()
            if len(call_times) < max_calls_per_minute:
                call_times.append(now)
                return func(*args, **kwargs)
            else:
                sleep_time = interval - (now - call_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                return wrapper(*args, **kwargs)

        return wrapper

    return decorator


def rate_limiter(max_calls_per_minute):
    min_interval = 60.0 / max_calls_per_minute
    last_called = 0

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_called
            elapsed = time.time() - last_called
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called = time.time()
            return ret

        return wrapper

    return decorator


@rate_limiter(max_calls_per_minute=14)
def gen_content(c):
    """
    Generate content using the AI model with rate limiting.

    Args:
        c (str): Prompt for content generation.

    Returns:
        genai.types.GenerateContentResponse: Generated content.
    """
    return model.generate_content(c)


EXAMPLE_DATA = [
    """                                    id |             name_en              |                                                                                                                                                                                                                               description_en
    ----+----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    1 | Censo Agropecuário               | O Censo Agropecuário, realizado pelo Instituto Brasileiro de Geografia e Estatística (IBGE), é a principal e mais completa investigação estatística e territorial sobre a produção agropecuária do país. Visa obter informações sobre a estrutura, a dinâmica e o nível de produção da atividade agropecuária brasileira.                                                                                                                                                  +
        |                                  |                                                                                                                                                                                                                                                                                                                                                                                                                                                                            +
        |                                  | As informações geradas possibilitam a avaliação de políticas públicas como, por exemplo, a de redistribuição de terras. Elas permitem, ainda, estudos a respeito da expansão das fronteiras agrícolas, da dinamização produtiva ditada pelas inovações tecnológicas, e enriquecem a produção de indicadores ambientais. Propiciam também análises sobre transformações decorrentes do processo de reestruturação e de ajustes na economia e de seus reflexos sobre o setor.+
        |                                  |                                                                                                                                                                                                                                                                                                                                                                                                                                                                            +
        |                                  | Enquanto as pesquisas mensais e trimestrais sobre agricultura e pecuária disponibilizam dados referentes ao Brasil, Grandes Regiões e Unidades da Federação, os resultados do Censo Agro são referidos a municípios e a localidades, permitindo agregações e análises de diferentes recortes territoriais, como unidades de conservação ambiental, terras indígenas, bacias hidrográficas, Biomas, assentamentos fundiários, áreas remanescentes de quilombos, etc.        +
        |                                  |
    2 | Pesquisa Nacional de Saúde (PNS) | A Pesquisa Nacional de Saúde (PNS) é um inquérito de base domiciliar e âmbito nacional, realizada pelo Ministério da Saúde (MS) em parceria com o Instituto Brasileiro de Geografia e Estatística (IBGE), nos anos de 2013 e 2019.                                                                                                                                                                                                                                         +
        |                                  | A população pesquisada corresponde aos moradores de domicílios particulares permanentes do Brasil, exceto os localizados nos setores censitários especiais (compostos por aglomerados subnormais; quartéis, bases militares etc.; alojamento, acampamentos etc.; embarcações, barcos, navios etc.; aldeia indígena; penitenciárias, colônias penais, presídios, cadeias etc.; asilos, orfanatos, conventos, hospitais etc.; e assentamentos rurais).                       +
        |                                  |
"""
]

FIELDS_TO_TRANSLATE = [
    ("dataset", ["name"]),
    ("dataset", ["description"]),
    ("analysis", ["name", "description"]),
    ("analysis_type", ["name"]),
    ("area", ["name"]),
    ("availability", ["name"]),
    ("column", ["description"]),
    ("column", ["observations"]),
    ("column_original_name", ["name"]),
    ("entity", ["name"]),
    ("entity_category", ["name"]),
    ("information_request", ["observations"]),
    ("language", ["name"]),
    ("license", ["name"]),
    ("organization", ["name", "description"]),
    ("quality_check", ["name", "description"]),
    ("raw_data_source", ["name", "description"]),
    ("status", ["name"]),
    ("table", ["name", "description"]),
    ("tag", ["name"]),
    ("theme", ["name"]),
]

main()
