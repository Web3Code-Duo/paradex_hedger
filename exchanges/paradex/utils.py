from typing import List


def flatten_signature(sig: List[int]) -> str:
    return f'["{sig[0]}","{sig[1]}"]'


def is_token_expired(status_code: int, response: dict) -> bool:
    return (
        True
        if (
            status_code == 401
            and response["message"].startswith(
                "invalid bearer jwt: token is expired by"
            )
        )
        else False
    )
