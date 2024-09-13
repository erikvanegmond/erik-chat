import weaviate
import weaviate.classes as wvc
import os
from typing import List
import streamlit as st

from openai import OpenAI
from stqdm import stqdm


def word_splitter(source_text: str) -> List[str]:
    import re
    source_text = re.sub(r"\s+", " ", source_text)  # Replace multiple whitespces
    return re.split(r"\s", source_text)  # Split by single whitespace


def get_chunks_fixed_size_with_overlap(text: str, chunk_size: int, overlap_fraction: float) -> List[str]:
    text_words = word_splitter(text)
    overlap_int = int(chunk_size * overlap_fraction)
    chunks = []
    for i in range(0, len(text_words), chunk_size):
        chunk = " ".join(text_words[max(i - overlap_int, 0): i + chunk_size])
        chunks.append(chunk)
    return chunks


def get_chunks_by_paragraph(source_text: str) -> List[str]:
    paragraphs = source_text.split("\n\n")
    new_paragraphs = []
    for paragraph in paragraphs:
        if '\n* ' in paragraph:
            paragraph = paragraph.strip('* ')
            new_paragraphs += paragraph.split('\n* ')
        else:
            new_paragraphs.append(paragraph)
    return new_paragraphs


def build_chunk_objs(book_text_obj, chunks):
    chunk_objs = list()
    for i, c in enumerate(chunks):
        chunk_obj = {
            "chapter_title": book_text_obj["chapter_title"],
            "filename": book_text_obj["filename"],
            "chunk": c,
            "chunk_index": i
        }
        chunk_objs.append(chunk_obj)
    return chunk_objs


def main(root_path):
    with st.status("Refreshing data..."):
        prop_map = {
            'Tools & libraries': 'Tools_en_libraries',
            'Methoden & Technieken': 'Methoden_en_Technieken',
            'Programmeer-, scripting-, en markuptalen': 'Programmeer_scripting_en_markuptalen'
        }

        cv_objs = list()
        cv_data = []
        path_list = []
        for root, _, files in os.walk(root_path):
            rel_path = root.removeprefix(root_path).strip('\\').strip('/')
            path_list += [(root, rel_path, file) for file in files]

        st.write("Parsing files...")
        for root, rel_path, file in stqdm(path_list):
            bedrijven = {x.get('bedrijf'): x for x in cv_objs}
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                data = {}
                for i, line in enumerate(lines := f.readlines()):
                    if not line.strip():
                        break
                    key, _, value = line.partition(":")
                    key = key.strip()
                    # print(key, prop_map.get(key, key))
                    data[prop_map.get(key, key)] = value.strip().replace('[', '').replace(']', '')
                beschrijving = "".join(lines[i:]).strip().replace('[', '').replace(']', '')
                if file[0].isnumeric() and (company := file.partition(' ')[-1].rpartition('.')[0]):
                    data['bedrijf'] = company
                    data_summary = filter(
                        lambda x: bool(x),
                        [data.get('Platforms', ''), data.get('Methoden_en_Technieken', ''),
                         data.get('Besturingssytemen', ''), data.get('Databases', ''), data.get('Tools_en_libraries', '')]
                    )
                    data_to_language = ""
                    if 'heden' in data['Periode'].lower():
                        data_to_language += f"Sinds {data['Periode'].split(' - ')[0]} werkt Erik bij {data['bedrijf']} "
                    else:
                        data_to_language += f"In de periode {data['Periode']} heeft Erik bij {data['bedrijf']} "

                    if data['type'] in ['Werk', 'Vrijwilligerswerk']:
                        data_to_language += f"gewerkt in de rol van {data['Rol']}. "
                    if data['type'] in ['Vrijwilligerswerk']:
                        data_to_language += f"vrijwilligerswerk verricht in de rol van {data['Rol']}. "
                    elif data['type'] == "Opleiding":
                        data_to_language = f"In de periode {data['Periode']} heeft Erik bij {data['bedrijf']} de {data["NaamOpleiding"]} gevolgd. "
                    elif data['type'] == "Extracurriculair":
                        data_to_language = f"In de periode {data['Periode']} heeft Erik naast zijn studie gewerkt bij {data["bedrijf"]}. "

                    if data['Programmeer_scripting_en_markuptalen'].strip():
                        data_to_language += f"Hij werkte met de volgende programeertalen: {data['Programmeer_scripting_en_markuptalen']}. "
                    if data_summary:
                        data_to_language += f"Verder heeft hij met de volgende technieken, databases en tools gewerkt: {', '.join(data_summary)}\n"

                    data['beschrijving'] = data_to_language + beschrijving
                    cv_data.append(data['beschrijving'])
                    cv_objs.append(data)

                elif file == 'Algemeen.md':
                    data['beschrijving'] = beschrijving
                    cv_data.insert(0, data['beschrijving'])
                    cv_objs.append(data)
                elif bedrijf := bedrijven.get(rel_path):
                    cv_objs.append(bedrijf | {'beschrijving': beschrijving})
                else:
                    data['beschrijving'] = beschrijving
                    cv_objs.append(data)

        st.write("Chunking files...")
        chunked_objs = []
        for cv_obj in stqdm(cv_objs):
            text = cv_obj['beschrijving']
            for strategy_name, chunks in [
                ["fixed_size_100", get_chunks_fixed_size_with_overlap(text, 100, 0.2)],
                ["para_chunks", get_chunks_by_paragraph(text)]
            ]:
                for i, chunk in enumerate(chunks):
                    chunked_obj = cv_obj | {'chunk': chunk, "chunk_index": i, 'chunking_strategy': strategy_name}
                    del chunked_obj['beschrijving']
                    chunked_objs.append(chunked_obj)

        with weaviate.connect_to_local() as client:
            COLLECTION_NAME = "CV"

            if COLLECTION_NAME in client.collections.list_all():
                client.collections.delete("CV")

            cv_collection = client.collections.create(
                name="CV",
                vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(),
                properties=[
                    wvc.config.Property(name='chunk',
                                        data_type=wvc.config.DataType.TEXT,
                                        index_filterable=True,
                                        index_searchable=True,
                                        )
                ]
            )
            with st.spinner("Uploading to weaviate..."):
                cv_collection.data.insert_many(chunked_objs)


        with open('assets/cv_summary.txt', 'w', encoding='utf-8') as f:
            client = OpenAI()
            st.write("Summarizing CV...")
            lines = []
            for d in stqdm(cv_data):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f'Vat het volgende stuk tekst samen in 1 alinea: {d}'},
                    ]
                )
                msg = response.choices[0].message.content + '\n\n'
                lines.append(msg)
            f.writelines(lines)
        st.write("Data has been refreshed")
        st.toast('Data has been refreshed', icon='❄️')

st.header("Reload data")

root_path = st.text_input('path/to/data')

if root_path.strip():
    # root_path = r'C:\Users\erikv\Dropbox\Documenten\Obsidian\Werk\Carriere'
    # root_path = r'/root/text_data'
    main(root_path=root_path)
