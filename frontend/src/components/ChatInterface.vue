<template>
  <div class="chat-container">
    <div class="chat-header">
      <h2>AI Assistant</h2>
      <div class="chat-description">
        <p>Use natural language to manage your inventory:</p>
        <div class="command-examples">
          <div class="example-cmd">"add laptop for $999 from TechStore"</div>
          <div class="example-cmd">"delete all items from Mike"</div>
          <div class="example-cmd">"increase all prices by 10%"</div>
          <div class="example-cmd">"add 3 apples for $5 from John"</div>
        </div>
      </div>
    </div>

    <!-- Chat History -->
    <div class="chat-history" ref="chatHistory">
      <div v-for="(message, index) in chatHistory" :key="index" class="message" :class="message.type">
        <div class="message-content">
          <div class="message-avatar">
            <span v-if="message.type === 'user'">👤</span>
            <span v-else>🤖</span>
          </div>
          <div class="message-bubble">
            <div class="message-text" v-html="formatMessage(message.text)"></div>
            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Chat Input -->
    <div class="chat-input-container">
      <form @submit.prevent="sendMessage" class="chat-form">
        <input
          v-model="currentMessage"
          placeholder="Type your command here..."
          :disabled="isLoading"
          class="chat-input"
          ref="messageInput"
        >
        <button
          type="submit"
          :disabled="!currentMessage.trim() || isLoading"
          class="send-btn"
        >
          {{ isLoading ? 'Processing...' : 'Send' }}
        </button>
      </form>
    </div>

    <!-- Session Info -->
    <div class="session-info">
      <div class="session-status">
        <span class="status-label">Session:</span>
        <span class="status-value">{{ sessionId.substring(0, 8) }}...</span>
      </div>
      <div class="message-count">
        <span class="count-label">Messages:</span>
        <span class="count-value">{{ chatHistory.length }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ChatInterface',
  data() {
    return {
      currentMessage: '',
      chatHistory: [],
      isLoading: false,
      sessionId: this.generateSessionId(),
      apiBaseUrl: 'http://localhost:8002'
    };
  },
  mounted() {
    this.addWelcomeMessage();
    this.$refs.messageInput?.focus();
  },  methods: {
    generateSessionId() {
      return 'session_' + Math.random().toString(36).substr(2, 9);
    },    addWelcomeMessage() {
      this.chatHistory.push({
        type: 'assistant',
        text: 'Welcome to the Smart Inventory System.<br><br>I can help you manage your inventory using natural language:<br><br>• "add laptop for $999 from TechStore"<br>• "delete bottle from Mike"<br>• "update all apple prices to $5"<br>• "increase all prices by 10%"<br><br>Ready to assist you.',
        timestamp: new Date()
      });
    },

    async sendMessage() {
      if (!this.currentMessage.trim() || this.isLoading) return;

      const userMessage = this.currentMessage.trim();
      
      // Add user message to history
      this.chatHistory.push({
        type: 'user',
        text: userMessage,
        timestamp: new Date()
      });

      // Clear input
      this.currentMessage = '';
      this.isLoading = true;

      try {
        // Send to smart-add endpoint
        const response = await axios.post(`${this.apiBaseUrl}/smart-add`, {
          message: userMessage,
          session_id: this.sessionId
        });

        // Add assistant response
        this.chatHistory.push({
          type: 'assistant',
          text: response.data.result || '✅ Operation completed successfully!',
          timestamp: new Date(),
          status: response.data.status,
          details: response.data.details
        });

        // Emit event to refresh items list
        this.$emit('inventory-updated');

      } catch (error) {
        console.error('Chat error:', error);
        
        let errorMessage = '❌ Sorry, I encountered an error processing your request.';
        
        if (error.response?.data?.result) {
          errorMessage = error.response.data.result;
        } else if (error.response?.data?.details?.error) {
          errorMessage = `❌ Error: ${error.response.data.details.error}`;
        } else if (error.message) {
          errorMessage = `❌ Network error: ${error.message}`;
        }

        this.chatHistory.push({
          type: 'error',
          text: errorMessage,
          timestamp: new Date()
        });
      } finally {
        this.isLoading = false;
        this.scrollToBottom();
        this.$nextTick(() => {
          this.$refs.messageInput?.focus();
        });
      }
    },

    formatMessage(text) {
      // Convert line breaks to <br> tags and handle basic formatting
      return text
        .replace(/\n/g, '<br>')
        .replace(/✅/g, '<span class="success-icon">✅</span>')
        .replace(/❌/g, '<span class="error-icon">❌</span>')
        .replace(/⚠️/g, '<span class="warning-icon">⚠️</span>')
        .replace(/\$(\d+\.?\d*)/g, '<span class="price">$$$1</span>');
    },

    formatTime(timestamp) {
      return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const chatHistory = this.$refs.chatHistory;
        if (chatHistory) {
          chatHistory.scrollTop = chatHistory.scrollHeight;
        }
      });
    }
  },

  watch: {
    chatHistory: {
      handler() {
        this.scrollToBottom();
      },
      deep: true
    }
  }
};
</script>

