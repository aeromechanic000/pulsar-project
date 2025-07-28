import os, sys, argparse, logging, time
import asyncio, threading
import signal, atexit
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Add the current directory to the path to import your modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import read_json, get_datetime_stamp, add_log

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global client instance and event loop management
client_instance = None
client_loop = None
client_thread = None
shutdown_event = None

def run_client_loop():
    """Run the client's event loop in a separate thread"""
    global client_loop, shutdown_event
    
    try:
        client_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(client_loop)
        
        # Create a threading event for shutdown signaling
        shutdown_event = threading.Event()
        
        # Simple approach: run forever until shutdown
        async def loop_until_shutdown():
            while not shutdown_event.is_set():
                await asyncio.sleep(0.01)
        
        client_loop.run_until_complete(loop_until_shutdown())
        
    except Exception as e:
        add_log(f"Client loop error: {e}", label="error")
    finally:
        try:
            if client_loop and not client_loop.is_closed():
                client_loop.close()
        except Exception:
            pass

def run_async_in_client_loop(coro):
    """Run async function in the client's event loop"""
    if client_loop is None or client_loop.is_closed():
        raise RuntimeError("Client loop is not running")
    
    # Use asyncio.run_coroutine_threadsafe for cross-thread execution
    future = asyncio.run_coroutine_threadsafe(coro, client_loop)
    try:
        return future.result(timeout=180)
    except Exception as e:
        add_log(f"Error running async function: {e}", label="error")
        raise

def ensure_client_loop():
    """Ensure the client event loop is running"""
    global client_thread, client_loop
    
    if client_thread is None or not client_thread.is_alive():
        client_thread = threading.Thread(target=run_client_loop, daemon=True)
        client_thread.start()
        
        # Wait for the loop to start
        for _ in range(50):  # Wait up to 5 seconds
            time.sleep(0.1)
            if client_loop is not None and not client_loop.is_closed():
                break
        else:
            raise RuntimeError("Failed to start client event loop")

