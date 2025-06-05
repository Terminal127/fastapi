# 🚀 AI-Powered Inventory Management System

A FastAPI-based inventory management system with AI-powered natural language processing for CRUD operations, built with LangChain and Google Gemini Pro.

## ✨ Features

- **Natural Language Processing**: Use plain English to manage inventory
- **Complex Operations**: Bulk operations, percentage-based updates, advanced queries
- **MongoDB Integration**: Persistent data storage with MongoDB Atlas
- **Smart Duplicate Handling**: Intelligent handling of items from different sellers
- **In-Memory Chat History**: Contextual conversations (up to 5 exchanges)
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Comprehensive Error Handling**: Graceful error handling and user feedback

## 🛠️ Quick Start

### Method 1: Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env and add your Google API key
   # GOOGLE_API_KEY=your-actual-api-key-here
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

4. **Test the API**
   ```bash
   python test_api.py
   ```

### Method 2: Docker Deployment

1. **Set Environment Variables**
   ```bash
   # Edit docker-compose.yml and add your Google API key
   ```

2. **Build and Run**
   ```bash
   docker-compose up --build
   ```

3. **Access the API**
   - API: http://localhost:8002
   - Health Check: http://localhost:8002/health
   - Items List: http://localhost:8002/items

## 🎯 Usage Examples

### Basic Operations

```bash
# Add an item
POST /chat
{"message": "add laptop 999.99 TechStore"}

# Delete an item
POST /chat
{"message": "delete laptop from TechStore"}

# Update an item
POST /chat
{"message": "update laptop price to 899.99"}

# Search items
POST /chat
{"message": "search for laptop"}
```

### Complex Operations

```bash
# Bulk add multiple items
POST /chat
{"message": "add laptop 999 TechStore, mouse 29.99 TechStore, keyboard 79.99 OfficeSupply"}

# Increase all prices by percentage
POST /chat
{"message": "increase all prices by 10%"}

# Delete all items by specific seller
POST /chat
{"message": "delete all items by seller TechStore"}

# Advanced deletion query
POST /chat
{"message": "delete all persons selling only bottle"}

# Combined operations
POST /chat
{"message": "add phone 599 MobileShop and delete old laptop"}
```

### Search and Query

```bash
# Search by name
POST /chat
{"message": "search for laptop"}

# Search by seller
POST /chat
{"message": "show items by TechStore"}

# List all items
POST /chat
{"message": "list all items"}
```

## 🏗️ Architecture

### Core Components

- **FastAPI**: Web framework for the REST API
- **LangChain**: AI orchestration and tool management
- **Google Gemini Pro**: Large Language Model for natural language understanding
- **MongoDB Atlas**: Cloud database for persistent storage
- **Motor**: Async MongoDB driver

### Key Features

1. **AI-Powered Query Processing**
   - Natural language understanding with Google Gemini Pro
   - Context-aware conversations with chat history
   - Complex query parsing and execution

2. **Intelligent Database Operations**
   - Smart duplicate handling for items from different sellers
   - Bulk operations with transaction-like behavior
   - Advanced filtering and search capabilities

3. **Robust Error Handling**
   - Comprehensive input validation
   - Graceful error messages
   - Database connection resilience

## 📚 API Endpoints

### Main Endpoints

- `GET /` - Welcome message and API information
- `POST /chat` - Main AI chat interface
- `GET /items` - List all items in inventory
- `GET /health` - Health check and database connection status

### Chat Request Format

```json
{
  "message": "your natural language request",
  "session_id": "optional-session-identifier"
}
```

### Chat Response Format

```json
{
  "success": true,
  "message": "AI response with operation results",
  "chat_history": "Recent conversation context"
}
```

## 🔧 Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Your Google API key for Gemini Pro (required)
- `MONGODB_URI`: MongoDB connection string (optional, defaults to included Atlas cluster)

### Docker Configuration

The application includes Docker configuration for easy deployment:

- `Dockerfile`: Multi-stage build for optimized production images
- `docker-compose.yml`: Complete orchestration with health checks
- `.dockerignore`: Optimized build context

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Make sure the API is running (python main.py or docker-compose up)
python test_api.py
```

The test suite covers:
- Health checks
- Basic CRUD operations
- Complex bulk operations
- Advanced query processing
- Error handling scenarios

## 🚀 Production Deployment

### Docker Production Mode

```bash
# Build for production
docker build --target production -t inventory-api .

# Run with production settings
docker run -p 8002:8002 -e GOOGLE_API_KEY=your-key inventory-api
```

### Performance Considerations

- MongoDB connection pooling with Motor
- Async operations throughout the application
- Optimized Docker images with multi-stage builds
- Health checks and auto-restart capabilities

## 🛡️ Security

- Input validation and sanitization
- Environment-based configuration
- No hardcoded credentials
- CORS middleware for web integration

## 📈 Monitoring

- Health check endpoint for uptime monitoring
- Comprehensive error logging
- Database connection status tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

---

**Built with ❤️ using FastAPI, LangChain, and Google Gemini Pro**
