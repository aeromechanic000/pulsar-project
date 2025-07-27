import re, aiohttp
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import quote

from provider import *
from utils import *

@dataclass
class ExtractedFile:
    """Represents a file extracted from response content"""
    filename: str
    type: str  # code, data, html, article, config
    content: str
    size: int
    timestamp: str
    language: Optional[str] = None
    format: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "type": self.type,
            "content": self.content,
            "size": self.size,
            "timestamp": self.timestamp,
            "language": self.language,
            "format": self.format,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractedFile':
        return cls(
            filename=data["filename"],
            type=data["type"],
            content=data["content"],
            size=data["size"],
            timestamp=data["timestamp"],
            language=data.get("language"),
            format=data.get("format"),
            metadata=data.get("metadata", {})
        )

class TaskLogRecord:
    """Represents a single log record in task history"""
    
    def __init__(self, timestamp: str = None, query: str = "", response_summary: str = ""):
        self.timestamp = timestamp or get_datetime_stamp()
        self.query = query
        self.response_summary = response_summary
        self.entries: List[str] = []
        self.files: Dict[str, ExtractedFile] = {}
        self.metadata: Dict[str, Any] = {}
        self.error: Optional[str] = None
    
    def add_entry(self, entry: str):
        """Add a log entry"""
        self.entries.append(str(entry))
    
    def add_entries(self, entries: List[str]):
        """Add multiple log entries"""
        for entry in entries:
            self.add_entry(entry)
    
    def add_file(self, extracted_file: ExtractedFile):
        """Add an extracted file to this log record"""
        self.files[extracted_file.filename] = extracted_file
        self.add_entry(f"Extracted file: {extracted_file.filename} ({extracted_file.type}, {extracted_file.size} chars)")
    
    def add_files(self, files: Dict[str, ExtractedFile]):
        """Add multiple extracted files"""
        for filename, file_obj in files.items():
            self.add_file(file_obj)
    
    def set_error(self, error: str):
        """Set error information"""
        self.error = error
        self.add_entry(f"Error occurred: {error}")
    
    def get_file_summary(self) -> str:
        """Get a summary of extracted files"""
        if not self.files:
            return "No files extracted"
        
        file_types = {}
        for file_obj in self.files.values():
            file_types[file_obj.type] = file_types.get(file_obj.type, 0) + 1
        
        summary_parts = []
        for file_type, count in file_types.items():
            summary_parts.append(f"{count} {file_type} file(s)")
        
        return f"Extracted {len(self.files)} files: " + ", ".join(summary_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary for serialization"""
        return {
            "timestamp": self.timestamp,
            "query": self.query,
            "response_summary": self.response_summary,
            "entries": self.entries,
            "files": {filename: file_obj.to_dict() for filename, file_obj in self.files.items()},
            "metadata": self.metadata,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskLogRecord':
        """Create log record from dictionary"""
        record = cls(
            timestamp=data.get("timestamp"),
            query=data.get("query", ""),
            response_summary=data.get("response_summary", "")
        )
        record.entries = data.get("entries", [])
        record.metadata = data.get("metadata", {})
        record.error = data.get("error")
        
        # Reconstruct files
        files_data = data.get("files", {})
        for filename, file_data in files_data.items():
            record.files[filename] = ExtractedFile.from_dict(file_data)
        
        return record

class FileExtractor:
    """Utility class for extracting different types of content from text"""
    
    @staticmethod
    def get_file_extension(language: str) -> str:
        """Get appropriate file extension for programming language."""
        extension_map = {
            'python': 'py', 'javascript': 'js', 'typescript': 'ts', 'java': 'java',
            'cpp': 'cpp', 'c': 'c', 'csharp': 'cs', 'php': 'php', 'ruby': 'rb',
            'go': 'go', 'rust': 'rs', 'swift': 'swift', 'kotlin': 'kt', 'scala': 'scala',
            'html': 'html', 'css': 'css', 'sql': 'sql', 'bash': 'sh', 'shell': 'sh',
            'powershell': 'ps1', 'yaml': 'yml', 'json': 'json', 'xml': 'xml',
            'markdown': 'md', 'text': 'txt'
        }
        return extension_map.get(language.lower(), 'txt')
    
    @classmethod
    def extract_code_blocks(cls, text: str) -> List[ExtractedFile]:
        """Extract code blocks from text"""
        files = []
        code_pattern = r'```(\w+)?\n(.*?)\n```'
        code_matches = re.findall(code_pattern, text, re.DOTALL)
        
        for i, (language, code_content) in enumerate(code_matches):
            if code_content.strip():
                language = language or "text"
                filename = f"code_block_{i+1}.{cls.get_file_extension(language)}"
                
                file_obj = ExtractedFile(
                    filename=filename,
                    type="code",
                    content=code_content.strip(),
                    size=len(code_content.strip()),
                    timestamp=get_datetime_stamp(),
                    language=language,
                    metadata={"block_index": i+1}
                )
                files.append(file_obj)
        
        return files
    
    @classmethod
    def extract_structured_data(cls, text: str) -> List[ExtractedFile]:
        """Extract structured data (JSON, YAML, XML, etc.)"""
        files = []
        
        # Patterns for different data formats
        patterns = {
            'json': r'```json\n(.*?)\n```',
            'yaml': r'```ya?ml\n(.*?)\n```',
            'toml': r'```toml\n(.*?)\n```',
            'xml': r'```xml\n(.*?)\n```',
            'ini': r'```ini\n(.*?)\n```'
        }
        
        for data_format, pattern in patterns.items():
            matches = re.findall(pattern, text, re.DOTALL)
            for i, content in enumerate(matches):
                if content.strip():
                    filename = f"data_{len(files)+1}.{data_format}"
                    
                    file_obj = ExtractedFile(
                        filename=filename,
                        type="data",
                        content=content.strip(),
                        size=len(content.strip()),
                        timestamp=get_datetime_stamp(),
                        format=data_format,
                        metadata={"data_index": i+1}
                    )
                    files.append(file_obj)
        
        return files
    
    @classmethod
    def extract_html_content(cls, text: str) -> List[ExtractedFile]:
        """Extract HTML content"""
        files = []
        html_pattern = r'```html\n(.*?)\n```'
        html_matches = re.findall(html_pattern, text, re.DOTALL)
        
        for i, html_content in enumerate(html_matches):
            if html_content.strip():
                filename = f"webpage_{i+1}.html"
                
                file_obj = ExtractedFile(
                    filename=filename,
                    type="html",
                    content=html_content.strip(),
                    size=len(html_content.strip()),
                    timestamp=get_datetime_stamp(),
                    format="html",
                    metadata={"html_index": i+1}
                )
                files.append(file_obj)
        
        return files
    
    @classmethod
    def extract_articles(cls, text: str) -> List[ExtractedFile]:
        """Extract article-like markdown content"""
        files = []
        lines = text.split('\n')
        article_content = []
        in_article = False
        article_count = 0
        
        for line in lines:
            # Detect article-like content (headers, paragraphs)
            if line.startswith('#') or (line.strip() and len(line.strip()) > 50 and not line.startswith('```')):
                if not in_article:
                    in_article = True
                    article_content = []
                article_content.append(line)
            elif in_article and line.strip() == '':
                article_content.append(line)
            elif in_article and (line.startswith('```') or len(article_content) > 5):
                # End of article-like content
                if len(article_content) > 5:  # Minimum lines for an article
                    article_text = '\n'.join(article_content).strip()
                    if len(article_text) > 200:  # Minimum length for an article
                        article_count += 1
                        filename = f"article_{article_count}.md"
                        
                        file_obj = ExtractedFile(
                            filename=filename,
                            type="article",
                            content=article_text,
                            size=len(article_text),
                            timestamp=get_datetime_stamp(),
                            format="markdown",
                            metadata={"article_index": article_count, "line_count": len(article_content)}
                        )
                        files.append(file_obj)
                
                in_article = False
                article_content = []
        
        return files
    
    @classmethod
    def extract_all_content(cls, text: str) -> List[ExtractedFile]:
        """Extract all types of content from text"""
        all_files = []
        all_files.extend(cls.extract_code_blocks(text))
        all_files.extend(cls.extract_structured_data(text))
        all_files.extend(cls.extract_html_content(text))
        all_files.extend(cls.extract_articles(text))
        return all_files

class Task(ABC):
    def __init__(self, client, provider, task_id: int, task_type: str) :
        self.client, self.provider = client, provider
        self.task_id, self.task_type = task_id, task_type
        self.title = f"Task {task_id}"  # Default title
        self.target, self.plan, self.progress = "", "", ""
        self.logs = []
        self.created_at = get_datetime_stamp()
    
    async def get_static_context(self):
        task_parts = [] 
        return "\n".join(task_parts)

    async def get_dynamic_context(self):
        task_parts = [
            f"Current Task ID: {self.task_id}",
            f"Current Title: {self.title}",
            f"Current Target: {self.target or 'Not set'}",
            f"Current Plan: {self.plan or 'Not set'}",
            f"Current Progress: {self.progress or 'Not started'}",
        ] 
        return "\n".join(task_parts)

    def update_title_from_target(self):
        """Extract a meaningful title from the target"""
        if not self.target:
            return
        
        # Simple title extraction - take first sentence or first 50 chars
        target_clean = self.target.strip()
        if '.' in target_clean:
            title = target_clean.split('.')[0].strip()
        else:
            title = target_clean[:50].strip()
        
        # Remove common prefixes
        prefixes_to_remove = ['create', 'build', 'develop', 'make', 'generate', 'write']
        words = title.lower().split()
        if words and words[0] in prefixes_to_remove:
            title = ' '.join(title.split()[1:])
        
        # Capitalize and limit length
        if title:
            self.title = title[:60].strip().title()

class PlanTask(Task):
    async def get_static_context(self):
        task_parts = []
        return "\n".join(task_parts)

class ResearchTask(Task):
    pass

class TaskManager:
    def __init__(self, client):
        self.client = client
        self.provider = None
        self.config, self.tasks = {}, {} 
        self.working_task = None
        self.next_task_id = 1  # Track next available task ID
    
    def get_working_task(self) -> Optional[Task]:
        if self.working_task in self.tasks.keys():
            return self.tasks[self.working_task]
        return None
    
    def get_working_logs(self) -> List[Dict[str, Any]]:
        task = self.get_working_task()
        if task is not None:
            return task.logs
        return []
    
    def get_working_target(self) -> str:
        task = self.get_working_task()
        if task is not None:
            return task.target
        return ""
    
    def get_working_plan(self) -> str:
        task = self.get_working_task()
        if task is not None:
            return task.plan
        return ""
    
    def get_working_progress(self) -> str:
        task = self.get_working_task()
        if task is not None:
            return task.progress
        return ""
    
    def get_working_task_id(self) -> int:
        return self.working_task if self.working_task is not None else -1
    
    def load_config(self, config):
        self.config = config

        provider_config = self.config.get("provider", {})
        provider_name = provider_config.get("name", None)
        provider_cls = get_provider(provider_name) 
        if provider_cls is not None: 
            self.provider = provider_cls(provider_config)
            add_log(f"TaskManager is using provider: {provider_name}")
        else:
            self.provider = self.client.provider
            add_log(f"TaskManager is using client's provider.")

        self.new_task()
    
    def new_task(self, task_type: str = "plan") -> int:
        task_id = self.next_task_id
        
        if task_type == "plan":
            task = PlanTask(self.client, self.provider, task_id, "plan")
        elif task_type == "research":
            task = ResearchTask(self.client, self.provider, task_id, "research")
        else:
            return -1

        self.tasks[task_id] = task
        self.working_task = task_id
        self.next_task_id += 1

        add_log(f"Created new {task_type} task with ID: {task_id}")
        return task_id
    
    def load_task(self, task_id: int) -> bool:
        if task_id in self.tasks.keys():
            self.working_task = task_id
            add_log(f"Loaded task with ID: {task_id}")
            return True
        return False
    
    async def get_static_context(self) -> str:
        working_task = self.get_working_task()
        if working_task is not None:
            return await working_task.get_static_context()
        return ""

    async def get_dynamic_context(self) -> str:
        working_task = self.get_working_task()
        if working_task is not None:
            return await working_task.get_dynamic_context()
        return ""
        
    async def update(self, query, response):
        """
        Update target, plan and progress based on the query and response.
        When the target is empty, it should figure out the target at first, and then work on the plan and update the progress.
        """
        if self.working_task not in self.tasks:
            return
        
        current_task = self.tasks[self.working_task]
        
        # Prepare context for analysis
        response_text = "\n".join([msg["content"] for msg in response if isinstance(msg.get("content"), str)])
        
        # Create new log record
        response_summary_limit = self.config.get("response_summary_limit", 200)
        log_record = TaskLogRecord(
            query=query,
            response_summary=response_text[:response_summary_limit] + "..." if len(response_text) > response_summary_limit else response_text
        )
        
        # Extract file content from response
        try:
            extracted_files = FileExtractor.extract_all_content(response_text)
            
            # Add extracted files to log record
            for file_obj in extracted_files:
                log_record.add_file(file_obj)
                
            if extracted_files:
                log_record.add_entry(f"Content extraction completed: {log_record.get_file_summary()}")
                
        except Exception as e:
            log_record.set_error(f"File extraction failed: {str(e)}")
            add_log(f"Error extracting files: {e}", label="error")
        
        # Build prompt based on current task state
        prompt_parts = [
            "Analyze the following user query and assistant response to update the task information.",
            f"Current Task ID: {current_task.task_id}",
            f"Current Title: {current_task.title}",
            f"Current Target: {current_task.target or 'Not set'}",
            f"Current Plan: {current_task.plan or 'Not set'}",
            f"Current Progress: {current_task.progress or 'Not started'}",
            f"\nUser Query: {query}",
            f"Assistant Response: {response_text}",
        ]
        
        if log_record.files:
            prompt_parts.append(f"\nExtracted Files/Content: {list(log_record.files.keys())}")
        
        if not current_task.target:
            # Focus on identifying the target first
            prompt_parts.extend([
                "\nThe task target is not set. Please:",
                "1. Identify the main objective or goal from the conversation",
                "2. Set a clear, specific target",
                "3. Extract a short, meaningful title for this task (max 60 characters)",
                "4. Create an initial plan with key steps",
                "5. Set initial progress status"
            ])
        else:
            # Update existing task
            prompt_parts.extend([
                "\nThe task already has a target. Please:",
                "1. Keep the target unless it needs significant modification", 
                "2. Update the title if the target has changed significantly",
                "3. Update the plan based on new information or progress",
                "4. Update progress to reflect current status",
                "5. Add any new insights or obstacles discovered"
            ])
        
        prompt_parts.append("""
Please respond in JSON format with:
- "target": Clear statement of the main objective
- "title": Short, descriptive title for the task (max 60 characters)
- "plan": Detailed plan with numbered steps
- "progress": Current progress description
- "logs": Array of new log entries about what happened

Format your response as JSON only, enclosed in triple backticks.""")
        
        prompt = "\n".join(prompt_parts)
        
        try:
            if self.provider:
                llm_response = await self.provider.generate_response(prompt)
                
                # Extract JSON from response
                from utils import split_content_and_json
                content, data = split_content_and_json(llm_response)
                
                # Update task fields
                if "target" in data and data["target"]:
                    current_task.target = str(data["target"])
                    log_record.add_entry(f"Target updated: {current_task.target}")
                    add_log(f"Task target updated: {current_task.target}")
                    
                    # Auto-update title when target changes
                    current_task.update_title_from_target()
                
                # Update title if provided
                if "title" in data and data["title"]:
                    current_task.title = str(data["title"])[:60]  # Limit title length
                    log_record.add_entry(f"Title updated: {current_task.title}")
                    add_log(f"Task title updated: {current_task.title}")
                
                if "plan" in data and data["plan"]:
                    current_task.plan = str(data["plan"])
                    log_record.add_entry("Plan updated")
                    add_log(f"Task plan updated")
                
                if "progress" in data and data["progress"]:
                    current_task.progress = str(data["progress"])
                    log_record.add_entry(f"Progress updated: {current_task.progress}")
                    add_log(f"Task progress updated: {current_task.progress}")
                
                # Add analysis entries from LLM
                if "logs" in data and isinstance(data["logs"], list):
                    log_record.add_entries(data["logs"])
                
                # Add metadata about the update
                log_record.metadata.update({
                    "target_updated": "target" in data,
                    "title_updated": "title" in data,
                    "plan_updated": "plan" in data,
                    "progress_updated": "progress" in data,
                    "files_extracted": len(log_record.files),
                    "update_successful": True
                })
                
        except Exception as e:
            log_record.set_error(f"Task update failed: {str(e)}")
            log_record.metadata["update_successful"] = False
            add_log(f"Error updating task: {e}", label="error")
        
        # Add the log record to task logs
        current_task.logs.append(log_record)
        
        # Maintain log size limit
        max_logs = self.config.get("max_logs", 50)
        if len(current_task.logs) > max_logs:
            current_task.logs = current_task.logs[-max_logs:]
            add_log(f"Trimmed task logs to {max_logs} entries")
        
        files_count = len(log_record.files)
        add_log(f"Task {self.working_task} updated successfully. Files extracted: {files_count}")