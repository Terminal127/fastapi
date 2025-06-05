<template>
  <div id="app">
    <header>
      <h1>Smart Inventory Management</h1>
      <p class="subtitle">AI-Powered Inventory with Natural Language Processing</p>
    </header>

    <div class="main-container">
      <!-- Chat Interface Section -->
      <div class="chat-section">
        <ChatInterface @inventory-updated="refreshItems" />
      </div>

      <!-- Items List Section -->
      <div class="items-section">
        <ItemList ref="itemList" />
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

export default {
  name: 'App',
  components: {
    ItemList,
    ChatInterface
  },
  methods: {
    refreshItems() {
      // Refresh the items list when inventory is updated via chat
      if (this.$refs.itemList) {
        this.$refs.itemList.fetchItems();
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
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  opacity: 0.7;
  font-weight: 300;
}

.main-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  min-height: calc(100vh - 140px);
}

@media (max-width: 1024px) {
  .main-container {
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
