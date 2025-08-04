
import inspect, functools, re, json5
import datetime, json
import math, random
import logging, warnings
from urllib.parse import urlparse, urlunparse
warnings.filterwarnings("ignore")

def get_datetime() :
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def get_datetime_stamp() :
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def get_random_label() :
    return "%s_%s" % (get_datetime_stamp(), "%03d" % random.randint(0, 1000))

def robust_urljoin(base, path):
    """
    Joins two URLs more robustly, preserving path segments
    without automatic truncation of the base path.
    """
    # Parse the base URL
    base_parsed = urlparse(base)
    
    # Handle cases where base has no path or only a slash
    base_path = base_parsed.path
    if not base_path or base_path == '/':
        combined_path = path
    else:
        # Remove any trailing slashes from base path before joining
        base_path = base_path.rstrip('/')
        # Remove any leading slashes from new path before joining
        path = path.lstrip('/')
        combined_path = f"{base_path}/{path}"
    
    # Reconstruct the URL with the combined path
    joined_parsed = base_parsed._replace(path=combined_path)
    return urlunparse(joined_parsed)

def read_json(filepath, init_cls = dict) :
    data = init_cls()
    with open(filepath, "r") as f :
        data = json.load(f)
    return data


def write_json(data, filepath) :
    result = False
    with open(filepath, "w") as f :
        json.dump(data, f, indent = 4)
        result = True
    return result

class bstyles:
    GREEN = '\033[92m'           
    BLUE = '\033[94m'           
    CYAN = '\033[96m'            
    ORANGE = '\033[38;5;208m'   
    RED = '\033[31m'            
    PINK = '\033[38;5;205m'     
    GRAY = '\033[90m'           
    PURPLE = '\033[35m'         
    YELLOW = '\033[93m'        
    WHITE = '\033[97m'        
    LIGHT_GREEN = '\033[92;1m'  
    LIGHT_CYAN = '\033[96;1m'   
    LIGHT_RED = '\033[91m'      
    LIGHT_PURPLE = '\033[95m'   
    LIGHT_ORANGE = '\033[38;5;214m'
    DARK_BLUE = '\033[34m'      
    DARK_CYAN = '\033[36m'      
    DARK_YELLOW = '\033[33m'   
    DARK_ORANGE = '\033[38;5;166m' 
    BROWN = '\033[38;5;130m'    
    GOLD = '\033[38;5;220m'     
    SILVER = '\033[38;5;246m'   
    LIME = '\033[38;5;118m'    
    MINT = '\033[38;5;159m'     
    LAVENDER = '\033[38;5;183m' 
    ROSE = '\033[38;5;213m'     
    BG_BLACK = '\033[40m'       
    BG_RED = '\033[41m'         
    BG_GREEN = '\033[42m'       
    BG_YELLOW = '\033[43m'      
    BG_BLUE = '\033[44m'        
    BG_PURPLE = '\033[45m'      
    BG_CYAN = '\033[46m'        
    BG_WHITE = '\033[47m'       
    BG_GRAY = '\033[100m'       
    ENDC = '\033[0m'            
    BOLD = '\033[1m'            
    FAINT = '\033[2m'          
    ITALIC = '\033[3m'          
    UNDERLINE = '\033[4m'       
    SLOW_BLINK = '\033[5m'      
    RAPID_BLINK = '\033[6m'     
    INVERT = '\033[7m'          
    HIDE = '\033[8m'            
    STRIKETHROUGH = '\033[9m'   
    DOUBLE_UNDERLINE = '\033[21m' 
    OVERLINE = '\033[53m'        
    RESET_UNDERLINE = '\033[24m' 
    RESET_BOLD = '\033[22m'      
    RESET_INVERT = '\033[27m'    

def print_log(content, label = "log") :
    head_tag, end_tag = "", "" 
    if label == "log" :
        head_tag = bstyles.CYAN
        end_tag = bstyles.ENDC
    elif label == "success" :
        head_tag = bstyles.GREEN
        end_tag = bstyles.ENDC
    elif label == "warning" :
        head_tag = bstyles.YELLOW
        end_tag = bstyles.ENDC
    elif label == "error" :
        head_tag = bstyles.RED
        end_tag = bstyles.ENDC

    print(f"{head_tag}[{get_datetime()}]{end_tag} {content}")

def add_log(content = "", label = "log", print = True) : 
    if label == "error" : 
        logging.error(content)
    elif label == "warning" : 
        logging.warning(content)
    else :  
        logging.info(content)
    if print : 
        print_log(content, label)

def split_content_and_json(text) :
    content, data = text, {}
    mark_pos = [m.start() for m in re.finditer("```", text)]
    for i in range(0, len(mark_pos) - 1) :
        data_start = mark_pos[i]
        data_end = mark_pos[i + 1]
        try :
            json_text = text[(data_start + 3) : data_end].replace("\n", "").replace("\r", "").strip()
            start = json_text.find("{")
            list_start = json_text.find("[")
            if list_start >= 0 and list_start < start :
                start = list_start
            if start >= 0 :
                json_text = json_text[start:]
            for tag in ["html", "css", "python", "javascript", "json", "xml"] :
                if json_text.find(tag) == 0 :
                    json_text = json_text[len(tag):].strip()
                    break
            data = json5.loads(json_text)
            content = text[:data_start].strip() + "\n" + text[min(len(text), data_end + 3):].strip()
        except Exception as e :
            content, data = text, {}
        if type(data) == dict and len(data) > 0 :
            break
    if len(data) < 1 : 
        try : 
            data = json5.loads(text)
        except Exception as e :
            data = {}
    return content, data

