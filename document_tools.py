import os
import re
from pypdf import PdfReader
from config import DATA_FOLDER

DOCUMENTS = [
    '01_Support_Policy_v3_CURRENT.pdf',
    '02_Support_Policy_v2_DEPRECATED.pdf',
    '03_Cancellation_and_Service_Credit_SOP_v4.pdf',
    '04_Product_Operations_Guide_and_Known_Issues.pdf',
    '05_Northstar_Logistics_Enterprise_Agreement.pdf',
    '06_LumenWorks_Service_Agreement.pdf'
]


def read_document(file_name):
    path = os.path.join(DATA_FOLDER, file_name)
    reader = PdfReader(path)
    return '\n'.join(page.extract_text() or '' for page in reader.pages)


def document_metadata(file_name):
    text = read_document(file_name)

    if 'Northstar' in text:
        customer = 'Northstar Logistics'
    elif 'LumenWorks' in text:
        customer = 'LumenWorks'
    else:
        customer = 'ParcelPilot'

    return {
        'document': file_name,
        'deprecated': 'DEPRECATED' in text.upper(),
        'customer': customer,
        'text': text
    }


def _clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def _snippets(text, words, window=260):
    clean = _clean_text(text)
    low = clean.lower()

    hits = []

    for word in words:
        start = 0
        while True:
            pos = low.find(word, start)
            if pos == -1:
                break
            left = max(0, pos - window)
            right = min(len(clean),pos + len(word) + window)
            hits.append(clean[left:right])
            start = pos + len(word)
            if len(hits) >= 4:
                break
        if len(hits) >= 4:
            break

    unique = []
    for item in hits:
        if item not in unique:
            unique.append(item)
    return unique[:3]

def _is_agreement(file_name):
    return 'Agreement' in file_name

def _authority(file_name, deprecated):
    if _is_agreement(file_name):
        return 'SIGNED_CUSTOMER_AGREEMENT'
    if deprecated:
        return 'HISTORICAL_ONLY'
    return 'CURRENT_POLICY_OR_PRODUCT_DOCUMENT'

def search_documents(query, customer=''):
    words = [word.lower() for word in re.findall(r'[a-zA-Z0-9]+', query)if len(word) > 2]
    query_low = query.lower()

    wants_deprecated = ('deprecated' in query_low or 'historical' in query_low or 'old policy' in query_low)

    results = []

    for file_name in DOCUMENTS:
        info = document_metadata(file_name)

        if info['deprecated'] and not wants_deprecated:
            continue

        low = info['text'].lower()

        keyword_score = sum(low.count(word) for word in words)

        if keyword_score == 0:
            continue

        customer_match = False

        if customer:
            customer_match = (customer.lower() in info['customer'].lower() or info['customer'].lower() in customer.lower())

        agreement = _is_agreement(file_name)

        score = keyword_score

        if customer_match:
            score += 20

        if customer_match and agreement:
            score += 100

        snippets = _snippets(info['text'], words)

        results.append({
            'document': file_name,
            'score': score,
            'keyword_score': keyword_score,
            'deprecated': info['deprecated'],
            'customer': info['customer'],
            'customer_match': customer_match,
            'authority': _authority(
                file_name,
                info['deprecated']
            ),
            'snippets': snippets
        })

    results.sort(
        key=lambda x: (
            x['deprecated'],
            x['customer_match'],
            x['authority'] == 'SIGNED_CUSTOMER_AGREEMENT',
            -x['score']
        ),
        reverse=True
    )

    return results[:5]