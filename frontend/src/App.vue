<template>
  <div id="app">
    <header>
      <h1>Smart Inventory Management</h1>
      <p class="subtitle">AI-Powered Inventory with Natural Language Processing</p>
      
      <!-- Navigation Tabs -->
      <nav class="nav-tabs">
        <button 
          @click="activeTab = 'chat'" 
          :class="{ active: activeTab === 'chat' }"
          class="nav-tab"
        >
          💬 Chat Assistant
        </button>
        <button 
          @click="activeTab = 'items'" 
          :class="{ active: activeTab === 'items' }"
          class="nav-tab"
        >
          📦 Inventory
        </button>
        <button 
          @click="activeTab = 'analytics'" 
          :class="{ active: activeTab === 'analytics' }"
          class="nav-tab"
        >
          📊 Analytics
        </button>
      </nav>
    </header>

    <div class="main-container">
      <!-- Chat Interface Tab -->
      <div v-if="activeTab === 'chat'" class="tab-content">
        <div class="chat-section">
          <ChatInterface @inventory-updated="refreshItems" />
        </div>
        <div class="items-section">
          <ItemList ref="itemList" />
        </div>
      </div>

      <!-- Items List Tab -->
      <div v-if="activeTab === 'items'" class="tab-content">
        <ItemList ref="itemListStandalone" />
      </div>

      <!-- Analytics Tab -->
      <div v-if="activeTab === 'analytics'" class="tab-content">
        <AnalyticsDashboard />
      </div>
    </div>

    <footer>
      <p>Built with FastAPI, Vue.js, and LangChain | AI Assistant powered by Google Gemini</p>
    </footer>
  </div>
</template>

<script>
import ItemList from './components/ItemList.vue'
import ChatInterface from './components/ChatInterface.vue'
import AnalyticsDashboard from './components/AnalyticsDashboard.vue'

export default {
  name: 'App',
  components: {
    ItemList,
    ChatInterface,
    AnalyticsDashboard
  },
  data() {
    return {
      activeTab: 'chat' // Default to chat tab
    };
  },
  methods: {
    refreshItems() {
      // Refresh the items list when inventory is updated via chat
      if (this.$refs.itemList) {
        this.$refs.itemList.fetchItems();
      }
      if (this.$refs.itemListStandalone) {
        this.$refs.itemListStandalone.fetchItems();
      }
    }
  }
};
</script>

<style>
/* Minimalist Black Theme */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #ffffff;
  min-height: 100vh;
  background: #000000;
}

header {
  background: #111111;
  color: #ffffff;
  padding: 2rem 0;
  text-align: center;
  border-bottom: 1px solid #222222;
}

header h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 300;
  letter-spacing: 1px;
}

.subtitle {
  margin: 0.5rem 0 1.5rem 0;
  font-size: 0.9rem;
  color: #cccccc;
  font-weight: 300;
}

/* Navigation Tabs */
.nav-tabs {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-top: 20px;
}

.nav-tab {
  padding: 12px 24px;
  background: #222222;
  color: #cccccc;
  border: 1px solid #333333;
  border-right: none;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  font-weight: 500;
}

.nav-tab:first-child {
  border-radius: 6px 0 0 6px;
}

.nav-tab:last-child {
  border-radius: 0 6px 6px 0;
  border-right: 1px solid #333333;
}

.nav-tab:hover {
  background: #333333;
  color: #ffffff;
}

.nav-tab.active {
  background: #4CAF50;
  color: #ffffff;
  border-color: #4CAF50;
}

.nav-tab.active + .nav-tab {
  border-left-color: #4CAF50;
}

.subtitle {
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  opacity: 0.7;
  font-weight: 300;
}

.main-container {
  min-height: calc(100vh - 200px);
  background: #000000;
}

.tab-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  min-height: calc(100vh - 200px);
}

/* For standalone tabs (items and analytics) */
.tab-content:has(.analytics-container),
.tab-content:has(> .items-container:only-child) {
  grid-template-columns: 1fr;
}

@media (max-width: 1024px) {
  .tab-content {
    grid-template-columns: 1fr;
  }
}

.chat-section, .items-section {
  background: #111111;
  border-right: 1px solid #222222;
}

.items-section {
  border-right: none;
}

footer {
  background: #111111;
  color: #ffffff;
  text-align: center;
  padding: 1rem;
  border-top: 1px solid #222222;
}

footer p {
  margin: 0;
  font-size: 0.8rem;
  opacity: 0.6;
  font-weight: 300;
}
</style>
