
from utils import *


if __name__ == "__main__" :
    records = [
        "abc", "bca", "word", "word1, wo", "word2", "word3"
    ]
    top_k_records = simple_rag("wo d1", records, 3)
    print(top_k_records)