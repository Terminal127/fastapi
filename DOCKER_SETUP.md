# 🚀 Smart Inventory System Pro - Complete Docker Setup

An AI-powered inventory management system with Vue.js frontend, FastAPI backend, and advanced features including analytics, QR codes, bulk operations, and real-time insights.

## ✨ Features

### 🤖 AI Chat Interface
- Natural language inventory management
- Smart bulk operations
- Complex query processing
- Contextual conversation history

### 📊 Analytics & Insights
- Real-time charts and visualizations
- Price distribution analysis
- Seller performance metrics
- Inventory optimization suggestions
- Duplicate detection and insights

### 🔧 Advanced Operations
- **QR Code Generation** - Generate QR codes for items
- **Bulk Operations** - Add, update, delete multiple items
- **CSV Import/Export** - Bulk data management
- **Advanced Search** - Filter by price, seller, name
- **Health Monitoring** - Comprehensive system status

### 🎨 Modern UI
- Minimalist black theme
- Responsive design
- Real-time updates
- Interactive charts and analytics

## 🐳 Docker Setup & Usage

### Prerequisites
- Docker Desktop installed
- Git (optional)

### 🚀 Quick Start

1. **Clone or Download the Project**
   ```bash
   git clone <repository-url>
   cd smart-inventory-system
   ```

2. **Build and Start All Services**
   ```bash
   docker-compose up --build
   ```

3. **Access the Application**
   - **Frontend (Vue.js)**: http://localhost:3000
   - **Backend API**: http://localhost:8002
   - **API Documentation**: http://localhost:8002/docs

### 🛠️ Development Mode

For development with hot-reload:
```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 🔧 Individual Service Management

```bash
# Build only backend
docker-compose build backend

# Start only frontend
docker-compose up frontend

# Restart a service
docker-compose restart backend
```

## 📚 API Endpoints

### Core Inventory Management
- `POST /smart-add` - AI-powered natural language interface
- `GET /items` - List all inventory items
- `POST /add-item` - Manual item addition
- `GET /health` - Comprehensive health check

### Advanced Features
- `GET /qr-code/{item_id}` - Generate QR code for item
- `POST /bulk-operations` - Bulk add/update/delete operations
- `GET /export/csv` - Export inventory to CSV
- `POST /import/csv` - Import inventory from CSV
- `GET /search/items` - Advanced search with filters

### Analytics & Insights
- `GET /analytics/charts` - Generate data visualization charts
- `GET /analytics/items` - Get inventory statistics
- `GET /insights` - AI-powered inventory insights
- `GET /trends` - Trending items and patterns
- `GET /optimize-inventory` - Optimization recommendations

### Webhooks & Alerts
- `POST /webhook-config` - Configure real-time webhooks
- `POST /alert` - Create inventory alerts
- `POST /trigger-event` - Test webhook events

## 💬 Using the AI Chat Interface

The system understands natural language commands:

### ➕ Adding Items
```
"add laptop for $999 from TechStore"
"add 3 apples for $5 from John and 2 bananas for $3 from Sarah"
```

### 🗑️ Deleting Items
```
"delete bottle from Mike"
"delete all items from old_seller"
"delete all persons selling only bottle"
"delete all apples"
```

### 🔄 Updating Items
```
"update bottle price to $5 from Mike"
"update all items from John to $10"
"change all apple prices to $8"
"increase all prices by 20%"
"decrease all prices by 10%"
```

### 🔍 Complex Operations
```
"add phone for $500 from Alex and delete all items from old sellers"
"update all apple prices to $6 and add 5 oranges for $3 from Bob"
```

## 🎯 Cool Features to Try

### 1. 📊 Analytics Dashboard
Visit the API documentation at http://localhost:8002/docs and try:
- `/analytics/charts` - View price distribution and seller analytics
- `/insights` - Get AI-powered inventory insights
- `/trends` - See trending items and patterns

### 2. 📱 QR Code Generation
Generate QR codes for any item:
```bash
GET /qr-code/{item_id}
```

### 3. 📁 CSV Operations
- Export entire inventory: `GET /export/csv`
- Import bulk data: `POST /import/csv`

### 4. 🔍 Advanced Search
Filter inventory with multiple criteria:
```bash
GET /search/items?name=apple&min_price=1&max_price=10&seller=john&sort_by=price&sort_order=desc
```

### 5. 🏥 Health Monitoring
Check system status: `GET /health`

## 🛠️ Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Change ports in docker-compose.yml
   ports:
     - "3001:80"  # Change from 3000 to 3001
     - "8003:8002" # Change from 8002 to 8003
   ```

2. **Backend Connection Issues**
   - Check if backend is running: http://localhost:8002/health
   - Verify MongoDB connection in logs: `docker-compose logs backend`

3. **Frontend Build Issues**
   ```bash
   # Rebuild frontend only
   docker-compose build --no-cache frontend
   ```

4. **Database Issues**
   - The system uses MongoDB Atlas (cloud database)
   - Check network connectivity if experiencing database errors

### 🔧 Development Tips

1. **Live Code Changes**
   - Backend: Code changes trigger automatic reload
   - Frontend: Vue hot-reload is enabled in development

2. **Viewing Logs**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f backend
   ```

3. **Database Management**
   - Use MongoDB Compass or Atlas web interface
   - Connection string is in docker-compose.yml

## 🎨 Customization

### Frontend Theming
The frontend uses a minimalist black theme. To customize:
- Edit `frontend/src/App.vue` for global styles
- Modify component styles in `frontend/src/components/`

### Backend Configuration
- Environment variables in `docker-compose.yml`
- API settings in `test/main.py`

## 🚀 Production Deployment

For production:

1. **Update Environment Variables**
   - Use secure MongoDB connection
   - Set proper CORS origins
   - Use environment-specific API keys

2. **Use Production Docker Setup**
   ```bash
   # Create production docker-compose
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Enable HTTPS**
   - Use reverse proxy (nginx/traefik)
   - Add SSL certificates

## 📝 API Documentation

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test with Docker
5. Submit pull request

## 📄 License

This project is licensed under the MIT License.

---

## 🎯 Quick Demo Commands

Once running, try these in the chat interface:

```
add laptop for $999 from TechStore
add 3 apples for $2 from Bob
delete all items from Bob
update laptop price to $899
increase all prices by 10%
```

Visit http://localhost:8002/docs to explore all API endpoints!
