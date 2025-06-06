# Frontend Enhancements for Smart Inventory System

## 1. Real-time Updates with WebSockets

```javascript
// WebSocket connection for real-time updates
class InventoryWebSocket {
  constructor(apiBaseUrl) {
    this.wsUrl = apiBaseUrl.replace('http', 'ws') + '/ws';
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.callbacks = {
      'inventory_updated': [],
      'user_joined': [],
      'error': []
    };
  }

  connect() {
    try {
      this.ws = new WebSocket(this.wsUrl);
      
      this.ws.onopen = () => {
        console.log('✅ WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };

      this.ws.onclose = () => {
        console.log('⚠️ WebSocket disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        this.triggerCallbacks('error', error);
      };

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  handleMessage(data) {
    const { type, payload } = data;
    this.triggerCallbacks(type, payload);
  }

  on(event, callback) {
    if (this.callbacks[event]) {
      this.callbacks[event].push(callback);
    }
  }

  triggerCallbacks(event, data) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(callback => callback(data));
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`🔄 Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, 2000 * this.reconnectAttempts);
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage in Vue component
export default {
  name: 'ChatInterface',
  data() {
    return {
      ws: null,
      isConnected: false,
      // ... other data
    };
  },
  
  mounted() {
    this.setupWebSocket();
  },
  
  beforeUnmount() {
    if (this.ws) {
      this.ws.disconnect();
    }
  },
  
  methods: {
    setupWebSocket() {
      this.ws = new InventoryWebSocket(this.apiBaseUrl);
      
      this.ws.on('inventory_updated', (data) => {
        this.$emit('inventory-updated', data);
        this.addSystemMessage('🔄 Inventory updated in real-time');
      });
      
      this.ws.on('error', (error) => {
        this.addSystemMessage('⚠️ Connection error: ' + error.message);
      });
      
      this.ws.connect();
    },
    
    addSystemMessage(text) {
      this.chatHistory.push({
        type: 'system',
        text: text,
        timestamp: new Date()
      });
    }
  }
};
```

## 2. Advanced Search Interface

```vue
<template>
  <div class="search-container">
    <!-- Quick Search -->
    <div class="quick-search">
      <input 
        v-model="searchQuery" 
        @input="onSearchInput"
        placeholder="Search items, sellers..."
        class="search-input"
      >
      <button @click="toggleAdvancedSearch" class="advanced-btn">
        {{ showAdvanced ? 'Simple' : 'Advanced' }}
      </button>
    </div>

    <!-- Advanced Search Panel -->
    <div v-if="showAdvanced" class="advanced-search-panel">
      <div class="search-row">
        <div class="search-field">
          <label>Seller:</label>
          <input v-model="filters.seller" placeholder="Seller name">
        </div>
        <div class="search-field">
          <label>Price Range:</label>
          <input v-model.number="filters.minPrice" type="number" placeholder="Min" class="price-input">
          <span class="to-separator">to</span>
          <input v-model.number="filters.maxPrice" type="number" placeholder="Max" class="price-input">
        </div>
      </div>
      
      <div class="search-row">
        <div class="search-field">
          <label>Sort By:</label>
          <select v-model="filters.sortBy">
            <option value="name">Name</option>
            <option value="price">Price</option>
            <option value="seller">Seller</option>
            <option value="created_at">Date Added</option>
          </select>
        </div>
        <div class="search-field">
          <label>Order:</label>
          <select v-model="filters.sortOrder">
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
      </div>

      <div class="search-actions">
        <button @click="applyFilters" class="apply-btn">Apply Filters</button>
        <button @click="clearFilters" class="clear-btn">Clear</button>
      </div>
    </div>

    <!-- Search Results -->
    <div class="search-results">
      <div class="results-header">
        <span class="results-count">{{ searchResults.length }} items found</span>
        <div class="view-options">
          <button @click="viewMode = 'grid'" :class="{ active: viewMode === 'grid' }">Grid</button>
          <button @click="viewMode = 'list'" :class="{ active: viewMode === 'list' }">List</button>
        </div>
      </div>

      <div :class="`results-${viewMode}`">
        <div v-for="item in searchResults" :key="item._id" class="item-card">
          <div class="item-name">{{ item.name }}</div>
          <div class="item-price">${{ item.price.toFixed(2) }}</div>
          <div class="item-seller">{{ item.seller }}</div>
          <div class="item-actions">
            <button @click="editItem(item)" class="edit-btn">Edit</button>
            <button @click="deleteItem(item)" class="delete-btn">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { debounce } from 'lodash';

