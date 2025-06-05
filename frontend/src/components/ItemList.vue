<template>
  <div class="items-container">
    <div class="items-header">
      <h2>Inventory</h2>
      <button @click="fetchItems" class="refresh-btn" :disabled="loading">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <!-- Quick Add Form (Manual) -->
    <div class="quick-add-section">
      <h3>Add New Item</h3>
      <form class="add-item-form" @submit.prevent="addItem">
        <input v-model="newItem.name" placeholder="Item name" class="form-input" required>
        <input v-model.number="newItem.price" type="number" placeholder="Price" class="form-input" step="0.01" min="0" required>
        <input v-model="newItem.seller" placeholder="Seller" class="form-input" required>
        <button type="submit" :disabled="loading" class="submit-btn">
          {{ loading ? 'Adding...' : 'Add Item' }}
        </button>
      </form>
      <p class="tip">Use the AI assistant for advanced operations</p>
    </div>    <!-- Items Display -->
    <div class="items-list">
      <div v-if="items.length === 0 && !loading" class="no-items">
        No items in inventory
      </div>
      <div v-for="item in items" :key="item.id" class="item-card">
        <div class="item-info">
          <h4>{{ item.name }}</h4>
          <p>${{ item.price.toFixed(2) }}</p>
          <p>Seller: {{ item.seller }}</p>
        </div>
        <div class="item-actions">
          <button @click="openUpdateModal(item)" class="action-btn edit-btn">Edit</button>
          <button @click="deleteItem(item.id)" class="action-btn delete-btn" :disabled="loading">Delete</button>
        </div>
      </div>
    </div>    <!-- Edit Modal -->
    <div v-if="editingItem" class="modal-overlay" @click="cancelEdit">
      <div class="modal" @click.stop>
        <h3>Edit Item</h3>
        <form @submit.prevent="updateItem" class="modal-form">
          <input v-model="editingItem.name" placeholder="Item name" class="form-input" required>
          <input v-model.number="editingItem.price" type="number" placeholder="Price" class="form-input" step="0.01" min="0" required>
          <input v-model="editingItem.seller" placeholder="Seller" class="form-input" required>
          <div class="modal-actions">
            <button type="button" @click="cancelEdit" class="action-btn cancel-btn">Cancel</button>
            <button type="submit" :disabled="loading" class="action-btn submit-btn">
              {{ loading ? 'Updating...' : 'Update' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ItemList',
  data() {
    return {
      items: [],
      newItem: {
        name: '',
        price: 0,
        seller: ''
      },
      editingItem: null,
      loading: false,
      apiBaseUrl: 'http://localhost:8002'
    };
  },
  async mounted() {
    await this.fetchItems();
  },  methods: {    particleStyle() {
      return {
        left: Math.random() * 100 + '%',
        animationDelay: Math.random() * 3 + 's',
        animationDuration: (Math.random() * 3 + 2) + 's'
      };
    },
    
    async fetchItems() {
      try {
        this.loading = true;
        const response = await axios.get(`${this.apiBaseUrl}/items`);
        this.items = response.data.items || [];
      } catch (error) {
        console.error('Error fetching items:', error);
        this.items = [];
      } finally {
        this.loading = false;
      }
    },

    async addItem() {
      if (this.loading) return;
      
      try {
        if (!this.newItem.name || !this.newItem.seller || this.newItem.price <= 0) {
          alert('Please fill in all fields and ensure price is greater than 0');
          return;
        }
        
        this.loading = true;
        
        // Use the smart-add endpoint with natural language
        const message = `add ${this.newItem.name} for $${this.newItem.price} from ${this.newItem.seller}`;
        
        const response = await axios.post(`${this.apiBaseUrl}/smart-add`, {
          message: message,
          session_id: 'manual_add_' + Math.random().toString(36).substr(2, 9)
        });

        if (response.data.status === 'success') {
          // Reset form only after successful addition
          this.newItem = { name: '', price: 0, seller: '' };
          await this.fetchItems();
          
          // Show success message
          alert('✅ ' + (response.data.result || 'Item added successfully!'));
        } else {
          alert('❌ ' + (response.data.result || 'Failed to add item'));
        }
        
      } catch (error) {
        console.error('Error adding item:', error);
        const errorMsg = error.response?.data?.result || error.message || 'Error adding item';
        alert('❌ ' + errorMsg);
      } finally {
        this.loading = false;
      }
    },    openUpdateModal(item) {
      this.editingItem = { ...item };
    },

    async deleteItem(itemId) {
      if (!confirm('Are you sure you want to delete this item?')) return;
      
      try {
        this.loading = true;
        
        // Find the item name for the delete message
        const item = this.items.find(i => i.id === itemId);
        const message = `delete ${item?.name || 'item'}`;
        
        const response = await axios.post(`${this.apiBaseUrl}/smart-add`, {
          message: message,
          session_id: 'manual_delete_' + Math.random().toString(36).substr(2, 9)
        });

        if (response.data.status === 'success') {
          await this.fetchItems();
          alert('✅ ' + (response.data.result || 'Item deleted successfully!'));
        } else {
          alert('❌ ' + (response.data.result || 'Failed to delete item'));
        }
        
      } catch (error) {
        console.error('Error deleting item:', error);
        const errorMsg = error.response?.data?.result || error.message || 'Error deleting item';
        alert('❌ ' + errorMsg);
      } finally {
        this.loading = false;
      }
    },

    cancelEdit() {
      this.editingItem = null;
    },

    async updateItem() {
      if (!this.editingItem || this.loading) return;

      try {
        this.loading = true;
        
        // Use smart-add endpoint to update
        const message = `update ${this.editingItem.name} price to $${this.editingItem.price} from ${this.editingItem.seller}`;
        
        const response = await axios.post(`${this.apiBaseUrl}/smart-add`, {
          message: message,
          session_id: 'manual_update_' + Math.random().toString(36).substr(2, 9)
        });

        if (response.data.status === 'success') {
          this.editingItem = null;
          await this.fetchItems();
          alert('✅ ' + (response.data.result || 'Item updated successfully!'));
        } else {
          alert('❌ ' + (response.data.result || 'Failed to update item'));
        }

      } catch (error) {
        console.error('Error updating item:', error);
        const errorMsg = error.response?.data?.result || error.message || 'Error updating item';
        alert('❌ ' + errorMsg);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
/* Minimalist Black Theme */
.items-container {
  padding: 20px;
  background: #000000;
  color: #ffffff;
  min-height: 100%;
}

.items-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 1px solid #222222;
}

.items-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #ffffff;
}

.refresh-btn {
  padding: 8px 16px;
  background: #222222;
  color: #ffffff;
  border: 1px solid #444444;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #333333;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quick-add-section {
  background: #111111;
  padding: 20px;
  border: 1px solid #222222;
  border-radius: 4px;
  margin-bottom: 30px;
}

.quick-add-section h3 {
  margin: 0 0 15px 0;
  font-size: 1.1rem;
  font-weight: 500;
  color: #ffffff;
}

.add-item-form {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.form-input {
  flex: 1;
  min-width: 150px;
  padding: 8px 12px;
  background: #000000;
  color: #ffffff;
  border: 1px solid #333333;
  border-radius: 4px;
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: #555555;
}

.form-input::placeholder {
  color: #666666;
}

.submit-btn {
  padding: 8px 16px;
  background: #333333;
  color: #ffffff;
  border: 1px solid #444444;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #444444;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tip {
  margin: 0;
  font-size: 12px;
  color: #666666;
  font-style: italic;
}

.items-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.no-items {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: #666666;
  background: #111111;
  border: 1px solid #222222;
  border-radius: 4px;
}

.item-card {
  background: #111111;
  border: 1px solid #222222;
  border-radius: 4px;
  padding: 15px;
  transition: border-color 0.2s;
}

.item-card:hover {
  border-color: #333333;
}

.item-info {
  margin-bottom: 15px;
}

.item-info h4 {
  margin: 0 0 8px 0;
  font-size: 1.1rem;
  font-weight: 500;
  color: #ffffff;
}

.item-info p {
  margin: 4px 0;
  font-size: 14px;
  color: #cccccc;
}

.item-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid #333333;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-btn {
  background: #222222;
  color: #ffffff;
}

.edit-btn:hover {
  background: #333333;
}

.delete-btn {
  background: #2a1f1f;
  color: #ffffff;
  border-color: #4a3333;
}

.delete-btn:hover:not(:disabled) {
  background: #3a2f2f;
}

.delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 4px;
  padding: 25px;
  min-width: 400px;
  max-width: 90vw;
}

.modal h3 {
  margin: 0 0 20px 0;
  font-size: 1.2rem;
  font-weight: 500;
  color: #ffffff;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 5px;
}

.cancel-btn {
  background: #222222;
  color: #ffffff;
}

.cancel-btn:hover {
  background: #333333;
}

/* Responsive Design */
@media (max-width: 768px) {
  .items-container {
    padding: 15px;
  }
  
  .items-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
  
  .add-item-form {
    flex-direction: column;
  }
  
  .items-list {
    grid-template-columns: 1fr;
  }
  
  .modal {
    min-width: 320px;
    margin: 20px;
  }
  
  .modal-actions {
    flex-direction: column;
  }
}
</style>
