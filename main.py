import logging

from flask import Flask, request
from googletrans import Translator
import psycopg2
from psycopg2 import Error
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


@app.route("/translate", methods=['POST'])
def translate():
    body = request.get_json()
    if body['code'][0] != CODE:
        return 'bad code'
    text = body['text'][0]
    src_language = body['src_language'][0]
    dsc_language = body['dsc_language'][0]
    chat_id = body['chat_id'][0]
    result = get_translate_text(text, src_language, dsc_language)
    return save_translate_to_db(chat_id, result)


def get_translate_text(text, src_language, dsc_languages):
    translator = Translator()
    result = {src_language: text}
    for dsc_language in dsc_languages:
        res = translator.translate(text, src=src_language, dest=dsc_language)
        result[dsc_language] = res.text
    return result


def save_translate_to_db(chat_id, profile_list):
    global conn, cursor
    try:
        conn = psycopg2.connect(dbname=DBNAME, user=USER, password=PASSWORD, host=HOST, port=POSTGRES_PORT)
        cursor = conn.cursor()
        print(conn)
        cursor.execute("SELECT markup_profile_id from person p where p.chat_id = %s", (chat_id,))
        markup_profile_id = cursor.fetchone()
        if markup_profile_id[0] is None:
            cursor.execute("SELECT MAX(id) FROM markup_profile")
            target_id = cursor.fetchone()
            if target_id[0] is None:
                target_id = 0
            else:
                target_id = target_id[0]
            target_id = target_id + 1
            cursor.execute("""INSERT INTO markup_profile (id, ru_profile, en_profile, es_profile) 
                                        VALUES (%s, %s, %s, %s);""",
                           (target_id, profile_list['ru'], profile_list['en'], profile_list['es']))
        else:
            cursor.execute("SELECT id from markup_profile m ORDER BY id ASC LIMIT 1")
            target_id = cursor.fetchone()
            target_id = target_id[0]
            cursor.execute("""UPDATE markup_profile 
            SET ru_profile = %s, en_profile = %s, es_profile= %s WHERE id = %s;""",
                           (profile_list['ru'], profile_list['en'], profile_list['es'], target_id))
        cursor.execute("UPDATE person p SET markup_profile_id = %s WHERE p.chat_id = %s", (target_id, (chat_id,)))
        conn.commit()
        print("commit")
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL", error)
        return error
    finally:
        if conn:
            cursor.close()
            conn.close()
            return "ok"


if __name__ == "__main__":
    CODE = os.getenv('TRANSLATE_CODE_SERVICE')
    DBNAME = os.getenv('POSTGRES_DATABASE')
    USER = os.getenv('POSTGRES_USER')
    PASSWORD = os.getenv('POSTGRES_ROOT_PASSWORD')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT')
    PORT = os.getenv('TRANSLATE_SERVICE_PORT')
    HOST = os.getenv('POSTGRES_HOST')
    app.run(host='0.0.0.0',port=PORT)
