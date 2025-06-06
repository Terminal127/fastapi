<template>
  <div class="analytics-container">
    <div class="analytics-header">
      <h2>📊 Analytics Dashboard</h2>
      <div class="header-actions">
        <button @click="refreshData" class="refresh-btn" :disabled="loading">
          {{ loading ? 'Loading...' : '🔄 Refresh' }}
        </button>
        <button @click="toggleView" class="toggle-btn">
          {{ viewMode === 'charts' ? '📈 Charts' : '💻 System Stats' }}
        </button>
      </div>
    </div>

    <!-- System Stats View -->
    <div v-if="viewMode === 'stats'" class="system-stats">
      <div class="stats-grid">
        <!-- Database Stats -->
        <div class="stat-section">
          <h3>📊 Database Statistics</h3>
          <div class="metrics">
            <div class="metric">
              <span class="metric-label">Total Items:</span>
              <span class="metric-value">{{ systemStats.database?.total_items || 0 }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Total Sellers:</span>
              <span class="metric-value">{{ systemStats.database?.total_sellers || 0 }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Inventory Value:</span>
              <span class="metric-value">${{ formatNumber(systemStats.database?.total_inventory_value || 0) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Average Price:</span>
              <span class="metric-value">${{ formatNumber(systemStats.database?.price_statistics?.average || 0) }}</span>
            </div>
          </div>
        </div>

        <!-- System Resources -->
        <div class="stat-section">
          <h3>💾 System Resources</h3>
          <div class="metrics">
            <div class="metric">
              <span class="metric-label">Memory Usage:</span>
              <span class="metric-value" :class="getHealthClass(systemStats.system?.memory?.used_percent)">
                {{ systemStats.system?.memory?.used_percent || 0 }}%
              </span>
            </div>
            <div class="metric">
              <span class="metric-label">Disk Usage:</span>
              <span class="metric-value" :class="getHealthClass(systemStats.system?.disk?.used_percent)">
                {{ systemStats.system?.disk?.used_percent || 0 }}%
              </span>
            </div>
            <div class="metric">
              <span class="metric-label">CPU Usage:</span>
              <span class="metric-value" :class="getHealthClass(systemStats.system?.cpu_usage_percent)">
                {{ systemStats.system?.cpu_usage_percent || 0 }}%
              </span>
            </div>
          </div>
        </div>

        <!-- API Stats -->
        <div class="stat-section">
          <h3>🚀 API Statistics</h3>
          <div class="metrics">
            <div class="metric">
              <span class="metric-label">Uptime:</span>
              <span class="metric-value">{{ formatUptime(systemStats.api?.uptime_hours || 0) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Health Status:</span>
              <span class="metric-value" :class="systemStats.health_status === 'healthy' ? 'health-good' : 'health-warning'">
                ● {{ (systemStats.health_status || 'unknown').toUpperCase() }}
              </span>
            </div>
            <div class="metric">
              <span class="metric-label">Active Webhooks:</span>
              <span class="metric-value">{{ systemStats.api?.active_webhooks || 0 }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Active Alerts:</span>
              <span class="metric-value">{{ systemStats.api?.active_alerts || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts View -->
    <div v-if="viewMode === 'charts'" class="charts-view">
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="card-title">Total Items</div>
          <div class="card-value">{{ chartData.stats?.total_items || 0 }}</div>
        </div>
        <div class="summary-card">
          <div class="card-title">Total Sellers</div>
          <div class="card-value">{{ chartData.stats?.total_sellers || 0 }}</div>
        </div>
        <div class="summary-card">
          <div class="card-title">Average Price</div>
          <div class="card-value">${{ formatNumber(chartData.stats?.avg_price || 0) }}</div>
        </div>
        <div class="summary-card">
          <div class="card-title">Price Range</div>
          <div class="card-value">
            ${{ formatNumber(chartData.stats?.price_range?.min || 0) }} - 
            ${{ formatNumber(chartData.stats?.price_range?.max || 0) }}
          </div>
        </div>
      </div>

      <!-- Charts -->
      <div class="charts-grid">
        <div v-if="chartData.charts?.price_distribution" class="chart-container">
          <h3>📈 Price Distribution</h3>
          <img :src="'data:image/png;base64,' + chartData.charts.price_distribution" 
               alt="Price Distribution Chart" 
               class="chart-image" />
        </div>

        <div v-if="chartData.charts?.sellers_chart" class="chart-container">
          <h3>👥 Top Sellers by Item Count</h3>
          <img :src="'data:image/png;base64,' + chartData.charts.sellers_chart" 
               alt="Sellers Chart" 
               class="chart-image" />
        </div>

        <div v-if="chartData.charts?.avg_price_by_seller" class="chart-container">
          <h3>💰 Average Price by Seller</h3>
          <img :src="'data:image/png;base64,' + chartData.charts.avg_price_by_seller" 
               alt="Average Price Chart" 
               class="chart-image" />
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-message">
      <h3>❌ Error Loading Data</h3>
      <p>{{ error }}</p>
      <button @click="refreshData" class="refresh-btn">Try Again</button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>Loading analytics data...</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AnalyticsDashboard',
  data() {
    return {
      viewMode: 'charts', // 'charts' or 'stats'
      loading: false,
      error: null,
      apiBaseUrl: 'http://localhost:8002',
      chartData: {
        charts: {},
        stats: {}
      },
      systemStats: {}
    };
  },
  async mounted() {
    await this.loadAllData();
  },
  methods: {
    async loadAllData() {
      this.loading = true;
      this.error = null;
      
      try {
        await Promise.all([
          this.loadChartData(),
          this.loadSystemStats()
        ]);
      } catch (error) {
        console.error('Error loading analytics data:', error);
        this.error = error.message || 'Failed to load analytics data';
      } finally {
        this.loading = false;
      }
    },

    async loadChartData() {
      try {
        const response = await axios.get(`${this.apiBaseUrl}/analytics/charts`);
        
        if (response.data.success) {
          this.chartData = response.data;
        } else {
          throw new Error(response.data.message || 'Failed to load charts');
        }
      } catch (error) {
        console.error('Error loading chart data:', error);
        throw error;
      }
    },

    async loadSystemStats() {
      try {
        const response = await axios.get(`${this.apiBaseUrl}/analytics/system-stats`);
        
        if (response.data.success) {
          this.systemStats = response.data;
        } else {
          throw new Error(response.data.message || 'Failed to load system stats');
        }
      } catch (error) {
        console.error('Error loading system stats:', error);
        throw error;
      }
    },

    async refreshData() {
      await this.loadAllData();
    },

    toggleView() {
      this.viewMode = this.viewMode === 'charts' ? 'stats' : 'charts';
    },

    formatNumber(value) {
      if (typeof value !== 'number') return '0';
      return value.toFixed(2);
    },

    formatUptime(hours) {
      if (hours < 1) {
        return `${Math.round(hours * 60)} minutes`;
      } else if (hours < 24) {
        return `${hours.toFixed(1)} hours`;
      } else {
        return `${Math.round(hours / 24)} days`;
      }
    },

    getHealthClass(percentage) {
      if (percentage < 70) return 'health-good';
      if (percentage < 85) return 'health-warning';
      return 'health-critical';
    }
  }
};
</script>

<style scoped>
/* Minimalist Black Theme for Analytics */
.analytics-container {
  padding: 20px;
  background: #000000;
  color: #ffffff;
  min-height: 100vh;
}

.analytics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 1px solid #222222;
}

.analytics-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.refresh-btn, .toggle-btn {
  padding: 8px 16px;
  background: #222222;
  color: #ffffff;
  border: 1px solid #444444;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 14px;
}

.refresh-btn:hover:not(:disabled), .toggle-btn:hover {
  background: #333333;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle-btn {
  background: #1a3a1a;
  border-color: #2a5a2a;
}

.toggle-btn:hover {
  background: #2a4a2a;
}

/* System Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.stat-section {
  background: #111111;
  border: 1px solid #222222;
  border-radius: 8px;
  padding: 20px;
}

.stat-section h3 {
  margin: 0 0 15px 0;
  font-size: 1.1rem;
  color: #ffffff;
  border-bottom: 1px solid #333333;
  padding-bottom: 8px;
}

.metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dotted #333333;
}

.metric:last-child {
  border-bottom: none;
}

.metric-label {
  color: #cccccc;
  font-size: 14px;
}

.metric-value {
  color: #ffffff;
  font-weight: bold;
  font-size: 14px;
}

.health-good {
  color: #4CAF50 !important;
}

.health-warning {
  color: #FF9800 !important;
}

.health-critical {
  color: #F44336 !important;
}

/* Charts View */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.summary-card {
  background: #111111;
  border: 1px solid #222222;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.card-title {
  color: #cccccc;
  font-size: 14px;
  margin-bottom: 8px;
}

.card-value {
  color: #4CAF50;
  font-size: 1.5rem;
  font-weight: bold;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
}

.chart-container {
  background: #111111;
  border: 1px solid #222222;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.chart-container h3 {
  margin: 0 0 15px 0;
  color: #ffffff;
  font-size: 1.1rem;
}

.chart-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  background: #ffffff;
}

/* Error State */
.error-message {
  text-align: center;
  padding: 40px;
  background: #2a1f1f;
  border: 1px solid #4a3333;
  border-radius: 8px;
  color: #ffcccc;
}

.error-message h3 {
  margin: 0 0 10px 0;
  color: #ff6666;
}

.error-message p {
  margin: 0 0 20px 0;
  color: #cccccc;
}

/* Loading State */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #333333;
  border-top: 3px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Responsive Design */
@media (max-width: 768px) {
  .analytics-container {
    padding: 15px;
  }

  .analytics-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }

  .header-actions {
    justify-content: center;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .metric {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .summary-cards {
    grid-template-columns: 1fr;
  }
}
</style>
