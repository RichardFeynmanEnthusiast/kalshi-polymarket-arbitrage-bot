from typing import List

from py_clob_client.client import BookParams


def generate_book_params(token_dict) -> List[BookParams]:
    """Generate a list of required params for the call to retrieve order books"""
    book_params = [
        BookParams(token_id=token)
        for condition in token_dict.values()
        for token in condition
    ]
    return book_params