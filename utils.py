
import inspect, functools, re, json5
import datetime, json
import math, random
import logging, warnings
warnings.filterwarnings("ignore")

def get_datetime() :
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def get_datetime_stamp() :
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def get_random_label() :
    return "%s_%s" % (get_datetime_stamp(), "%03d" % random.randint(0, 1000))

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