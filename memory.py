
import aiohttp, asyncio
from typing import Optional, Dict, List, Any
from abc import ABC, abstractmethod
from urllib.parse import quote

from provider import *
from utils import *

class MemoryOperation : 
    def __init__(self, name: str, func : Any, config : Dict = None) -> None :
        self.name, self.func = name, func
        self.config = config or {
            "title" : self.name,
            "description" : f"The '{self.name}' operation.",
            "input_schema" : {
                "properties" : {}, 
                "title" : self.name,
                "type" : "object",
                "required" : [],
            },
        }

class MemoryResultTextContent :
    def __init__(self, text : str = "") -> None :
        self.type = "text"
        self.text = text 

class MemoryResultValueContent :
    def __init__(self, value : Any) -> None :
        self.type = "value"
        self.value = value

class MemoryResult :
    def __init__(self, status = 0, error = None, content = None) -> None :
        self.status, self.error = status, error 
        self.content = content or []

class Memory :
    def __init__(self, client, config) : 
        self.client = client
        self.config = config
        self.provider = None

        provider_config = self.config.get("provider", {})
        provider_name = provider_config.get("name", None)
        provider_cls = get_provider(provider_name) 
        if provider_cls is not None : 
            self.provider = provider_cls(provider_config)
            add_log(f"Memery is using provider: {provider_name}")
        else:
            self.provider = self.client.provider
            add_log(f"Memory is using the client's provider.")

        self.records = []
        self.summary, self.topics, self.database = {}, {}, {} 
        self.prepare_operations()

        self.timelabel = f"{get_random_label()}"
        if self.config.get("load_memory", True) : 
            self.load()
    
    async def save(self) -> None :
        """Save memory state to disk."""
        try:
            with open(f"./data/memory/memory-{self.timelabel}.json", "w") as f:
                data = {
                    "records": self.records,
                    "summary": self.summary,
                    "topics": self.topics,
                    "database": self.database,
                }
                json.dump(data, f, indent=4)
            add_log("Memory saved successfully.", label = "success")
        except Exception as e:
            add_log(f"Error saving memory: {e}", label="error")
    
    def load(self) -> None :
        """Load memory state from disk."""
        try:
            with open(f"./data/memory/memory_{self.timelabel}.json", "r") as f:
                data = json.load(f)
                self.records = data.get("records", [])
                self.summary = data.get("summary", {})
                self.topics = data.get("topics", {})
                self.database = data.get("database", {})
            add_log("Memory loaded successfully.", label = "success")
        except FileNotFoundError:
            add_log("No previous memory found, starting fresh.")
        except Exception as e:
            add_log(f"Error loading memory: {e}", label="error")
    
    async def get_static_context(self) -> str : 
        memory_parts = [] 
        memory_parts.append("\n## Available Memory Operations:")
        operations = await self.get_operations()
        for op in operations.values() :
            memory_parts.append(f"- {op['name']}: '{op['description']}")
            memory_parts.append(f"  Input schema: {json.dumps(op['input_schema'])}")
        return "\n".join(memory_parts)

    async def get_dynamic_context(self, query = None) -> str : 
        memory_parts = [] 
        if len(self.records) > 0 :
            memory_parts.append("\n## Latest Memory Records:")
            for record in self.records[- self.config.get("latest_record_num", 10):] :
                memory_parts.append(f"- [{record['timestamp']}] {record['content']}")
        return "\n".join(memory_parts)

    def prepare_operations(self) -> None :
        self.operations = {
            "add_memory_record" : MemoryOperation("add_memory_record", self.add_memory_record, {
                "title" : "Add Memory Record",
                "description" : '''Add a memory to the system.

    Args:
        record: The memory piece in string format to add;
''',
                "input_schema" : {
                    "properties" : {
                        "record" : {
                            "title" : "Record",
                            "type" : "string",
                        },
                    },
                    "title" : "AddMemoryRecordArguments",
                    "type" : "object",
                    "required" : ["record"],
                },
            }),
            "add_memory_data" : MemoryOperation("add_memory_data", self.add_memory_data, {
                "title" : "Add Memory Data",
                "description" : '''Add a key-value pair to the memory database.

    Args:
        key: A key for the data to add;
        value: A string value;
''',
                "input_schema" : {
                    "properties" : {
                        "key" : {
                            "title" : "Key",
                            "type" : "string",
                        },
                        "value" : {
                            "title" : "Value",
                            "type" : "string",
                        },
                    },
                    "title" : "AddMemoryDataArguments",
                    "type" : "object",
                    "required" : ["key", "value"],
                },
            }),
        }
    
    async def get_operations(self, query = None) -> Dict[str, Any] :
        operations = {} 
        for name, info in self.operations.items() :
            if name in self.config.get("ignored_operations", ["add_memory_record", ]) : 
                continue
            operation = {
                "name" : name,
                "title" : info.config.get("title", name),
                "description" : info.config.get("description", ""),
                "input_schema" : info.config.get("input_schema", {"properties" : {}})
            }
            operations[name] = operation
        return operations

    async def call_operation(self, op_name: str, op_args: Dict[str, Any]) -> Dict[str, Any] :
        """Call a memory operation."""
        result = {"status" : 0, "error" : None, "content" : []}
        if op_name in self.operations.keys() :
            op_info = self.operations[op_name]
            try:
                is_args_valid = True 
                for key, value in op_args.items() :
                    if key not in op_info.config["input_schema"]["properties"].keys() : 
                        is_args_valid = False
                        break
                    else :
                        _type = op_info.config["input_schema"]["properties"][key].get("type", "string")
                        if _type == "number" : 
                            if is_int_convertible(value) :
                                op_args[key] = int(value)
                            elif is_float_convertible(value) :
                                op_args[key] = float(value)
                            else :
                                is_args_valid = False
                                break
                        elif _type == "boolean" : 
                            try : 
                                op_args[key] = bool(value)
                            except ValueError :
                                is_args_valid = False
                                break
                        elif _type == "string" : 
                            try : 
                                op_args[key] = str(value)
                            except ValueError :
                                is_args_valid = False
                                break
                if is_args_valid :
                    result = await self.operations[op_name].func(**op_args)
                    return result
                else :
                    raise ValueError(f"Invalid arguments for operation '{op_name}'. Expected: {op_info.config['input_schema']['properties'].keys()}")
            except Exception as e:
                add_log(f"Error calling operation {op_name}: {e}", label = "error")
        raise ValueError(f"Operation {op_name} cannot be found.")
    
    async def add_memory_record(self, memory : str) -> MemoryResult :
        self.records.append({"timestamp" : get_datetime_stamp(), "content" : memory})
        return MemoryResult(status = 0, error = None, content = [MemoryResultTextContent(text = f"Memory record added: {memory}")])

    async def add_memory_data(self, key : str, value : str) -> MemoryResult :
        self.database[key] = value
        return MemoryResult(status = 0, error = None, content = [MemoryResultTextContent(text = f"Memory data added: {key} - {value}")])

    async def get_memory_data(self, key : str) -> MemoryResult :
        if key in self.database.keys() :
            return MemoryResult(status = 0, error = None, content = [MemoryResultValueContent(value = self.database[key])])
        else :
            return MemoryResult(status = 0, error = None, content = [MemoryResultTextContent(text = f"Cannot find any value associated to key '{key}' in memory data.")])

    async def update(self):
        """
        Update the memory summary and current content in topics.
        If a new topic is found, it should be added to the topics. If the topic already exists, it should be updated.
        """
        if not self.records:
            return
        
        # Get recent records that haven't been processed yet
        recent_records = self.records[-self.config.get("update_batch_size", 5):]
        
        if not recent_records:
            return
        
        # Prepare context for the LLM to analyze records
        records_text = "\n".join([f"[{record['timestamp']}] {record['content']}" for record in recent_records])
        
        prompt = f"""Analyze the following memory records and extract:
    1. Key topics/themes present in the records
    2. A brief summary of the main points
    3. Any important data or facts that should be remembered

    Recent Memory Records:
    {records_text}

    Current Topics: {list(self.topics.keys()) if self.topics else 'None'}

    Please respond in JSON format with:
    - "summary": Brief summary of the records
    - "topics": Object with topic names as keys and descriptions as values
    - "key_facts": Array of important facts or data points

    Format your response as JSON only, enclosed in triple backticks."""

        try:
            if self.provider:
                response = await self.provider.generate_response(prompt)
                
                # Extract JSON from response
                content, data = split_content_and_json(response)
                
                # Update summary
                if "summary" in data:
                    current_time = get_datetime_stamp()
                    self.summary[current_time] = data["summary"]
                    
                    # Keep only recent summaries (last 10)
                    if len(self.summary) > 10:
                        oldest_key = min(self.summary.keys())
                        del self.summary[oldest_key]
                
                # Update topics with limit management
                if "topics" in data and isinstance(data["topics"], dict):
                    max_topics = self.config.get("max_topics", 20)  # Default limit of 20 topics
                    
                    for topic, description in data["topics"].items():
                        if topic in self.topics:
                            # Update existing topic
                            self.topics[topic]["description"] = description
                            self.topics[topic]["last_updated"] = get_datetime_stamp()
                            self.topics[topic]["frequency"] = self.topics[topic].get("frequency", 0) + 1
                        else:
                            # Check if we need to make room for new topic
                            if len(self.topics) >= max_topics:
                                # Remove least frequently used and oldest topics
                                topics_by_priority = sorted(
                                    self.topics.items(),
                                    key=lambda x: (x[1].get("frequency", 0), x[1].get("last_updated", ""))
                                )
                                # Remove the lowest priority topic
                                topic_to_remove = topics_by_priority[0][0]
                                del self.topics[topic_to_remove]
                                add_log(f"Removed topic '{topic_to_remove}' to make room for new topic '{topic}'")
                            
                            # Add new topic
                            self.topics[topic] = {
                                "description": description,
                                "created": get_datetime_stamp(),
                                "last_updated": get_datetime_stamp(),
                                "frequency": 1
                            }
                            add_log(f"Added new topic: '{topic}'")
                
                # Store key facts in database
                if "key_facts" in data and isinstance(data["key_facts"], list):
                    for i, fact in enumerate(data["key_facts"]):
                        fact_key = f"fact_{get_datetime_stamp()}_{i}"
                        self.database[fact_key] = str(fact)
                        
                add_log(f"Memory updated successfully. Current topics: {len(self.topics)}/{self.config.get('max_topics', 20)}", label = "success")
                
        except Exception as e:
            add_log(f"Error updating memory: {e}", label="error")
        
        await self.save()