export default {
  name: 'AdvancedSearch',
  data() {
    return {
      searchQuery: '',
      showAdvanced: false,
      viewMode: 'grid',
      searchResults: [],
      filters: {
        seller: '',
        minPrice: null,
        maxPrice: null,
        sortBy: 'name',
        sortOrder: 'asc'
      }
    };
  },
  
  created() {
    this.debouncedSearch = debounce(this.performSearch, 300);
  },
  
  methods: {
    onSearchInput() {
      this.debouncedSearch();
    },
    
    async performSearch() {
      try {
        const params = new URLSearchParams();
        
        if (this.searchQuery) params.append('q', this.searchQuery);
        if (this.filters.seller) params.append('seller', this.filters.seller);
        if (this.filters.minPrice) params.append('min_price', this.filters.minPrice);
        if (this.filters.maxPrice) params.append('max_price', this.filters.maxPrice);
        params.append('sort_by', this.filters.sortBy);
        params.append('sort_order', this.filters.sortOrder);
        
        const response = await fetch(`${this.apiBaseUrl}/items/search?${params}`);
        const data = await response.json();
        
        this.searchResults = data.items;
        
      } catch (error) {
        console.error('Search error:', error);
      }
    },
    
    toggleAdvancedSearch() {
      this.showAdvanced = !this.showAdvanced;
    },
    
    applyFilters() {
      this.performSearch();
    },
    
    clearFilters() {
      this.searchQuery = '';
      this.filters = {
        seller: '',
        minPrice: null,
        maxPrice: null,
        sortBy: 'name',
        sortOrder: 'asc'
      };
      this.performSearch();
    }
  }
};
</script>
```

## 3. Data Visualization Dashboard

```vue
<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h2>Inventory Analytics</h2>
      <button @click="refreshData" class="refresh-btn">Refresh</button>
    </div>

    <!-- Summary Cards -->
    <div class="summary-cards">
      <div class="summary-card">
        <div class="card-title">Total Items</div>
        <div class="card-value">{{ analytics.total_items || 0 }}</div>
        <div class="card-change">+{{ newItemsToday }} today</div>
      </div>
      
      <div class="summary-card">
        <div class="card-title">Total Value</div>
        <div class="card-value">${{ (analytics.total_value || 0).toFixed(2) }}</div>
        <div class="card-change">{{ valueChangePercent }}% this week</div>
      </div>
      
      <div class="summary-card">
        <div class="card-title">Avg Price</div>
        <div class="card-value">${{ (analytics.avg_price || 0).toFixed(2) }}</div>
      </div>
      
      <div class="summary-card">
        <div class="card-title">Sellers</div>
        <div class="card-value">{{ analytics.unique_sellers_count || 0 }}</div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-section">
      <div class="chart-container">
        <h3>Price Distribution</h3>
        <canvas ref="priceChart"></canvas>
      </div>
      
      <div class="chart-container">
        <h3>Items by Seller</h3>
        <canvas ref="sellerChart"></canvas>
      </div>
    </div>

    <!-- Alerts -->
    <div class="alerts-section">
      <h3>Inventory Alerts</h3>
      <div v-if="alerts.length === 0" class="no-alerts">
        ✅ No alerts at this time
      </div>
      <div v-else class="alerts-list">
        <div v-for="alert in alerts" :key="alert.id" :class="`alert alert-${alert.severity}`">
          <div class="alert-icon">
            <span v-if="alert.severity === 'warning'">⚠️</span>
            <span v-else-if="alert.severity === 'error'">❌</span>
            <span v-else>ℹ️</span>
          </div>
          <div class="alert-content">
            <div class="alert-message">{{ alert.message }}</div>
            <div class="alert-time">{{ formatTime(alert.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Chart from 'chart.js/auto';

export default {
  name: 'AnalyticsDashboard',
  data() {
    return {
      analytics: {},
      sellerAnalytics: [],
      alerts: [],
      charts: {},
      newItemsToday: 0,
      valueChangePercent: 0
    };
  },
  
  async mounted() {
    await this.loadDashboardData();
    this.createCharts();
  },
  
  methods: {
    async loadDashboardData() {
      try {
        // Load analytics summary
        const analyticsResponse = await fetch(`${this.apiBaseUrl}/analytics/summary`);
        this.analytics = await analyticsResponse.json();
        
        // Load seller analytics
        const sellerResponse = await fetch(`${this.apiBaseUrl}/analytics/by-seller`);
        const sellerData = await sellerResponse.json();
        this.sellerAnalytics = sellerData.sellers;
        
        // Load alerts
        const alertsResponse = await fetch(`${this.apiBaseUrl}/alerts`);
        const alertsData = await alertsResponse.json();
        this.alerts = alertsData.alerts;
        
        // Calculate additional metrics
        this.calculateMetrics();
        
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      }
    },
    
    createCharts() {
      this.createPriceDistributionChart();
      this.createSellerChart();
    },
    
    createPriceDistributionChart() {
      const ctx = this.$refs.priceChart.getContext('2d');
      
      // Create price ranges
      const priceRanges = ['$0-25', '$25-100', '$100-500', '$500-1000', '$1000+'];
      const counts = [0, 0, 0, 0, 0];
      
      // You would get this data from your API
      // For now, using mock data
      
      this.charts.priceChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: priceRanges,
          datasets: [{
            label: 'Number of Items',
            data: counts,
            backgroundColor: '#333333',
            borderColor: '#555555',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              labels: { color: '#ffffff' }
            }
          },
          scales: {
            x: { ticks: { color: '#ffffff' } },
            y: { ticks: { color: '#ffffff' } }
          }
        }
      });
    },
    
    createSellerChart() {
      const ctx = this.$refs.sellerChart.getContext('2d');
      
      const topSellers = this.sellerAnalytics.slice(0, 5);
      const labels = topSellers.map(s => s.seller);
      const values = topSellers.map(s => s.total_value);
      
      this.charts.sellerChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: [
              '#FF6384',
              '#36A2EB', 
              '#FFCE56',
              '#4BC0C0',
              '#9966FF'
            ]
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              labels: { color: '#ffffff' }
            }
          }
        }
      });
    },
    
    calculateMetrics() {
      // Calculate new items today (mock calculation)
      this.newItemsToday = Math.floor(Math.random() * 10);
      
      // Calculate value change percentage (mock calculation)
      this.valueChangePercent = (Math.random() * 20 - 10).toFixed(1);
    },
    
    async refreshData() {
      await this.loadDashboardData();
      
      // Update charts
      Object.values(this.charts).forEach(chart => {
        if (chart) chart.destroy();
      });
      this.createCharts();
    },
    
    formatTime(timestamp) {
      return new Date(timestamp).toLocaleString();
    }
  }
};
</script>
```

## 4. Progressive Web App (PWA) Features

```javascript
// sw.js - Service Worker for offline functionality
const CACHE_NAME = 'inventory-v1';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version or fetch from network
        return response || fetch(event.request);
      })
  );
});

// manifest.json
{
  "name": "Smart Inventory System",
  "short_name": "Inventory",
  "description": "AI-powered inventory management",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#000000",
  "background_color": "#000000",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png", 
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}

// Register service worker in main.js
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then((registration) => {
      console.log('SW registered: ', registration);
    })
    .catch((registrationError) => {
      console.log('SW registration failed: ', registrationError);
    });
}
```