def is_int_convertible(value):
    try:
        # First, try converting to a float to handle cases like "5.0"
        f = float(value)
        # Then, check if the float has no fractional part
        return f.is_integer()
    except ValueError:
        return False

def is_float_convertible(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def is_boolean_convertible(value):
    """
    Determines if a value represents a boolean (true or false)
    
    Args:
        value: The value to check
        
    Returns:
        bool: True if the value represents true/false, False otherwise
    """
    # Check for actual boolean values
    if isinstance(value, bool):
        return True
        
    # Check for string representations of boolean values
    if isinstance(value, str):
        lower_val = value.lower()
        return lower_val in {'true', 'false', 't', 'f', 'yes', 'no', 'y', 'n'}
        
    # Check for integer representations (0 = false, 1 = true in some contexts)
    if isinstance(value, int):
        return value in (0, 1)
        
    return False

def convert_to_boolean(value):
    """
    Converts a value to a boolean based on common representations of true/false.
    
    Args:
        value: The value to convert (can be string, int, bool, etc.)
        
    Returns:
        bool: Corresponding boolean value
        
    Raises:
        ValueError: If the value cannot be converted to a boolean
    """
    # Handle actual boolean values
    if isinstance(value, bool):
        return value
    
    # Handle string representations (case-insensitive)
    if isinstance(value, str):
        lower_val = value.lower()
        if lower_val in {'true', 't', 'yes', 'y'}:
            return True
        elif lower_val in {'false', 'f', 'no', 'n'}:
            return False
            
    # Handle integer representations
    if isinstance(value, int):
        if value == 1:
            return True
        elif value == 0:
            return False
            
    # Handle float representations that are whole numbers
    if isinstance(value, float):
        if value.is_integer():
            return convert_to_boolean(int(value))
            
    # If none of the above, it's not convertible
    raise ValueError(f"Cannot convert {repr(value)} to a boolean")
    
def truncate_string(s, num) : 
    return s[: min(len(s), num)]

def clean_string(s):
    s = s.lower()
    s = re.sub(r'[^\w\s]', '', s)
    return s

def count_words_in_string(s, keywords):
    count = 0
    for word in keywords :
        if word in s :
            count += 1
    return count

common_english_words = {
    "the", "and", "of", "a", "to", "in", "is", "you", "that", "it",
    "he", "was", "for", "on", "are", "as", "with", "his", "they", "I",
    "at", "be", "this", "have", "from", "or", "one", "had", "by", "word",
    "but", "not", "what", "all", "were", "we", "when", "your", "can",
    "said", "there", "use", "an", "each", "which", "she", "do", "how",
    "their", "if", "will", "up", "other", "about", "out", "many", "then",
    "them", "these", "so", "some", "her", "would", "make", "like",
    "him", "into", "time", "has", "look", "two", "more", "write",
    "go", "see", "number", "no", "way", "could", "people", "my",
    "than", "first", "water", "been", "call", "who", "oil", "its",
    "now", "find", "long", "down", "day", "did", "get", "come",
    "made", "may", "part"
}

# Define a set of common Chinese words
common_chinese_words = {
    "的", "一", "是", "不", "在", "人", "有", "我", "他", "这",
    "个", "上", "们", "来", "到", "时", "大", "地", "为",
    "子", "中", "你", "说", "生", "国", "年", "着", "就", "那",
    "和", "要", "她", "出", "也", "得", "里", "后", "自", "以",
    "会", "家", "可", "下", "而", "过", "天", "去", "能", "对",
    "小", "多", "然", "于", "心", "学", "么", "之", "都", "好",
    "看", "起", "发", "当", "没", "成", "只", "如", "事", "把",
    "还", "用", "第", "样", "道", "想", "作", "种", "开", "美",
    "总", "从", "无", "情", "己", "面", "最", "女", "但", "现",
    "前", "些", "所", "同", "日", "手", "又", "行", "意", "动",
    "方", "期", "它", "头", "经", "长", "儿"
}

def get_keywords(text):
    words = []
    temp_word = ""
    for char in text :
        if '\u4e00' <= char <= '\u9fff':
            if temp_word:
                if temp_word.lower() not in common_english_words:
                    words.append(temp_word)
                temp_word = ""
            if len(char.strip) > 0 and char not in common_chinese_words:
                words.append(char)
        else:
            if char.isalnum():
                temp_word += char
            else:
                if temp_word :
                    if temp_word.lower() not in common_english_words:
                        words.append(temp_word)
                    temp_word = ""
                if len(char.strip()) > 0 :
                    words.append(char)
    temp_word = temp_word.strip()
    if len(temp_word) > 0 :
        if temp_word.lower() not in common_english_words:
            words.append(temp_word)
    return words

def get_top_k_records(keywords, records, top_k) :
    result = []
    for i, s in enumerate(records) :
        result.append((i, s, count_words_in_string(s, keywords)))
    result.sort(key = lambda x: x[2], reverse=True)
    result = result[:top_k]
    return result

def simple_rag(query, records, top_k = 5) : 
    keywords = get_keywords(clean_string(query))
    print(keywords)
    top_k_result = get_top_k_records(keywords, [clean_string(r) for r in records], top_k)
    return [item[:2] for item in top_k_result]