@app.route('/')
def index():
    """Serve the React playground"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# API Routes

@app.route('/api/initialize', methods=['POST'])
def initialize_client():
    """Initialize the MCP client with configuration"""
    global client_instance
    
    try:
        # Ensure the client event loop is running
        ensure_client_loop()
        
        config_data = request.get_json()
        config_path = config_data.get('config_path', 'configs.json')
        
        # Load configuration
        config = read_json(config_path)
        
        # Initialize client in its own event loop
        from client import Client
        client_instance = Client()
        
        # Run initialization in the client's event loop
        run_async_in_client_loop(client_instance.initialize(config))
        
        return jsonify({
            'status': 'success',
            'message': 'Client initialized successfully'
        })
        
    except Exception as e:
        add_log(f"Error initializing client: {e}", label="error")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/config', methods=['GET'])
def get_config_info():
    """Get client configuration information"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        config_info = run_async_in_client_loop(client_instance.get_config_info())
        return jsonify(config_info)
        
    except Exception as e:
        add_log(f"Error getting config info: {e}", label="error")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks with detailed information"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        tasks_data = {}
        for task_id, task in client_instance.task_manager.tasks.items():
            # Convert logs to serializable format
            logs_data = []
            for log in task.logs:
                log_dict = log.to_dict()
                logs_data.append(log_dict)
            
            tasks_data[task_id] = {
                'id': task.task_id,
                'type': task.task_type,
                'title': task.title,
                'target': task.target,
                'plan': task.plan,
                'progress': task.progress,
                'created_at': task.created_at,
                'logs': logs_data,
                'logs_count': len(task.logs),
                'files_count': sum(len(log.files) for log in task.logs),
                'is_working': task_id == client_instance.task_manager.working_task
            }
        
        return jsonify({
            'tasks': tasks_data,
            'working_task_id': client_instance.task_manager.working_task
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task_detail(task_id):
    """Get detailed information about a specific task"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        if task_id not in client_instance.task_manager.tasks:
            return jsonify({'error': 'Task not found'}), 404
        
        task = client_instance.task_manager.tasks[task_id]
        
        # Convert logs to serializable format
        logs_data = []
        for log in task.logs:
            log_dict = log.to_dict()
            logs_data.append(log_dict)
        
        task_data = {
            'id': task.task_id,
            'type': task.task_type,
            'title': task.title,
            'target': task.target,
            'plan': task.plan,
            'progress': task.progress,
            'created_at': task.created_at,
            'logs': logs_data,
            'is_working': task_id == client_instance.task_manager.working_task
        }
        
        return jsonify(task_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/detailed', methods=['GET'])
def get_task_detailed_info(task_id):
    """Get comprehensive task information including all details and files"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        if task_id not in client_instance.task_manager.tasks:
            return jsonify({'error': 'Task not found'}), 404
        
        task = client_instance.task_manager.tasks[task_id]
        
        # Convert logs to serializable format with full file information
        logs_data = []
        for log in task.logs:
            log_dict = log.to_dict()
            logs_data.append(log_dict)
        
        task_data = {
            'id': task.task_id,
            'type': task.task_type,
            'title': task.title,
            'target': task.target,
            'plan': task.plan,
            'progress': task.progress,
            'created_at': task.created_at,
            'logs': logs_data,
            'is_working': task_id == client_instance.task_manager.working_task,
            'logs_count': len(task.logs),
            'files_count': sum(len(log.files) for log in task.logs)
        }
        
        return jsonify(task_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """Get current status of a specific task (lightweight)"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        if task_id not in client_instance.task_manager.tasks:
            return jsonify({'error': 'Task not found'}), 404
        
        task = client_instance.task_manager.tasks[task_id]
        
        # Return lightweight status info
        status_data = {
            'id': task.task_id,
            'target': task.target,
            'plan': task.plan,
            'progress': task.progress,
            'logs_count': len(task.logs),
            'files_count': sum(len(log.files) for log in task.logs),
            'last_updated': task.logs[-1].timestamp if task.logs else task.created_at,
            'is_working': task_id == client_instance.task_manager.working_task
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/new', methods=['POST'])
def create_new_task():
    """Create a new task"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        data = request.get_json()
        task_type = data.get('type', 'plan')
        
        task_id = client_instance.task_manager.new_task(task_type)
        
        if task_id > 0:
            return jsonify({
                'status': 'success',
                'task_id': task_id,
                'message': f'New {task_type} task created'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create task'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/load', methods=['POST'])
def load_task(task_id):
    """Load a specific task as working task"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        result = client_instance.task_manager.load_task(task_id)
        
        if result:
            return jsonify({
                'status': 'success',
                'working_task_id': task_id,
                'message': f'Task {task_id} loaded'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to load task {task_id}'
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory', methods=['GET'])
def get_memory_info():
    """Get memory information"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        memory_data = {
            'records_count': len(client_instance.memory.records),
            'topics': client_instance.memory.topics,
            'database_keys': list(client_instance.memory.database.keys()),
            'summary': client_instance.memory.summary,
            'recent_records': client_instance.memory.records[-10:] if client_instance.memory.records else []
        }
        
        return jsonify(memory_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/operations', methods=['GET'])
def get_memory_operations():
    """Get available memory operations"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        operations = run_async_in_client_loop(client_instance.memory.get_operations())
        return jsonify({'operations': operations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get available tools"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        tools = run_async_in_client_loop(client_instance.server_manager.get_tools())
        return jsonify({'tools': tools})
        
    except Exception as e:
        add_log(f"Error getting tools: {e}", label="error")
        return jsonify({'error': str(e)}), 500

@app.route('/api/memory/details', methods=['GET'])
def get_memory_details():
    """Get detailed memory information including summaries, topics, and database"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        memory_data = {
            'records_count': len(client_instance.memory.records),
            'topics': client_instance.memory.topics,
            'database': client_instance.memory.database,
            'summary': client_instance.memory.summary,
            'recent_records': client_instance.memory.records[-10:] if client_instance.memory.records else []
        }
        
        return jsonify(memory_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def process_chat():
    """Process a chat query"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        response = run_async_in_client_loop(client_instance.process_query(query))
        
        # Get updated task information
        working_task_id = client_instance.task_manager.working_task
        updated_task = None
        if working_task_id and working_task_id in client_instance.task_manager.tasks:
            task = client_instance.task_manager.tasks[working_task_id]
            logs_data = []
            for log in task.logs:
                log_dict = log.to_dict()
                logs_data.append(log_dict)
            
            updated_task = {
                'id': working_task_id,
                'target': task.target,
                'plan': task.plan,
                'progress': task.progress,
                'logs': logs_data,
                'is_working': True,
                'logs_count': len(task.logs),
                'files_count': sum(len(log.files) for log in task.logs)
            }
        
        # Emit real-time update via WebSocket
        socketio.emit('chat_response', {
            'query': query,
            'response': response,
            'updated_task': updated_task,
            'timestamp': get_datetime_stamp()
        })
        
        return jsonify({
            'status': 'success',
            'response': response,
            'updated_task': updated_task
        })
        
    except Exception as e:
        add_log(f"Error processing chat: {e}", label="error")
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/<task_id>/<filename>', methods=['GET'])
def get_file_content(task_id, filename):
    """Get content of a specific file from task logs"""
    if not client_instance:
        return jsonify({'error': 'Client not initialized'}), 400
    
    try:
        task_id = int(task_id)
        if task_id not in client_instance.task_manager.tasks:
            return jsonify({'error': 'Task not found'}), 404
        
        task = client_instance.task_manager.tasks[task_id]
        
        # Search for file in all log records
        for log_record in task.logs:
            if filename in log_record.files:
                file_obj = log_record.files[filename]
                return jsonify({
                    'filename': file_obj.filename,
                    'type': file_obj.type,
                    'content': file_obj.content,
                    'size': file_obj.size,
                    'language': file_obj.language,
                    'format': file_obj.format,
                    'metadata': file_obj.metadata,
                    'timestamp': file_obj.timestamp
                })
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'Connected to MCP Client'})

@socketio.on('disconnect')
def handle_disconnect():
    add_log('Client disconnected')

def cleanup():
    """Clean up resources on shutdown - simplified version"""
    global shutdown_event, client_thread
    
    add_log("Starting cleanup process...")
    
    # Signal shutdown to the event loop
    if shutdown_event:
        shutdown_event.set()
    
    # Wait for client thread to finish
    if client_thread and client_thread.is_alive():
        client_thread.join(timeout=1)  # Reduced timeout since loop is more responsive
        if client_thread.is_alive():
            add_log("Client thread did not shut down gracefully", label="warning")
        else:
            add_log("Client thread shut down gracefully")
    
    add_log("Cleanup completed")

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    add_log(f"Received signal {signum}, shutting down gracefully...")
    cleanup()
    sys.exit(0)

# Register cleanup function
import atexit

atexit.register(cleanup)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Create necessary directories
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('data/memory', exist_ok=True)
os.makedirs('data/task', exist_ok=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Setup and run the program.")
    parser.add_argument('--save-logs', action='store_true', help='Enable log saving')
    args = parser.parse_args()
    # Setup logging

    if args.save_logs :
        logging.basicConfig(
            filename=os.path.join("./logs/flask_log-%s.log" % get_datetime_stamp()),
            filemode='a',
            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S',
            level=logging.DEBUG,
        )
    
    add_log("Starting Flask server on http://localhost:9898")
    
    try:
        socketio.run(app, host='0.0.0.0', port=9898, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        add_log("Server stopped by user")
    except Exception as e:
        add_log(f"Server error: {e}", label="error")
    finally:
        # Cleanup will be called by signal handler or atexit
        pass