const { useState, useEffect, useRef } = React;

// API utilities
const API_BASE = '';

const api = {
    async get(endpoint) {
        const response = await fetch(`${API_BASE}/api${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    },
    
    async post(endpoint, data) {
        const response = await fetch(`${API_BASE}/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }
};

const truncate_string = (str, maxLength) => {
    if (str) {
        return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
    }
    return null
} 

// File type configuration based on your extension map
const FILE_TYPE_CONFIG = {
    // Markdown types (render as markdown)
    'plan': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'guide': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'tutorial': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'recipe': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'article': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'report': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'manual': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'changelog': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    'logbook': { extension: 'md', renderAs: 'markdown', color: 'green', icon: 'fas fa-file-alt' },
    
    // Text types (render as plain text)
    'novel': { extension: 'txt', renderAs: 'text', color: 'yellow', icon: 'fas fa-book' },
    'note': { extension: 'txt', renderAs: 'text', color: 'yellow', icon: 'fas fa-book' },
    'journal': { extension: 'txt', renderAs: 'text', color: 'yellow', icon: 'fas fa-book' },
    'poem': { extension: 'txt', renderAs: 'text', color: 'yellow', icon: 'fas fa-book' },
    'story': { extension: 'txt', renderAs: 'text', color: 'yellow', icon: 'fas fa-book' },
    'dialogue': { extension: 'txt', renderAs: 'text', color: 'yellow', icon: 'fas fa-book' },
    
    // Keep existing types for backward compatibility
    'code': { extension: 'txt', renderAs: 'code', color: 'blue', icon: 'fas fa-code' },
    'data': { extension: 'json', renderAs: 'code', color: 'purple', icon: 'fas fa-database' },
    'html': { extension: 'html', renderAs: 'code', color: 'orange', icon: 'fas fa-globe' }
};

// Helper function to get file type configuration
const getFileTypeConfig = (fileType) => {
    return FILE_TYPE_CONFIG[fileType] || { extension: 'txt', renderAs: 'text', color: 'slate', icon: 'fas fa-file' };
};

// Socket connection
const socket = io();

// Main App Component
function App() {
    const [isInitialized, setIsInitialized] = useState(false);
    const [loading, setLoading] = useState(false);
    const [tasks, setTasks] = useState({});
    const [workingTaskId, setWorkingTaskId] = useState(null);
    const [selectedTaskId, setSelectedTaskId] = useState(null);
    const [selectedLogIndex, setSelectedLogIndex] = useState(null);
    const [selectedDetail, setSelectedDetail] = useState(null);
    const [memory, setMemory] = useState(null);
    const [chatMessages, setChatMessages] = useState([]);
    const [currentQuery, setCurrentQuery] = useState('');
    const [tools, setTools] = useState({});
    const [memoryOps, setMemoryOps] = useState({});
    const [alert, setAlert] = useState({ isOpen: false, title: '', message: '', type: 'info' });
    const [toast, setToast] = useState({ isVisible: false, title: '', message: '', type: 'info' });
    const [showTaskTypeModal, setShowTaskTypeModal] = useState(false);
    const [isPolling, setIsPolling] = useState(false);
    const [isProcessingQuery, setIsProcessingQuery] = useState(false);
    const [pollDuringProcessing, setPollDuringProcessing] = useState(false);
    const [statusMessage, setStatusMessage] = useState('');
    const [statusType, setStatusType] = useState('idle'); // 'idle', 'processing', 'polling', 'success', 'error'

    const availableTaskTypes = [
        { 
            type: 'plan', 
            label: 'Plan Task', 
            icon: 'fas fa-tasks', 
            description: 'Create a structured plan for achieving goals',
            color: 'indigo'
        },
        { 
            type: 'research', 
            label: 'Research Task', 
            icon: 'fas fa-search', 
            description: 'Gather and analyze information on topics',
            color: 'emerald'
        }
    ];

    // Alert helper functions
    const showAlert = (title, message, type = 'info') => {
        setAlert({ isOpen: true, title, message, type });
    };

    const closeAlert = () => {
        setAlert({ isOpen: false, title: '', message: '', type: 'info' });
    };

    const showToast = (message, type = 'info', title = '') => {
        setToast({ isVisible: true, title, message, type });
    };

    const closeToast = () => {
        setToast({ isVisible: false, title: '', message: '', type: 'info' });
    };

    // Initialize client
    const initializeClient = async () => {
        setLoading(true);
        try {
            await api.post('/initialize', {});
            setIsInitialized(true);
            await loadAllData();
        } catch (error) {
            showAlert('Initialization Failed', error.message, 'error');
        }
        setLoading(false);
    };
    
    // Load all data
    const loadAllData = async () => {
        try {
            const [tasksData, memoryData, toolsData, memOpsData] = await Promise.all([
                api.get('/tasks'),
                api.get('/memory'),
                api.get('/tools'),
                api.get('/memory/operations')
            ]);
            
            setTasks(tasksData.tasks);
            setWorkingTaskId(tasksData.working_task_id);
            setMemory(memoryData);
            setTools(toolsData.tools);
            setMemoryOps(memOpsData.operations);
        } catch (error) {
            console.error('Failed to load data:', error);
        }
    };

    // Load detailed task data
    const loadTaskDetails = async (taskId) => {
        if (!taskId) return;
        try {
            const taskDetail = await api.get(`/tasks/${taskId}/detailed`);
            setTasks(prev => ({
                ...prev,
                [taskId]: taskDetail
            }));
        } catch (error) {
            console.error('Failed to load task details:', error);
        }
    };
    
    const updateStatus = (message, type = 'idle') => {
        setStatusMessage(message);
        setStatusType(type);
    };

    const clearStatus = () => {
        setStatusMessage('');
        setStatusType('idle');
    };

    // Add polling function
    const pollTaskStatus = async () => {
        if (!workingTaskId || isPolling) return;
        
        try {
            setIsPolling(true);

            if (pollDuringProcessing) {
                updateStatus('Fetching task updates...', 'polling');
            }

            const status = await api.get(`/tasks/${workingTaskId}/status`);
            
            // Check if task has been updated (compare timestamps or log counts)
            const currentTask = tasks[workingTaskId];
            if (currentTask && 
                (status.logs_count !== currentTask.logs_count || 
                status.last_updated !== currentTask.logs?.[currentTask.logs.length - 1]?.timestamp)) {
                
                // Task has been updated, fetch detailed data
                await loadTaskDetails(workingTaskId);

                if (pollDuringProcessing) {
                    updateStatus('Task data refreshed', 'success');
                }
            }
        } catch (error) {
            console.error('Polling error:', error);
            if (pollDuringProcessing) {
                updateStatus('Failed to fetch updates', 'error');
            }
        } finally {
            setIsPolling(false);
        }
    };
    // Send chat message
    const sendMessage = async () => {
        if (!currentQuery.trim()) return;
    
        const userMessage = { role: 'user', content: currentQuery, timestamp: new Date().toISOString() };
        setChatMessages(prev => [...prev, userMessage]);
        
        setLoading(true);
        setIsProcessingQuery(true);  // ** ADD THIS **
        setPollDuringProcessing(true);  // ** ADD THIS **

        updateStatus('Query submitted, processing...', 'processing');

        try {
            const response = await api.post('/chat', { query: currentQuery });

            updateStatus('Response received, updating task data...', 'polling');

            const assistantMessage = {
                role: 'assistant',
                content: response.response,
                timestamp: new Date().toISOString()
            };
            setChatMessages(prev => [...prev, assistantMessage]);
            setCurrentQuery('');
            
            // Update working task if response includes updated task
            if (response.updated_task) {
                setTasks(prev => ({
                    ...prev,
                    [response.updated_task.id]: response.updated_task
                }));
                
                // ** ADD THIS: Load detailed task data for the updated task **
                await loadTaskDetails(response.updated_task.id);
            }
            
            // Refresh general data
            await loadAllData();
            updateStatus('Task data updated successfully', 'success');

            // Clear status after 3 seconds
            setTimeout(() => clearStatus(), 3000);

        } catch (error) {
            updateStatus(`Error: ${error.message}`, 'error');
            // Clear error after 5 seconds
            setTimeout(() => clearStatus(), 5000);

            const errorMessage = {
                role: 'system',
                content: `Error: ${error.message}`,
                timestamp: new Date().toISOString()
            };
            setChatMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
            setIsProcessingQuery(false);  // ** ADD THIS **
            
            // Stop polling after a short delay to catch final updates
            setTimeout(() => {
                setPollDuringProcessing(false);
            }, 3000);
        }
    };

    // Create new task
    const createNewTask = async (type = 'plan') => {
        try {
            await api.post('/tasks/new', { type });
            await loadAllData();
        } catch (error) {
            showToast(`Failed to create task: ${error.message}`, 'error');
        }
    };

    // Load task
    const loadTask = async (taskId) => {
        try {
            await api.post(`/tasks/${taskId}/load`);
            await loadAllData();
        } catch (error) {
            showToast(`Failed to load task: ${error.message}`, 'error');

        }
    };

    // Show memory details
    const showMemoryDetails = async () => {
        try {
            const memoryDetails = await api.get('/memory/details');
            setSelectedDetail({ type: 'memory', data: memoryDetails });
        } catch (error) {
            showAlert('Memory Error', `Failed to load memory details: ${error.message}`, 'error');
        }
    };

    const showConfigDetails = async () => {
        try {
            const configDetails = await api.get('/config');
            setSelectedDetail({ type: 'config', data: configDetails });
        } catch (error) {
            showAlert('Configuration Error', `Failed to load configuration details: ${error.message}`, 'error');
        }
    };
    
    useEffect(() => {
        if (!workingTaskId || !pollDuringProcessing) return;
        
        const pollInterval = setInterval(pollTaskStatus, 1000); // More frequent during processing
        
        return () => clearInterval(pollInterval);
    }, [workingTaskId, pollDuringProcessing]);

    // Socket listeners
    useEffect(() => {
        socket.on('chat_response', (data) => {
            if (data.updated_task) {
                setTasks(prev => ({
                    ...prev,
                    [data.updated_task.id]: data.updated_task
                }));
            }
        });

        return () => {
            socket.off('chat_response');
        };
    }, []);

    // Load working task details when workingTaskId changes
    useEffect(() => {
        if (workingTaskId) {
            loadTaskDetails(workingTaskId);
        }
    }, [workingTaskId]);

    if (!isInitialized) {
        return <InitializationScreen onInitialize={initializeClient} loading={loading} />;
    }

    return (
        <div className="min-h-screen bg-slate-50">
            <Header onRefresh={loadAllData} />
            <div className={`layout-container pt-16 ${selectedDetail ? 'details-open' : ''}`}>
                <TaskSidebar
                    tasks={tasks}
                    workingTaskId={workingTaskId}
                    selectedTaskId={selectedTaskId}
                    onSelectTask={setSelectedTaskId}
                    onLoadTask={loadTask}
                    onShowTaskTypeModal={() => setShowTaskTypeModal(true)}
                />
                <div className="chat-container">
                    <ChatArea
                        messages={chatMessages}
                        currentQuery={currentQuery}
                        onQueryChange={setCurrentQuery}
                        onSendMessage={sendMessage}
                        onShowMemory={showMemoryDetails}
                        onShowConfig={showConfigDetails}
                        loading={loading}
                        onShowDetail={setSelectedDetail}
                    />
                </div>
                <TaskPanel
                    task={tasks[workingTaskId]}
                    selectedLogIndex={selectedLogIndex}
                    onSelectLog={setSelectedLogIndex}
                    onShowDetail={setSelectedDetail}
                />
                <DetailsPanel
                    detail={selectedDetail}
                    onClose={() => setSelectedDetail(null)}
                    isOpen={!!selectedDetail}
                    onShowDetail={setSelectedDetail}
                />
            </div>
            <StatusBar message={statusMessage} type={statusType} />
            <TaskTypeModal
                isOpen={showTaskTypeModal}
                onClose={() => setShowTaskTypeModal(false)}
                onCreateTask={createNewTask}
                availableTypes={availableTaskTypes}
            />
            <AlertModal
                isOpen={alert.isOpen}
                onClose={closeAlert}
                title={alert.title}
                message={alert.message}
                type={alert.type}
            />
            <Toast
                isVisible={toast.isVisible}
                onClose={closeToast}
                title={toast.title}
                message={toast.message}
                type={toast.type}
            />
        </div>
    );
}

// Initialization Screen (unchanged)
function InitializationScreen({ onInitialize, loading }) {
    return (
        <div className="min-h-screen gradient-bg flex items-center justify-center p-6">
            <div className="glass-effect rounded-2xl p-8 max-w-md w-full text-center text-white animate-fade-in">
                <div className="mb-6">
                    <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i className="fas fa-robot text-2xl"></i>
                    </div>
                    <h1 className="text-3xl font-bold mb-2">Pulsar Agent</h1>
                </div>
                
                <div className="space-y-4">
                    <p className="text-white text-opacity-90">
                        Initialize the playground to start exploring with the self-learning and evolving AI.
                    </p>
                    
                    <button
                        onClick={onInitialize}
                        disabled={loading}
                        className="w-full bg-white bg-opacity-20 hover:bg-opacity-30 backdrop-blur-sm border border-white border-opacity-30 text-white font-medium py-3 px-6 rounded-xl transition-all duration-200 hover-lift disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center">
                                <i className="fas fa-spinner fa-spin mr-2"></i>
                                Initializing...
                            </span>
                        ) : (
                            <span className="flex items-center justify-center">
                                <i className="fas fa-play mr-2"></i>
                                Start Playground
                            </span>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

// Header Component (unchanged)
function Header({ onRefresh }) {
    return (
        <header className="fixed top-0 left-0 right-0 bg-white border-b-2 border-slate-200 z-50 shadow-sm">
            <div className="flex items-center justify-between px-6 py-4">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center">
                        <img src="/static/icon.png" alt="Pulsar Agent" className="w-full h-full object-cover" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-slate-800">Pulsar Agent</h1>
                        <p className="text-xs text-slate-500">Agentic AI for Learning and Evolving</p>
                    </div>
                </div>
                
                <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-2 text-xs text-slate-500">
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                        <span>Connected</span>
                    </div>
                    <button
                        onClick={onRefresh}
                        className="bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 hover-lift"
                    >
                        <i className="fas fa-sync mr-2"></i>Refresh
                    </button>
                </div>
            </div>
        </header>
    );
}

// Task Sidebar Component (unchanged)
function TaskSidebar({ tasks, workingTaskId, selectedTaskId, onSelectTask, onLoadTask, onShowTaskTypeModal }) {
    return (
        <div className="task-sidebar bg-white panel-border flex flex-col">
            <div className="p-6 border-b-2 border-slate-100">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold text-slate-800">Tasks</h2>
                    <span className="bg-slate-100 text-slate-600 text-xs font-medium px-2 py-1 rounded-full">
                        {Object.keys(tasks).length}
                    </span>
                </div>
                
                <div className="flex space-x-2">
                    <button
                        onClick={() => onShowTaskTypeModal(true)} // You'll need to pass this as a prop
                        className="w-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover-lift"
                        title="Create New Task"
                    >
                        <i className="fas fa-plus mr-2"></i>Create Task
                    </button>
                </div>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {Object.values(tasks).length === 0 ? (
                    <div className="p-6 text-center text-slate-500">
                        <i className="fas fa-tasks text-3xl mb-3 text-slate-300"></i>
                        <p className="text-sm">No tasks yet</p>
                        <p className="text-xs mt-1">Create your first task to get started</p>
                    </div>
                ) : (
                    <div className="p-4 space-y-3">
                        {Object.values(tasks).map(task => (
                            <TaskCard
                                key={task.id}
                                task={task}
                                isSelected={selectedTaskId === task.id}
                                isWorking={workingTaskId === task.id}
                                onSelect={() => onSelectTask(task.id)}
                                onLoad={() => onLoadTask(task.id)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

// Task Card Component (unchanged)
function TaskCard({ task, isSelected, isWorking, onSelect, onLoad }) {
    return (
        <div
            className={`relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 hover-lift animate-fade-in ${
                isSelected 
                    ? 'border-indigo-200 bg-indigo-50 shadow-md' 
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
            } ${isWorking ? 'ring-2 ring-emerald-200' : ''}`}
            onClick={onSelect}
        >
            
            <div className="flex justify-between items-start mb-3">
                <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-800">{truncate_string(task.title, 10) || `Task ${task.id}`}</span>
                    <span className="bg-slate-100 text-black-700 text-xs font-medium px-2 py-1 rounded-full">
                       {task.type} 
                    </span>
                    {isWorking && (
                        <span className="bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-1 rounded-full">
                            Active
                        </span>
                    )}
                </div>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onLoad();
                    }}
                    className="bg-slate-100 hover:bg-slate-200 text-slate-600 p-1.5 rounded-lg text-xs transition-colors duration-200"
                    title="Load Task"
                >
                    <i className="fas fa-play"></i>
                </button>
            </div>
            
            <div className="space-y-2">
                <div>
                    <p className="text-xs font-medium text-slate-600 mb-1">Target</p>
                    <p className="text-sm text-slate-800 line-clamp-2">
                        {task.target || 'No target set'}
                    </p>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="flex items-center">
                        <i className="fas fa-list-ul mr-1"></i>
                        {task.logs_count || task.log_count || 0} logs
                    </span>
                    <span className="flex items-center">
                        <i className="fas fa-calendar mr-1"></i>
                        {new Date(task.created_at).toLocaleDateString()}
                    </span>
                </div>
            </div>
        </div>
    );
}

// Chat Area Component (unchanged from previous version)
function ChatArea({ messages, currentQuery, onQueryChange, onSendMessage, onShowMemory, onShowConfig, loading, onShowDetail }) {

    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSendMessage();
        }
    };

    const handleInputChange = (e) => {
        onQueryChange(e.target.value);
        
        // Auto-resize textarea
        const textarea = e.target;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    };

    const characterCount = currentQuery.length;
    const maxLength = 2000;

    return (
        <>
            <div className="chat-header">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold text-slate-800">Conversation</h2>
                        <p className="text-sm text-slate-500">Chat with your AI assistant</p>
                    </div>
                    <div className="flex items-center space-x-3">
                        <button
                            onClick={onShowConfig}
                            className="bg-blue-50 hover:bg-blue-100 text-blue-700 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover-lift"
                            title="View Configuration"
                        >
                            <i className="fas fa-cog mr-2"></i>Config
                        </button>
                        <button
                            onClick={onShowMemory}
                            className="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover-lift"
                            title="View Memory"
                        >
                            <i className="fas fa-brain mr-2"></i>Memory
                        </button>
                        <div className="text-sm text-slate-500">
                            {messages.length} messages
                        </div>
                    </div>
                </div>
            </div>

            <div className="chat-messages custom-scrollbar">
                {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center text-slate-400">
                            <i className="fas fa-comments text-4xl mb-4"></i>
                            <p className="text-lg mb-2">Start a conversation</p>
                            <p className="text-sm">Ask questions, request tasks, or explore ideas</p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {messages.map((message, index) => (
                            <ChatMessage
                                key={index}
                                message={message}
                                onShowDetail={onShowDetail}
                            />
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>
            
            <div className="chat-input-container">
                <div className="input-group">
                    <div className="input-wrapper">
                        <textarea
                            ref={textareaRef}
                            value={currentQuery}
                            onChange={handleInputChange}
                            onKeyPress={handleKeyPress}
                            placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
                            className="chat-input w-full px-4 py-3 pr-16"
                            disabled={loading}
                            maxLength={maxLength}
                            rows={1}
                        />
                        <div className="input-counter">
                            {characterCount}/{maxLength}
                        </div>
                    </div>
                    <button
                        onClick={onSendMessage}
                        disabled={loading || !currentQuery.trim()}
                        className="send-button text-white"
                        title="Send message"
                    >
                        {loading ? (
                            <i className="fas fa-spinner fa-spin"></i>
                        ) : (
                            <i className="fas fa-paper-plane"></i>
                        )}
                    </button>
                </div>
            </div>
        </>
    );
}

function ChatMessage({ message, onShowDetail }) {
    if (message.role === 'user') {
        return (
            <div className="flex justify-end animate-fade-in">
                <div className="bg-indigo-500 text-white p-4 rounded-2xl rounded-br-lg max-w-2xl shadow-sm">
                    <MarkdownContent content={message.content} className="text-white markdown-content-light" />
                    <div className="text-xs text-indigo-100 mt-2 text-right">
                        {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                </div>
            </div>
        );
    }

    if (message.role === 'system') {
        return (
            <div className="flex justify-center animate-fade-in">
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm max-w-lg">
                    <i className="fas fa-exclamation-triangle mr-2"></i>
                    <MarkdownContent content={message.content} className="inline" />
                </div>
            </div>
        );
    }
    
    // Assistant message with complex content
    return (
        <div className="flex justify-start animate-fade-in">
            <div className="bg-slate-50 border border-slate-200 p-4 rounded-2xl rounded-bl-lg max-w-2xl space-y-3 shadow-sm">
                {message.content.map((item, index) => {
                    if (typeof item === 'string') {
                        return (
                            <div key={index} className="text-slate-800">
                                <MarkdownContent content={item} />
                            </div>
                        );
                    }

                    if (item.role === 'assistant') {
                        const content = item.content;
                        
                        // Handle different content types
                        if (content.includes('[Think]')) {
                            return (
                                <button
                                    key={index}
                                    onClick={() => onShowDetail({ type: 'think', content: content })}
                                    className="w-full bg-slate-50 hover:bg-slate-100 border border-gray-200 text-gray-700 p-3 rounded-xl text-sm transition-all duration-200 hover-lift text-left"
                                >
                                    <i className="fas fa-lightbulb mr-2"></i>
                                    <span className="font-medium">Think</span>
                                    <span className="block text-xs text-gray-600 mt-1">Click to view details</span>
                                </button>
                            );
                        }

                        if (content.includes('[Tool Called]')) {
                            return (
                                <button
                                    key={index}
                                    onClick={() => onShowDetail({ type: 'tool_call', content: content })}
                                    className="w-full bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 p-3 rounded-xl text-sm transition-all duration-200 hover-lift text-left"
                                >
                                    <i className="fas fa-tools mr-2"></i>
                                    <span className="font-medium">Tool Executed</span>
                                    <span className="block text-xs text-purple-600 mt-1">Click to view details</span>
                                </button>
                            );
                        }
                        
                        if (content.includes('[Memory Operation Called]')) {
                            return (
                                <button
                                    key={index}
                                    onClick={() => onShowDetail({ type: 'memory_op', content: content })}
                                    className="w-full bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-700 p-3 rounded-xl text-sm transition-all duration-200 hover-lift text-left"
                                >
                                    <i className="fas fa-memory mr-2"></i>
                                    <span className="font-medium">Memory Updated</span>
                                    <span className="block text-xs text-amber-600 mt-1">Click to view details</span>
                                </button>
                            );
                        }
                        
                        return (
                            <div key={index} className="text-slate-800">
                                <MarkdownContent content={content} />
                            </div>
                        );
                    }

                    return (
                        <div key={index} className="text-slate-600 text-sm font-mono bg-slate-100 p-2 rounded">
                            <MarkdownContent content={JSON.stringify(item, null, 2)} />
                        </div>
                    );
                })}
                
                <div className="text-xs text-slate-400 text-right">
                    {new Date(message.timestamp).toLocaleTimeString()}
                </div>
            </div>
        </div>
    );
}

// Task Panel Component
function TaskPanel({ task, selectedLogIndex, onSelectLog, onShowDetail }) {
    if (!task) {
        return (
            <div className="task-panel bg-white panel-border p-6">
                <h2 className="text-lg font-semibold text-slate-800 mb-4">Current Task</h2>
                <div className="text-center text-slate-400">
                    <i className="fas fa-clipboard-list text-3xl mb-3"></i>
                    <p className="text-sm">No active task</p>
                    <p className="text-xs mt-1">Select or create a task to get started</p>
                </div>
            </div>
        );
    }

    return (
        <div className="task-panel bg-white panel-border flex flex-col">
            {/* Header Section - Unchanged */}
            <div className="p-6 border-b-2 border-slate-100">
                <div className="flex items-center justify-between mb-2">
                    <div>
                        <h2 className="text-lg font-semibold text-slate-800">{truncate_string(task.title, 16)}</h2>
                        <div className="text-sm text-slate-500 space-x-2 flex items-center">
                            <span>Task {task.id}</span> 
                            <span className="bg-slate-100 text-black-700 text-xs font-medium px-2 py-1 rounded-full">
                                {task.type} 
                            </span> 
                        </div>
                    </div>
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={() => onShowDetail({ type: 'task_details', task: task })}
                            className="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover-lift"
                            title="View Full Details"
                        >
                            <i className="fas fa-info-circle mr-2"></i>Details
                        </button>
                        <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></div>
                    </div>
                </div>
            </div>
            
            {/* Compact Fields Section */}
            <div className="p-4 border-b-2 border-slate-100 space-y-2">
                <TaskField 
                    label="Target" 
                    value={task.target} 
                    icon="fas fa-bullseye" 
                    onClick={() => onShowDetail({ type: 'task_field', field: 'target', value: task.target })} 
                />
                <TaskField 
                    label="Plan" 
                    value={task.plan} 
                    icon="fas fa-map" 
                    onClick={() => onShowDetail({ type: 'task_field', field: 'plan', value: task.plan })} 
                />
                <TaskField 
                    label="Progress" 
                    value={task.progress} 
                    icon="fas fa-chart-line" 
                    onClick={() => onShowDetail({ type: 'task_field', field: 'progress', value: task.progress })} 
                />
            </div>
            
            {/* Activity Log Section - Now takes more space */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-4">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-slate-800">Activity Log</h3>
                        <span className="bg-slate-100 text-slate-600 text-xs font-medium px-2 py-1 rounded-full">
                            {task.logs?.length || 0}
                        </span>
                    </div>
                    
                    {task.logs?.length === 0 || !task.logs ? (
                        <div className="text-center text-slate-400 py-8">
                            <i className="fas fa-history text-2xl mb-2"></i>
                            <p className="text-sm">No logs yet</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {task.logs.map((log, index) => (
                                <LogBlock
                                    key={index}
                                    log={log}
                                    index={index}
                                    isSelected={selectedLogIndex === index}
                                    onSelect={() => onSelectLog(index)}
                                    onShowDetail={onShowDetail}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Task Field Component (unchanged)
function TaskField({ label, value, icon, onClick }) {
    const truncatedValue = value ? 
        (value.length > 60 ? value.substring(0, 60) + '...' : value) : 
        `No ${label.toLowerCase()} set`;
    
    return (
        <div
            className="cursor-pointer hover:bg-slate-50 p-2 rounded-lg transition-colors duration-200 border border-slate-100"
            onClick={onClick}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center min-w-0 flex-1">
                    <i className={`${icon} text-slate-400 mr-2 text-sm flex-shrink-0`}></i>
                    <label className="text-xs font-medium text-slate-600 mr-2 flex-shrink-0 w-16">{label}:</label>
                    <span className="text-xs text-slate-800 truncate">
                        {truncatedValue}
                    </span>
                </div>
                <i className="fas fa-external-link-alt text-xs text-slate-400 ml-2 flex-shrink-0"></i>
            </div>
        </div>
    );
}

// Enhanced Markdown Content Component with theme support
function MarkdownContent({ content, className = "" }) {
    const { useEffect, useRef, useState } = React;
    const contentRef = useRef(null);
    const [isLibrariesReady, setIsLibrariesReady] = useState(false);

    // Check if libraries are loaded
    useEffect(() => {
        const checkLibraries = () => {
            if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
                setIsLibrariesReady(true);
                return true;
            }
            return false;
        };

        // Check immediately
        if (checkLibraries()) {
            return;
        }

        // If not ready, poll every 100ms for up to 5 seconds
        const maxAttempts = 50;
        let attempts = 0;
        const interval = setInterval(() => {
            attempts++;
            if (checkLibraries() || attempts >= maxAttempts) {
                clearInterval(interval);
            }
        }, 100);

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (!contentRef.current || !isLibrariesReady || !content) return;

        try {
            // Configure marked options for better rendering
            if (typeof marked.setOptions === 'function') {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    headerIds: false,
                    sanitize: false,
                    smartLists: true,
                    smartypants: false
                });
            }

            // Parse markdown and sanitize HTML
            const htmlContent = marked.parse ? marked.parse(content) : marked(content);
            const cleanHTML = DOMPurify.sanitize(htmlContent, {
                ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                              'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'table', 'thead', 
                              'tbody', 'tr', 'td', 'th', 'hr', 'img'],
                ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'data-lang']
            });
            
            contentRef.current.innerHTML = cleanHTML;

            // Add syntax highlighting classes to code blocks
            const codeBlocks = contentRef.current.querySelectorAll('pre code');
            codeBlocks.forEach(block => {
                const text = block.textContent;
                let language = '';
                
                // Simple language detection
                if (text.includes('function') || text.includes('const') || text.includes('let') || text.includes('var')) {
                    language = 'javascript';
                } else if (text.includes('def ') || text.includes('import ') || text.includes('print(')) {
                    language = 'python';
                } else if (text.startsWith('{') && text.includes('"')) {
                    language = 'json';
                } else if (text.includes('$') || text.includes('cd ') || text.includes('ls ') || text.includes('#!/bin/')) {
                    language = 'bash';
                } else if (text.includes('<html>') || text.includes('<!DOCTYPE') || text.includes('<div>')) {
                    language = 'html';
                } else if (text.includes('SELECT') || text.includes('FROM') || text.includes('WHERE')) {
                    language = 'sql';
                }
                
                if (language) {
                    block.parentElement.setAttribute('data-lang', language);
                    block.parentElement.classList.add(`lang-${language}`);
                }
            });

            // Process tables for better styling
            const tables = contentRef.current.querySelectorAll('table');
            tables.forEach(table => {
                table.classList.add('markdown-table');
            });

        } catch (error) {
            console.error('Markdown rendering error:', error);
            // Fallback to plain text with basic line breaks and proper color
            const isLightTheme = className.includes('markdown-content-light');
            const textColor = isLightTheme ? 'color: #ffffff;' : 'color: #374151;';
            contentRef.current.innerHTML = `<div style="${textColor}">${content.replace(/\n/g, '<br>')}</div>`;
        }
    }, [content, isLibrariesReady, className]);

    // Show loading state or fallback
    if (!isLibrariesReady) {
        const isLightTheme = className.includes('markdown-content-light');
        const textColor = isLightTheme ? '#ffffff' : '#374151';
        return (
            <div className={`whitespace-pre-wrap ${className}`} style={{ color: textColor }}>
                {content}
            </div>
        );
    }

    return (
        <div 
            ref={contentRef}
            className={`markdown-content ${className}`}
        />
    );
}

// Log Block Component (unchanged)
function LogBlock({ log, index, isSelected, onSelect, onShowDetail }) {
    return (
        <div
            className={`border-2 rounded-xl p-4 cursor-pointer transition-all duration-200 hover-lift animate-fade-in ${
                isSelected ? 'border-indigo-200 bg-indigo-50' : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
            onClick={onSelect}
        >
            {/* Header with timestamp and log number */}
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-slate-500">
                    {new Date(log.timestamp).toLocaleString()}
                </span>
                <div className="flex items-center space-x-2">
                    <span className="text-xs text-slate-500">#{index + 1}</span>
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            onShowDetail({ type: 'log_detail', log: log, log_index: index });
                        }}
                        className="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-2 py-1 rounded text-xs font-medium transition-all duration-200"
                        title="View Full Log Details"
                    >
                        <i className="fas fa-expand-alt mr-1"></i>
                        Details
                    </button>
                </div>
            </div>
            
            {/* Error display - now in its own section */}
            {log.error && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-center mb-2">
                        <i className="fas fa-exclamation-triangle text-red-500 mr-2"></i>
                        <span className="text-xs font-semibold text-red-700">Error Occurred</span>
                    </div>
                    <p className="text-xs text-red-600 leading-relaxed">{log.error}</p>
                </div>
            )}
            
            {/* Query section */}
            {log.query && (
                <div className="mb-3">
                    <p className="text-xs font-medium text-slate-700 mb-1">Query</p>
                    <p className="text-xs text-slate-600 line-clamp-2">{log.query}</p>
                </div>
            )}
            
            {/* Response summary */}
            <div className="mb-3">
                <p className="text-xs text-slate-600 line-clamp-2">{log.response_summary}</p>
            </div>
            
            {/* Files section */}
            {Object.keys(log.files || {}).length > 0 && (
                <div className="mb-3">
                    <p className="text-xs font-medium text-slate-600 mb-2">
                        <i className="fas fa-file-code mr-1"></i>
                        Extracted Files ({Object.keys(log.files).length})
                    </p>
                    <div className="flex flex-wrap gap-1">
                        {Object.entries(log.files).map(([filename, file]) => {
                            const typeConfig = getFileTypeConfig(file.type);
                            return (
                                <button
                                    key={filename}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onShowDetail({ type: 'file', file: file, log_index: index });
                                    }}
                                    className={`text-xs px-2 py-1 rounded-lg transition-colors duration-200 bg-${typeConfig.color}-100 hover:bg-${typeConfig.color}-200 text-${typeConfig.color}-700`}
                                    title={`${file.type} - ${file.size} chars`}
                                >
                                    <i className={`mr-1 ${typeConfig.icon}`}></i>
                                    {filename}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
            
            {/* Footer with entries count */}
            <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2">
                <span>{log.entries?.length || 0} entries</span>
                {!log.error && (
                    <span className="flex items-center text-green-600">
                        <i className="fas fa-check-circle mr-1"></i>
                        Success
                    </span>
                )}
            </div>
        </div>
    );
}

// Details Panel Component (unchanged)
function DetailsPanel({ detail, onClose, isOpen, onShowDetail}) {
    return (
        <div className={`details-panel ${isOpen ? 'open' : ''}`}>
            {!detail ? (
                <div className="p-6">
                    
                    <h2 className="text-lg font-semibold text-slate-800 mb-4">Details</h2>
                    <div className="text-center text-slate-400">
                        <i className="fas fa-info-circle text-3xl mb-3"></i>
                        <p className="text-sm">No item selected</p>
                        <p className="text-xs mt-1">Click on logs, files, or operations to view details</p>
                    </div>
                </div>
            ) : (
                <>
                    <div className="p-6 border-b-2 border-slate-100 flex justify-between items-center bg-slate-50">
                        <h2 className="text-lg font-semibold text-slate-800">
                            {detail.type === 'memory' && 'Memory Details'}
                            {detail.type === 'config' && 'Client Configuration'}
                            {detail.type === 'task_details' && 'Task Details'}
                            {detail.type === 'task_field' && `Task ${detail.field}`}
                            {detail.type === 'file' && 'File Details'}
                            {detail.type === 'log_detail' && `Log #${detail.log_index + 1} Details`}
                            {detail.type === 'think' && 'Think'}
                            {detail.type === 'tool_call' && 'Tool Call'}
                            {detail.type === 'memory_op' && 'Memory Operation'}
                        </h2>
                        <button
                            onClick={onClose}
                            className="text-slate-400 hover:text-slate-600 p-2 rounded-lg hover:bg-slate-200 transition-colors duration-200"
                            title="Close details"
                        >
                            <i className="fas fa-times text-lg"></i>
                        </button>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-6" style={{height: 'calc(100vh - 8rem)'}}>
                        {detail.type === 'memory' && <MemoryDetail data={detail.data} />}
                        {detail.type === 'config' && <ConfigDetail data={detail.data} />}
                        {detail.type === 'task_details' && <TaskDetails task={detail.task} />}
                        {detail.type === 'task_field' && <TaskFieldDetail field={detail.field} value={detail.value} />}
                        {detail.type === 'file' && <FileDetail file={detail.file} />}
                        {detail.type === 'log_detail' && <LogDetail log={detail.log} logIndex={detail.log_index} onShowDetail={onShowDetail}/>}
                        {detail.type === 'think' && <ThinkDetail content={detail.content} />}
                        {detail.type === 'tool_call' && <ToolCallDetail content={detail.content} />}
                        {detail.type === 'memory_op' && <MemoryOpDetail content={detail.content} />}
                    </div>
                </>
            )}
        </div>
    );
}

// Log Detail Component
function LogDetail({ log, logIndex, onShowDetail}) {
    return (
        <div className="space-y-6 animate-fade-in">
            {/* Log Header */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold text-slate-800">Log #{logIndex + 1}</h3>
                    <span className="text-sm text-slate-500">
                        {new Date(log.timestamp).toLocaleString()}
                    </span>
                </div>
                {log.error && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <div className="flex items-center mb-2">
                            <i className="fas fa-exclamation-triangle text-red-500 mr-2"></i>
                            <span className="text-sm font-semibold text-red-700">Error Occurred</span>
                        </div>
                        <p className="text-sm text-red-600">{log.error}</p>
                    </div>
                )}
            </div>

            {/* Query Section */}
            {log.query && (
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center">
                        <i className="fas fa-question-circle mr-2"></i>
                        Query
                    </h4>
                    <div className="bg-slate-50 p-3 rounded-lg">
                        <p className="text-sm text-slate-800 whitespace-pre-wrap">{log.query}</p>
                    </div>
                </div>
            )}

            {/* Response Summary */}
            <div className="bg-white border border-slate-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center">
                    <i className="fas fa-reply mr-2"></i>
                    Response Summary
                </h4>
                <div className="bg-slate-50 p-3 rounded-lg">
                    <p className="text-sm text-slate-800 whitespace-pre-wrap">{log.response_summary || 'No response summary available'}</p>
                </div>
            </div>

            {/* Entries Section */}
            {log.entries && log.entries.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center">
                        <i className="fas fa-list mr-2"></i>
                        Log Entries ({log.entries.length})
                    </h4>
                    <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
                        {log.entries.map((entry, index) => (
                            <div key={index} className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs font-medium text-slate-600">Entry #{index + 1}</span>
                                    {entry.timestamp && (
                                        <span className="text-xs text-slate-500">
                                            {new Date(entry.timestamp).toLocaleTimeString()}
                                        </span>
                                    )}
                                </div>
                                <div className="text-sm text-slate-800 whitespace-pre-wrap">
                                    {typeof entry === 'string' ? entry : JSON.stringify(entry, null, 2)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {Object.entries(log.files).map(([filename, file]) => {
                const typeConfig = getFileTypeConfig(file.type);
                return (
                    <div key={filename} className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center">
                                <i className={`mr-2 ${typeConfig.icon} text-${typeConfig.color}-600`}></i>
                                <span className="font-medium text-slate-800">{filename}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <span className="text-xs text-slate-500">{file.type}</span>
                                <span className="text-xs text-slate-500">{file.size} chars</span>
                            </div>
                        </div>
                        <div className="text-xs text-slate-600 bg-white p-2 rounded border max-h-32 overflow-y-auto">
                            <pre className="whitespace-pre-wrap">{file.content.substring(0, 200)}{file.content.length > 200 ? '...' : ''}</pre>
                        </div>
                        <button
                            onClick={() => onShowDetail({ type: 'file', file: file, log_index: logIndex, parent: { type: 'log_detail', log: log, log_index: logIndex } })}
                            className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                        >
                            View Full File →
                        </button>
                    </div>
                );
            })}

            {/* Statistics */}
            <div className="bg-white border border-slate-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center">
                    <i className="fas fa-chart-bar mr-2"></i>
                    Statistics
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-slate-500">Entries:</span>
                        <span className="font-medium ml-2">{log.entries?.length || 0}</span>
                    </div>
                    <div>
                        <span className="text-slate-500">Files:</span>
                        <span className="font-medium ml-2">{Object.keys(log.files || {}).length}</span>
                    </div>
                    <div>
                        <span className="text-slate-500">Status:</span>
                        <span className={`font-medium ml-2 ${log.error ? 'text-red-600' : 'text-green-600'}`}>
                            {log.error ? 'Error' : 'Success'}
                        </span>
                    </div>
                    <div>
                        <span className="text-slate-500">Timestamp:</span>
                        <span className="font-medium ml-2">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Memory Detail Component (unchanged)
function MemoryDetail({ data }) {
    return (
        <div className="space-y-6 animate-fade-in">
            {/* Summary Section */}
            <div className="memory-section">
                <h4><i className="fas fa-chart-line"></i>Summary</h4>
                {Object.keys(data.summary || {}).length === 0 ? (
                    <p className="text-sm text-slate-500">No summaries available</p>
                ) : (
                    <div className="space-y-2">
                        {Object.entries(data.summary).map(([timestamp, summary]) => (
                            <div key={timestamp} className="bg-white border border-slate-200 rounded-lg p-3">
                                <div className="text-xs text-slate-500 mb-1">{timestamp}</div>
                                <div className="text-sm text-slate-700">{summary}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Topics Section */}
            <div className="memory-section">
                <h4><i className="fas fa-tags"></i>Topics ({Object.keys(data.topics || {}).length})</h4>
                {Object.keys(data.topics || {}).length === 0 ? (
                    <p className="text-sm text-slate-500">No topics discovered yet</p>
                ) : (
                    <div className="space-y-2">
                        {Object.entries(data.topics).map(([topic, info]) => (
                            <div key={topic} className="topic-item">
                                <div className="topic-name">{topic}</div>
                                <div className="text-sm text-slate-600 mb-2">{info.description}</div>
                                <div className="topic-meta">
                                    <span>Frequency: {info.frequency || 1}</span>
                                    <span>Last: {info.last_updated}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Database Section */}
            <div className="memory-section">
                <h4><i className="fas fa-database"></i>Database ({Object.keys(data.database || {}).length} items)</h4>
                {Object.keys(data.database || {}).length === 0 ? (
                    <p className="text-sm text-slate-500">No data stored yet</p>
                ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                        {Object.entries(data.database).map(([key, value]) => (
                            <div key={key} className="kv-item">
                                <div className="kv-key">{key}</div>
                                <div className="kv-value">{String(value).substring(0, 100)}{String(value).length > 100 ? '...' : ''}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Recent Records Section */}
            <div className="memory-section">
                <h4><i className="fas fa-history"></i>Recent Records ({data.recent_records?.length || 0})</h4>
                {(!data.recent_records || data.recent_records.length === 0) ? (
                    <p className="text-sm text-slate-500">No recent records</p>
                ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                        {data.recent_records.map((record, index) => (
                            <div key={index} className="bg-white border border-slate-200 rounded-lg p-3">
                                <div className="text-xs text-slate-500 mb-1">{record.timestamp}</div>
                                <div className="text-sm text-slate-700">{record.content}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

// Config Detail Component
function ConfigDetail({ data }) {
    return (
        <div className="space-y-6 animate-fade-in">
            {/* Provider Section */}
            <div className="memory-section">
                <h4><i className="fas fa-server"></i>Provider Configuration</h4>
                {Object.keys(data.provider || {}).length === 0 ? (
                    <p className="text-sm text-slate-500">No provider configuration</p>
                ) : (
                    <div className="bg-white border border-slate-200 rounded-lg p-3">
                        <pre className="text-xs text-slate-600 whitespace-pre-wrap">
                            {JSON.stringify(data.provider, null, 2)}
                        </pre>
                    </div>
                )}
            </div>

            {/* Memory Operations Section */}
            <div className="memory-section">
                <h4><i className="fas fa-memory"></i>Memory Operations ({data.memory_operations_num || 0})</h4>
                {(!data.memory_operations || data.memory_operations.length === 0) ? (
                    <p className="text-sm text-slate-500">No memory operations available</p>
                ) : (
                    <div className="space-y-2">
                        {data.memory_operations.map((op, index) => (
                            <div key={index} className="bg-white border border-slate-200 rounded-lg p-3">
                                <div className="font-medium text-slate-700 mb-1">{op.name}</div>
                                <div className="text-sm text-slate-600">{op.description}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Tools Section */}
            <div className="memory-section">
                <h4><i className="fas fa-tools"></i>Available Tools ({data.tools_num || 0})</h4>
                {(!data.tools || data.tools.length === 0) ? (
                    <p className="text-sm text-slate-500">No tools available</p>
                ) : (
                    <div className="space-y-2">
                        {data.tools.map((tool, index) => (
                            <div key={index} className="bg-white border border-slate-200 rounded-lg p-3">
                                <div className="font-medium text-slate-700 mb-1">{tool.name}</div>
                                <div className="text-sm text-slate-600">{tool.description}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

// Task Details Component (unchanged)
function TaskDetails({ task }) {
    return (
        <div className="space-y-4 animate-fade-in">
            <div className="task-detail-card">
                <div className="task-detail-label">
                    <i className="fas fa-bullseye"></i>
                    Target
                </div>
                <div className="task-detail-content">
                    {task.target || 'No target set'}
                </div>
            </div>

            <div className="task-detail-card">
                <div className="task-detail-label">
                    <i className="fas fa-map"></i>
                    Plan
                </div>
                <div className="task-detail-content">
                    {task.plan || 'No plan set'}
                </div>
            </div>

            <div className="task-detail-card">
                <div className="task-detail-label">
                    <i className="fas fa-chart-line"></i>
                    Progress
                </div>
                <div className="task-detail-content">
                    {task.progress || 'No progress recorded'}
                </div>
            </div>

            <div className="task-detail-card">
                <div className="task-detail-label">
                    <i className="fas fa-info-circle"></i>
                    Statistics
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-slate-500">Total Logs:</span>
                        <span className="font-medium ml-2">{task.logs_count || 0}</span>
                    </div>
                    <div>
                        <span className="text-slate-500">Total Files:</span>
                        <span className="font-medium ml-2">{task.files_count || 0}</span>
                    </div>
                    <div>
                        <span className="text-slate-500">Task ID:</span>
                        <span className="font-medium ml-2">{task.id}</span>
                    </div>
                    <div>
                        <span className="text-slate-500">Status:</span>
                        <span className={`font-medium ml-2 ${task.is_working ? 'text-green-600' : 'text-slate-500'}`}>
                            {task.is_working ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

function TaskFieldDetail({ field, value }) {
    return (
        <div className="space-y-4 animate-fade-in">
            <div className="task-detail-card">
                <div className="task-detail-label">
                    <i className={
                        field === 'target' ? 'fas fa-bullseye' :
                        field === 'plan' ? 'fas fa-map' :
                        field === 'progress' ? 'fas fa-chart-line' :
                        'fas fa-info-circle'
                    }></i>
                    {field.charAt(0).toUpperCase() + field.slice(1)}
                </div>
                <div className="task-detail-content">
                    {value ? (
                        <MarkdownContent content={value} />
                    ) : (
                        <span className="text-slate-500">No {field} set</span>
                    )}
                </div>
            </div>
        </div>
    );
}

// MODIFIED FileDetail Component to handle only specified file types
function FileDetail({ file, parent }) {
    // Function to handle file download
    const downloadFile = () => {
        try {
            const typeConfig = getFileTypeConfig(file.type);
            const extension = typeConfig.extension;
            
            // Create filename with proper extension
            const filename = file.filename || `${file.type}_${Date.now()}.${extension}`;
            
            // Create blob and download
            const blob = new Blob([file.content], { type: 'text/plain;charset=utf-8' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Download failed:', error);
            alert('Failed to download file');
        }
    };

    const typeConfig = getFileTypeConfig(file.type);

    return (
        <div className="space-y-6 animate-fade-in">
            {parent && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-center text-blue-700">
                        <i className="fas fa-info-circle mr-2"></i>
                        <span className="text-sm">
                            Viewing file from Log #{parent.log_index + 1}
                        </span>
                    </div>
                </div>
            )}
            
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-slate-800">{file.filename || `Untitled ${file.type}`}</h3>
                    <button
                        onClick={downloadFile}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover-lift flex items-center"
                        title="Download file"
                    >
                        <i className="fas fa-download mr-2"></i>
                        Download
                    </button>
                </div>
                
                <div className="flex flex-wrap gap-2 mb-4">
                    <span className={`bg-${typeConfig.color}-100 text-${typeConfig.color}-700 text-xs font-medium px-2 py-1 rounded-full`}>
                        {file.type}
                    </span>
                    <span className="bg-slate-100 text-slate-600 text-xs font-medium px-2 py-1 rounded-full">
                        {file.size} chars
                    </span>
                    <span className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-1 rounded-full">
                        .{typeConfig.extension}
                    </span>
                    {file.language && (
                        <span className="bg-green-100 text-green-700 text-xs font-medium px-2 py-1 rounded-full">
                            {file.language}
                        </span>
                    )}
                </div>
            </div>
            
            <div>
                <div>
                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Content</label>
                    {typeConfig.renderAs === 'markdown' ? (
                        // Render as markdown for supported types
                        <div className="bg-white border border-slate-200 p-4 rounded-xl text-sm overflow-x-auto">
                            <MarkdownContent content={file.content} />
                        </div>
                    ) : typeConfig.renderAs === 'code' ? (
                        // Render as code
                        <div className="bg-slate-900 text-slate-100 p-4 rounded-xl text-sm overflow-x-auto">
                            <pre className="whitespace-pre-wrap text-slate-100">{file.content}</pre>
                        </div>
                    ) : (
                        // Render as plain text
                        <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-sm overflow-x-auto">
                            <pre className="whitespace-pre-wrap text-slate-800">{file.content}</pre>
                        </div>
                    )}
                </div>
            </div>
            
            {file.metadata && Object.keys(file.metadata).length > 0 && (
                <div>
                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Metadata</label>
                    <div className="bg-slate-50 p-4 rounded-xl border">
                        <pre className="text-xs text-slate-600 whitespace-pre-wrap">
                            {JSON.stringify(file.metadata, null, 2)}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}

// Think Detail Component (unchanged)
function ThinkDetail({ content }) {
    try {
        const parsed = content.match(/name: (.*?), result: (.*)/);
        const name = parsed[1];
        const result = parsed[2];
        
        return (
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-2">Think</h3>
                    <div className="bg-purple-50 border border-purple-200 p-4 rounded-xl">
                        <div className="flex items-center mb-2">
                            <i className="fas fa-tools text-purple-600 mr-2"></i>
                            <span className="font-medium text-purple-800">{name}</span>
                        </div>
                    </div>
                </div>
                
                <div>
                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Result</label>
                    <div className="code-block p-4 rounded-xl text-sm overflow-x-auto">
                        <pre className="whitespace-pre-wrap">{result}</pre>
                    </div>
                </div>
            </div>
        );
    } catch {
        return (
            <div className="animate-fade-in">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Think</h3>
                <div className="code-block p-4 rounded-xl text-sm overflow-x-auto">
                    <pre className="whitespace-pre-wrap">{content}</pre>
                </div>
            </div>
        );
    }
}


// Tool Call Detail Component (unchanged)
function ToolCallDetail({ content }) {
    try {
        const parsed = content.match(/name: (.*?), result: (.*)/);
        const name = parsed[1];
        const result = parsed[2];
        
        return (
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-2">Tool Execution</h3>
                    <div className="bg-purple-50 border border-purple-200 p-4 rounded-xl">
                        <div className="flex items-center mb-2">
                            <i className="fas fa-tools text-purple-600 mr-2"></i>
                            <span className="font-medium text-purple-800">{name}</span>
                        </div>
                    </div>
                </div>
                
                <div>
                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Result</label>
                    <div className="code-block p-4 rounded-xl text-sm overflow-x-auto">
                        <pre className="whitespace-pre-wrap">{result}</pre>
                    </div>
                </div>
            </div>
        );
    } catch {
        return (
            <div className="animate-fade-in">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Tool Execution</h3>
                <div className="code-block p-4 rounded-xl text-sm overflow-x-auto">
                    <pre className="whitespace-pre-wrap">{content}</pre>
                </div>
            </div>
        );
    }
}

// Memory Operation Detail Component (unchanged)
function MemoryOpDetail({ content }) {
    try {
        const parsed = content.match(/name: (.*?), result: (.*)/);
        const name = parsed[1];
        const result = parsed[2];
        
        return (
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-2">Memory Operation</h3>
                    <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl">
                        <div className="flex items-center mb-2">
                            <i className="fas fa-memory text-amber-600 mr-2"></i>
                            <span className="font-medium text-amber-800">{name}</span>
                        </div>
                    </div>
                </div>
                
                <div>
                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Result</label>
                    <div className="code-block p-4 rounded-xl text-sm overflow-x-auto">
                        <pre className="whitespace-pre-wrap">{result}</pre>
                    </div>
                </div>
            </div>
        );
    } catch {
        return (
            <div className="animate-fade-in">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Memory Operation</h3>
                <div className="code-block p-4 rounded-xl text-sm overflow-x-auto">
                    <pre className="whitespace-pre-wrap">{content}</pre>
                </div>
            </div>
        );
    }
}

function TaskTypeModal({ isOpen, onClose, onCreateTask, availableTypes }) {
    if (!isOpen) return null;

    const handleCreateTask = (taskType) => {
        onCreateTask(taskType);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div 
                className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
                onClick={onClose}
            ></div>
            
            {/* Modal */}
            <div className="relative bg-white rounded-2xl shadow-xl border-2 border-slate-200 max-w-md w-full mx-4 animate-fade-in">
                <div className="bg-slate-50 border-b-2 border-slate-100 rounded-t-2xl p-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <i className="fas fa-plus text-indigo-600 text-xl mr-3"></i>
                            <h3 className="text-lg font-semibold text-slate-800">
                                Create New Task
                            </h3>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-slate-400 hover:text-slate-600 p-2 rounded-lg hover:bg-slate-200 transition-colors duration-200"
                        >
                            <i className="fas fa-times text-lg"></i>
                        </button>
                    </div>
                    <p className="text-sm text-slate-500 mt-2">
                        Choose the type of task you want to create
                    </p>
                </div>
                
                <div className="p-6">
                    <div className="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
                        {availableTypes.map((taskType) => (
                            <button
                                key={taskType.type}
                                onClick={() => handleCreateTask(taskType.type)}
                                className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 hover-lift bg-${taskType.color}-50 hover:bg-${taskType.color}-100 border-${taskType.color}-200 hover:border-${taskType.color}-300`}
                            >
                                <div className="flex items-center mb-2">
                                    <i className={`${taskType.icon} text-${taskType.color}-600 text-lg mr-3`}></i>
                                    <span className={`font-semibold text-${taskType.color}-800`}>
                                        {taskType.label}
                                    </span>
                                </div>
                                <p className={`text-sm text-${taskType.color}-700 opacity-90`}>
                                    {taskType.description}
                                </p>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatusBar({ message, type }) {
    if (!message) return null;

    const typeStyles = {
        idle: 'bg-slate-100 text-slate-600',
        processing: 'bg-blue-100 text-blue-700',
        polling: 'bg-amber-100 text-amber-700',
        success: 'bg-green-100 text-green-700',
        error: 'bg-red-100 text-red-700'
    };

    const iconStyles = {
        idle: 'fas fa-info-circle',
        processing: 'fas fa-spinner fa-spin',
        polling: 'fas fa-sync fa-spin',
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-triangle'
    };

    return (
        <div className={`fixed bottom-0 left-0 right-0 ${typeStyles[type]} border-t-2 border-opacity-30 px-6 py-3 text-sm font-medium animate-fade-in z-40`}>
            <div className="flex items-center justify-center">
                <i className={`${iconStyles[type]} mr-2`}></i>
                <span>{message}</span>
            </div>
        </div>
    );
}

// Alert Modal Component
function AlertModal({ isOpen, onClose, title, message, type = 'info' }) {
    if (!isOpen) return null;

    const typeStyles = {
        error: {
            bg: 'bg-red-50',
            border: 'border-red-200',
            icon: 'fas fa-exclamation-triangle text-red-500',
            titleColor: 'text-red-800',
            messageColor: 'text-red-700',
            buttonBg: 'bg-red-600 hover:bg-red-700'
        },
        success: {
            bg: 'bg-green-50',
            border: 'border-green-200', 
            icon: 'fas fa-check-circle text-green-500',
            titleColor: 'text-green-800',
            messageColor: 'text-green-700',
            buttonBg: 'bg-green-600 hover:bg-green-700'
        },
        warning: {
            bg: 'bg-amber-50',
            border: 'border-amber-200',
            icon: 'fas fa-exclamation-circle text-amber-500',
            titleColor: 'text-amber-800',
            messageColor: 'text-amber-700',
            buttonBg: 'bg-amber-600 hover:bg-amber-700'
        },
        info: {
            bg: 'bg-blue-50',
            border: 'border-blue-200',
            icon: 'fas fa-info-circle text-blue-500',
            titleColor: 'text-blue-800',
            messageColor: 'text-blue-700',
            buttonBg: 'bg-blue-600 hover:bg-blue-700'
        }
    };

    const styles = typeStyles[type] || typeStyles.info;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div 
                className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
                onClick={onClose}
            ></div>
            
            {/* Modal */}
            <div className="relative bg-white rounded-2xl shadow-xl border-2 border-slate-200 max-w-md w-full mx-4 animate-fade-in">
                <div className={`${styles.bg} ${styles.border} rounded-t-2xl p-6 border-b-2`}>
                    <div className="flex items-center">
                        <i className={`${styles.icon} text-2xl mr-3`}></i>
                        <h3 className={`text-lg font-semibold ${styles.titleColor}`}>
                            {title}
                        </h3>
                    </div>
                </div>
                
                <div className="p-6">
                    <p className={`${styles.messageColor} leading-relaxed mb-6`}>
                        {message}
                    </p>
                    
                    <div className="flex justify-end">
                        <button
                            onClick={onClose}
                            className={`${styles.buttonBg} text-white px-6 py-2 rounded-xl font-medium transition-all duration-200 hover-lift focus:outline-none focus:ring-2 focus:ring-offset-2`}
                        >
                            OK
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Toast Notification Component
function Toast({ isVisible, onClose, title, message, type = 'info', duration = 4000 }) {
    useEffect(() => {
        if (isVisible && duration > 0) {
            const timer = setTimeout(onClose, duration);
            return () => clearTimeout(timer);
        }
    }, [isVisible, duration, onClose]);

    if (!isVisible) return null;

    const typeStyles = {
        error: 'bg-red-50 border-red-200 text-red-800',
        success: 'bg-green-50 border-green-200 text-green-800',
        warning: 'bg-amber-50 border-amber-200 text-amber-800',
        info: 'bg-blue-50 border-blue-200 text-blue-800'
    };

    const iconStyles = {
        error: 'fas fa-exclamation-triangle text-red-500',
        success: 'fas fa-check-circle text-green-500',
        warning: 'fas fa-exclamation-circle text-amber-500',
        info: 'fas fa-info-circle text-blue-500'
    };

    return (
        <div className="fixed top-20 right-6 z-50 animate-fade-in">
            <div className={`${typeStyles[type]} border-2 rounded-xl p-4 shadow-lg max-w-sm backdrop-blur-sm`}>
                <div className="flex items-start">
                    <i className={`${iconStyles[type]} text-lg mr-3 mt-0.5 flex-shrink-0`}></i>
                    <div className="flex-1 min-w-0">
                        {title && (
                            <p className="font-semibold text-sm mb-1">{title}</p>
                        )}
                        <p className="text-sm opacity-90">{message}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="ml-3 text-current opacity-50 hover:opacity-75 transition-opacity"
                    >
                        <i className="fas fa-times text-sm"></i>
                    </button>
                </div>
            </div>
        </div>
    );
}

// Render the app
const { createRoot } = ReactDOM;
const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);