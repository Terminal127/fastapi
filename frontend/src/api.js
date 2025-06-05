import axios from 'axios';

const apiClient = axios.create({
    baseURL: 'http://localhost:8002',
    headers: {
        'Content-Type': 'application/json',
    }
});

export default {
  getItems() {
    return apiClient.get('/items');
  },
  smartAdd(message, sessionId = 'default') {
    return apiClient.post('/smart-add', {
      message: message,
      session_id: sessionId
    });
  },
  // Legacy methods for compatibility
  createItem(item) {
    const message = `add ${item.name} for $${item.price} from ${item.seller}`;
    return this.smartAdd(message);
  },
  deleteItem(name, seller) {
    const message = `delete ${name} from ${seller}`;
    return this.smartAdd(message);
  }
};