<style scoped>
.chat-container {
  background: #000000;
  border: 1px solid #222222;
  border-radius: 8px;
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  text-align: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #222222;
  padding-bottom: 15px;
}

.chat-header h2 {
  color: #ffffff;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.chat-description p {
  color: #cccccc;
  margin: 0 0 10px 0;
  font-size: 0.9rem;
}

.command-examples {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.example-cmd {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 4px;
  padding: 6px 10px;
  color: #999999;
  font-size: 0.8rem;
  text-align: center;
  transition: all 0.2s ease;
}

.example-cmd:hover {
  background: #222222;
  border-color: #444444;
  color: #cccccc;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 15px;
  padding: 10px;
  background: #111111;
  border: 1px solid #222222;
  border-radius: 4px;
  max-height: 400px;
}

.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-track {
  background: #111111;
}

.chat-history::-webkit-scrollbar-thumb {
  background: #333333;
  border-radius: 3px;
}

.chat-history::-webkit-scrollbar-thumb:hover {
  background: #444444;
}

.message {
  margin-bottom: 15px;
}

.message-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.message.user .message-content {
  flex-direction: row-reverse;
}

.message-avatar {
  background: #333333;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.message-bubble {
  max-width: 70%;
  background: #222222;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 10px 12px;
}

.message.user .message-bubble {
  background: #111111;
  border-color: #444444;
}

.message-text {
  color: #ffffff;
  line-height: 1.4;
  word-wrap: break-word;
  font-size: 0.9rem;
}

.message-time {
  font-size: 0.7rem;
  color: #666666;
  margin-top: 4px;
  text-align: right;
}

.chat-input-container {
  border-top: 1px solid #222222;
  padding-top: 15px;
}

.chat-form {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.chat-input {
  flex: 1;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 4px;
  padding: 10px 12px;
  color: #ffffff;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #555555;
  background: #222222;
}

.chat-input::placeholder {
  color: #666666;
}

.chat-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-btn {
  background: #333333;
  border: 1px solid #444444;
  border-radius: 4px;
  padding: 10px 16px;
  color: #ffffff;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.send-btn:hover:not(:disabled) {
  background: #444444;
  border-color: #555555;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.session-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 15px;
  padding: 10px;
  background: #111111;
  border: 1px solid #222222;
  border-radius: 4px;
  font-size: 0.8rem;
}

.session-status, .message-count {
  display: flex;
  align-items: center;
  gap: 5px;
}

.status-label, .count-label {
  color: #666666;
}

.status-value, .count-value {
  color: #cccccc;
  font-family: 'Courier New', monospace;
}

/* Message formatting for success/error icons */
.success-icon {
  color: #00ff00;
}

.error-icon {
  color: #ff6666;
}

.warning-icon {
  color: #ffaa00;
}

.price {
  font-weight: bold;
  color: #00ff00;
}
</style>
